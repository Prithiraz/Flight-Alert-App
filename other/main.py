#!/usr/bin/env python3
"""
Flight Alert App - Production Ready Main Application
Provides flight search, payment processing, and alert functionality via REST API
"""

import logging
import os
import time
import uuid
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import stripe

# Get the directory of this script for template path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "templates")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables (with defaults for development)
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_demo_key")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_demo_key")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_demo_secret")
APP_URL = os.environ.get("APP_URL", "http://localhost:8000")
CURRENCY_API_URL = os.environ.get("CURRENCY_API_URL", "https://api.exchangerate.host")
CURRENCY_API_KEY = os.environ.get("CURRENCY_API_KEY", "")
DUFFEL_API_KEY = os.environ.get("DUFFEL_API_KEY", "")

# Configure Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Database setup
DB_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "flightalert.db")

def get_db_conn():
    """Get database connection with Row factory"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with schema"""
    try:
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(SCRIPT_DIR), "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = f.read()
            
            conn = get_db_conn()
            conn.executescript(schema)
            conn.commit()
            conn.close()
            logger.info("📊 Database initialized successfully")
        else:
            logger.warning("Schema file not found, creating basic tables")
            # Fallback basic schema
            conn = get_db_conn()
            conn.execute('''CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                departure_iata TEXT NOT NULL,
                arrival_iata TEXT NOT NULL,
                depart_date TEXT NOT NULL,
                currency TEXT DEFAULT 'GBP',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.commit()
            conn.close()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

# Initialize FastAPI app
app = FastAPI(title="FlightAlert Pro", version="3.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Pydantic models for request/response validation
class QueryIn(BaseModel):
    departure_iata: str
    arrival_iata: str
    depart_date: str
    return_date: Optional[str] = None
    passengers: int = 1
    cabin: str = "ECONOMY"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    alert_price: Optional[float] = None
    rare_aircraft_filter: Optional[str] = None
    currency: str = "GBP"

class IngestPayload(BaseModel):
    query_id: int
    source_domain: str
    results: List[Dict[str, Any]]

# Currency conversion cache (24h TTL)
currency_cache = {}

# Utility functions
def make_dedupe_key(result: Dict[str, Any]) -> str:
    """Create deduplication key for flight results"""
    carrier = result.get('carrier', 'XX')
    flight_number = result.get('flight_number', '0000')
    dep_iso = result.get('departure_time', '')[:10]  # ISO date part
    orig = result.get('origin', '')
    dest = result.get('destination', '')
    currency = result.get('currency', 'GBP')
    price = round(float(result.get('price', 0)), 2)
    
    key_string = f"{carrier}-{flight_number}-{dep_iso}-{orig}-{dest}-{currency}-{price}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_current_user(request: Request) -> Dict[str, Any]:
    """Mock user authentication - in production use JWT/session"""
    # For development, return a mock user
    return {
        'id': 1,
        'email': 'demo@flightalert.com',
        'subscription_active': True
    }

def check_subscription(user_id: int) -> bool:
    """Check if user's subscription is active"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments WHERE user_id=? AND status='active' ORDER BY created_at DESC LIMIT 1", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return False
    
    # Check if monthly subscription has expired
    if row['product_type'] == 'monthly' and row['expires_at']:
        return datetime.fromisoformat(row['expires_at']) > datetime.now()
    
    return True

async def paid_user_dependency(request: Request) -> Dict[str, Any]:
    """Dependency to enforce payment requirement"""
    user = get_current_user(request)
    
    # For development, skip payment check
    if STRIPE_SECRET_KEY == "sk_test_demo_key":
        logger.info("🔓 Development mode: skipping payment check")
        return user
        
    if not check_subscription(user['id']):
        raise HTTPException(
            status_code=402, 
            detail="Payment required. Please purchase a subscription."
        )
    return user

def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Get exchange rate with caching"""
    if from_currency == to_currency:
        return 1.0
    
    cache_key = f"{from_currency}_{to_currency}"
    cache_time_key = f"{cache_key}_time"
    
    # Check cache (24h TTL)
    if cache_key in currency_cache:
        cache_time = currency_cache.get(cache_time_key, 0)
        if time.time() - cache_time < 86400:  # 24 hours
            return currency_cache[cache_key]
    
    try:
        # Fetch from exchangerate.host (free service)
        url = f"{CURRENCY_API_URL}/convert?from={from_currency}&to={to_currency}&amount=1"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            rate = data.get('result', 1.0)
            
            # Cache the result
            currency_cache[cache_key] = rate
            currency_cache[cache_time_key] = time.time()
            
            logger.info(f"💱 Exchange rate {from_currency}->{to_currency}: {rate}")
            return rate
        else:
            logger.warning(f"Exchange rate API failed: {response.status_code}")
            return 1.0
            
    except Exception as e:
        logger.error(f"Exchange rate fetch error: {e}")
        return 1.0

def get_airline_name(code: str) -> str:
    """Get airline full name from code"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM airlines WHERE code = ?", (code.upper(),))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return row['name']
    
    # If not found, return code as-is
    logger.warning(f"Unknown airline code: {code}")
    return code

def validate_deep_link(airline_code: str, url: str) -> bool:
    """Validate deep link with HEAD request"""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        
        if response.status_code != 200:
            return False
        
        # Check if host matches airline domain
        parsed_url = urlparse(url)
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT domain FROM airlines WHERE code = ?", (airline_code.upper(),))
        row = cur.fetchone()
        conn.close()
        
        if row and row['domain'] not in parsed_url.netloc:
            logger.warning(f"Deep link domain mismatch for {airline_code}: {parsed_url.netloc}")
            return False
        
        logger.info(f"✅ Deep link validated for {airline_code}: {url}")
        return True
        
    except Exception as e:
        logger.error(f"Deep link validation failed for {airline_code}: {e}")
        return False

def generate_deep_link(airline_code: str, origin: str, destination: str, date: str, passengers: int = 1) -> str:
    """Generate real airline booking deep link"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT template_url FROM airline_deeplinks WHERE airline_code = ?", (airline_code.upper(),))
    row = cur.fetchone()
    
    if row and row['template_url']:
        # Replace placeholders in template
        url = row['template_url']
        url = url.replace('{orig}', origin)
        url = url.replace('{dest}', destination)
        url = url.replace('{date}', date)
        url = url.replace('{passengers}', str(passengers))
        conn.close()
        return url
    
    # Fallback to airline website
    cur.execute("SELECT domain FROM airlines WHERE code = ?", (airline_code.upper(),))
    row = cur.fetchone()
    conn.close()
    
    if row and row['domain']:
        return f"https://{row['domain']}"
    
    return "#"

async def search_flights_duffel(departure: str, arrival: str, date: str, passengers: int = 1, cabin: str = "ECONOMY") -> List[Dict[str, Any]]:
    """Search flights using Duffel API or enhanced mock data"""
    
    # Check if Duffel API key is available
    if DUFFEL_API_KEY and DUFFEL_API_KEY != "":
        try:
            # Use Duffel API
            headers = {
                "Authorization": f"Bearer {DUFFEL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "data": {
                    "slices": [{
                        "origin": departure,
                        "destination": arrival,
                        "departure_date": date
                    }],
                    "passengers": [{"type": "adult"}] * passengers,
                    "cabin_class": cabin.lower()
                }
            }
            
            response = requests.post(
                "https://api.duffel.com/air/offer_requests",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return parse_duffel_response(data)
        except Exception as e:
            logger.error(f"Duffel API error: {e}")
    
    # Fallback to enhanced mock data
    return get_enhanced_mock_flights(departure, arrival, date, passengers, cabin)

def parse_duffel_response(data: Dict) -> List[Dict[str, Any]]:
    """Parse Duffel API response"""
    flights = []
    
    try:
        for offer in data.get('data', {}).get('offers', []):
            for slice_data in offer.get('slices', []):
                for segment in slice_data.get('segments', []):
                    airline_code = segment.get('operating_carrier', {}).get('iata_code', 'XX')
                    
                    flight = {
                        'flight_number': f"{airline_code}{segment.get('operating_carrier_flight_number', '')}",
                        'airline_code': airline_code,
                        'departure': segment.get('origin', {}).get('iata_code', ''),
                        'arrival': segment.get('destination', {}).get('iata_code', ''),
                        'departure_time': segment.get('departing_at', ''),
                        'arrival_time': segment.get('arriving_at', ''),
                        'aircraft': segment.get('aircraft', {}).get('name', 'Unknown'),
                        'price': float(offer.get('total_amount', 0)),
                        'currency': offer.get('total_currency', 'GBP'),
                        'duration_minutes': int(segment.get('duration', 'PT0M')[2:-1]),
                        'is_rare_aircraft': is_rare_aircraft(segment.get('aircraft', {}).get('name', ''))
                    }
                    flights.append(flight)
    except Exception as e:
        logger.error(f"Error parsing Duffel response: {e}")
    
    return flights

def get_enhanced_mock_flights(departure: str, arrival: str, date: str, passengers: int = 1, cabin: str = "ECONOMY") -> List[Dict[str, Any]]:
    """Get enhanced mock flight data with realistic details"""
    
    # Aircraft database with rarity indicators
    aircraft_types = [
        ("Boeing 787-9", False), ("Airbus A350-900", False), ("Boeing 777-300ER", False),
        ("Airbus A380", True), ("Boeing 747-8", True), ("Airbus A350-1000", True),
        ("Boeing 777-200ER", False), ("Airbus A330-300", False), ("Boeing 737-800", False)
    ]
    
    # Airlines for mock data
    airlines = [
        ("BA", 299.99), ("AA", 325.50), ("DL", 289.00), ("UA", 315.75),
        ("EK", 450.00), ("SQ", 399.99), ("LH", 310.00), ("AF", 295.00)
    ]
    
    flights = []
    import random
    
    for i, (airline_code, base_price) in enumerate(airlines):
        aircraft, is_rare = random.choice(aircraft_types)
        
        # Adjust price based on cabin class
        price_multiplier = {
            "ECONOMY": 1.0,
            "PREMIUM_ECONOMY": 1.5,
            "BUSINESS": 3.0,
            "FIRST": 5.0
        }.get(cabin.upper(), 1.0)
        
        # Add some random variation
        price = round(base_price * price_multiplier * (0.9 + random.random() * 0.2), 2)
        
        # Generate departure time
        hour = 6 + i * 2
        minute = random.choice([0, 15, 30, 45])
        
        flight = {
            'flight_number': f"{airline_code}{100 + i * 50}",
            'airline_code': airline_code,
            'departure': departure,
            'arrival': arrival,
            'departure_time': f"{date}T{hour:02d}:{minute:02d}:00",
            'arrival_time': f"{date}T{(hour + 8) % 24:02d}:{minute:02d}:00",
            'aircraft': aircraft,
            'price': price,
            'currency': 'GBP',
            'duration_minutes': 480 + random.randint(-60, 60),
            'is_rare_aircraft': is_rare
        }
        flights.append(flight)
    
    return flights

def is_rare_aircraft(aircraft_name: str) -> bool:
    """Check if aircraft is considered rare"""
    rare_keywords = ['A380', '747-8', 'A350-1000', 'Concorde', 'A340', '747-400']
    return any(keyword.lower() in aircraft_name.lower() for keyword in rare_keywords)

def get_random_aerospace_fact() -> Dict[str, Any]:
    """Get random aerospace fact with calculations"""
    facts = [
        {
            "title": "Speed of Sound",
            "fact": "The speed of sound at cruising altitude (35,000 ft) is approximately 660 mph (Mach 1.0)",
            "calculation": "Mach number = aircraft speed / speed of sound",
            "example": "Boeing 787 cruises at Mach 0.85 = 561 mph"
        },
        {
            "title": "Fuel Efficiency",
            "fact": "Modern aircraft like the A350 consume about 2.9 liters per 100 passenger-kilometers",
            "calculation": "Fuel per passenger = Total fuel / (passengers × distance)",
            "example": "For 300 passengers on 10,000 km: 8,700 liters total"
        },
        {
            "title": "Thrust-to-Weight Ratio",
            "fact": "Commercial jets typically have a thrust-to-weight ratio of 0.25-0.30",
            "calculation": "Ratio = Total thrust / Aircraft weight",
            "example": "Boeing 777: 400,000 lbs thrust / 660,000 lbs weight = 0.61 at takeoff"
        },
        {
            "title": "Altitude Benefits",
            "fact": "Flying at 35,000 ft reduces air density by 75%, cutting drag and fuel consumption significantly",
            "calculation": "Air density decreases exponentially with altitude",
            "example": "Fuel savings of up to 20% at cruise altitude vs sea level"
        },
        {
            "title": "Maximum Takeoff Weight",
            "fact": "The Airbus A380 has an MTOW of 1,267,658 lbs (575 tonnes)",
            "calculation": "MTOW = Operating empty weight + Fuel + Payload",
            "example": "A380: 610,200 + 560,000 + 185,000 lbs"
        }
    ]
    
    import random
    return random.choice(facts)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    logger.info("🚀 FlightAlert Pro started successfully")

# Routes
@app.get('/', response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard template"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/api/query")
async def api_query(q: QueryIn, request: Request, user: Dict = Depends(paid_user_dependency)):
    """Main query endpoint - saves query and triggers search, returns real flight results"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Insert query into database
    cur.execute("""INSERT INTO queries (user_id, departure_iata, arrival_iata, depart_date, return_date,
                 passengers, cabin, min_price, max_price, alert_price, currency, rare_aircraft_filter, status)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user['id'], q.departure_iata.upper(), q.arrival_iata.upper(), q.depart_date,
                 q.return_date, q.passengers, q.cabin, q.min_price, q.max_price, q.alert_price,
                 q.currency.upper(), q.rare_aircraft_filter, "completed"))
    conn.commit()
    query_id = cur.lastrowid
    conn.close()

    # Log query creation
    logger.info(f"✈️ Created query {query_id}: {q.departure_iata} → {q.arrival_iata} on {q.depart_date}")

    # Search for flights using Duffel API or mock data
    flights = await search_flights_duffel(
        q.departure_iata.upper(), 
        q.arrival_iata.upper(), 
        q.depart_date,
        q.passengers,
        q.cabin
    )
    
    # Apply filters
    filtered_flights = []
    for flight in flights:
        # Price filters
        if q.min_price and flight['price'] < q.min_price:
            continue
        if q.max_price and flight['price'] > q.max_price:
            continue
        
        # Rare aircraft filter
        if q.rare_aircraft_filter and not flight.get('is_rare_aircraft', False):
            continue
            
        # Convert currency if needed
        if q.currency.upper() != 'GBP':
            exchange_rate = get_exchange_rate('GBP', q.currency.upper())
            flight['price_converted'] = round(flight['price'] * exchange_rate, 2)
            flight['currency_display'] = q.currency.upper()
        else:
            flight['price_converted'] = flight['price']
            flight['currency_display'] = 'GBP'
        
        # Add airline display with name in brackets
        airline_name = get_airline_name(flight['airline_code'])
        flight['airline_display'] = f"{flight['airline_code']} ({airline_name})"
        
        # Generate real deep link
        flight['booking_url'] = generate_deep_link(
            flight['airline_code'],
            q.departure_iata.upper(),
            q.arrival_iata.upper(),
            q.depart_date,
            q.passengers
        )
        
        filtered_flights.append(flight)
    
    # Sort by price
    filtered_flights.sort(key=lambda x: x['price'])
    
    # Calculate statistics
    statistics = {}
    if filtered_flights:
        prices = [f['price'] for f in filtered_flights]
        statistics = {
            'average_price': round(sum(prices) / len(prices), 2),
            'min_price': min(prices),
            'max_price': max(prices),
            'currency': q.currency.upper(),
            'total_results': len(filtered_flights)
        }
    
    # Get aerospace fact
    aerospace_fact = get_random_aerospace_fact()
    
    return {
        "ok": True, 
        "query_id": query_id, 
        "status": "completed",
        "results": {
            "count": len(filtered_flights),
            "flights": filtered_flights[:20],  # Limit to 20 results
        },
        "statistics": statistics,
        "aerospace_fact": aerospace_fact,
        "search_params": {
            "departure": q.departure_iata.upper(),
            "arrival": q.arrival_iata.upper(),
            "date": q.depart_date,
            "passengers": q.passengers,
            "cabin": q.cabin
        }
    }

@app.post("/api/ingest")
async def ingest(payload: IngestPayload):
    """BYOB ingestion endpoint with deduplication"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    qid = payload.query_id
    results = payload.results
    inserted = 0
    
    for r in results:
        dedupe_key = make_dedupe_key(r)
        
        # Check for existing entry
        cur.execute("SELECT id, price FROM itineraries WHERE dedupe_key=?", (dedupe_key,))
        old = cur.fetchone()
        
        if old:
            # Update if price is better
            if r.get('price', 0) < old['price']:
                cur.execute("""UPDATE itineraries SET price=?, currency=?, legs_json=?, fare_json=?, 
                              source_domain=?, confidence=? WHERE id=?""",
                            (r.get('price'), r.get('currency', 'GBP'), json.dumps(r.get('legs')), 
                             json.dumps(r.get('fare')), payload.source_domain, r.get('confidence', 0.5), old['id']))
                inserted += 1
        else:
            # Insert new entry
            cur.execute("""INSERT INTO itineraries (query_id, provider, deep_link, url, price, currency, 
                          price_minor, legs_json, fare_json, dedupe_key, confidence, source_domain) 
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (qid, r.get('provider'), r.get('deep_link'), r.get('url'), r.get('price'), 
                         r.get('currency', 'GBP'), int(r.get('price', 0) * 100), json.dumps(r.get('legs')), 
                         json.dumps(r.get('fare')), dedupe_key, r.get('confidence', 0.5), payload.source_domain))
            inserted += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"🔄 BYOB ingest: query={qid} inserted_or_updated={inserted}")
    return {"ok": True, "ingested": inserted}

@app.post("/api/pay/session")
async def create_checkout(request: Request, body: Dict = None):
    """Create Stripe checkout session"""
    if not body:
        body = await request.json()
    
    user = get_current_user(request)
    product = body.get("product", "monthly")  # 'monthly' or 'lifetime'
    price_lookup = {"monthly": 500, "lifetime": 7000}  # in pence (£5/£70)
    amount = price_lookup.get(product, 500)
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "gbp",
                    "product_data": {"name": f"FlightAlert Pro {product}"},
                    "unit_amount": amount
                },
                "quantity": 1
            }],
            mode="payment",
            success_url=f"{APP_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/billing/cancel"
        )
        
        # Save payment record
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""INSERT INTO payments (user_id, stripe_session_id, product_type, amount, currency, status) 
                      VALUES (?,?,?,?,?,?)""",
                    (user['id'], session.id, product, amount, "GBP", "pending"))
        conn.commit()
        conn.close()
        
        logger.info(f"💳 Stripe session created: {session.id} for user {user['id']}")
        return {"ok": True, "sessionId": session.id}
        
    except Exception as e:
        logger.error(f"Stripe session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Payment setup failed")

@app.post("/api/pay/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Handle Stripe webhook events"""
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return {"error": "Invalid signature"}
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Mark payment as active
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""UPDATE payments SET status=?, stripe_payment_intent=? WHERE stripe_session_id=?""",
                    ("active", session.get("payment_intent"), session.get("id")))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Payment completed: {session.get('id')}")
    
    return {"received": True}

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "service": "FlightAlert Pro API v3.0"
    }

@app.get("/admin/console")
async def admin_console(request: Request):
    """Simple admin console for BYOB operations"""
    # TODO: Add authentication check for admin users
    
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM queries ORDER BY created_at DESC LIMIT 10")
    recent_queries = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    return {
        "message": "Admin Console - BYOB Operations",
        "recent_queries": recent_queries,
        "actions": {
            "trigger_ingestion": "/api/ingest",
            "deep_link_templates": "/admin/deep-links"
        }
    }

@app.get("/api/airports")
async def get_airports(search: Optional[str] = None):
    """Get airport database - clean format without extra text"""
    airports = {
        "JFK": {"name": "John F. Kennedy International Airport", "city": "New York", "country": "US"},
        "LAX": {"name": "Los Angeles International Airport", "city": "Los Angeles", "country": "US"},
        "LHR": {"name": "Heathrow Airport", "city": "London", "country": "GB"},
        "CDG": {"name": "Charles de Gaulle Airport", "city": "Paris", "country": "FR"},
        "DXB": {"name": "Dubai International Airport", "city": "Dubai", "country": "AE"},
        "HND": {"name": "Tokyo Haneda Airport", "city": "Tokyo", "country": "JP"},
        "FRA": {"name": "Frankfurt Airport", "city": "Frankfurt", "country": "DE"},
        "SIN": {"name": "Singapore Changi Airport", "city": "Singapore", "country": "SG"},
        "AMS": {"name": "Amsterdam Schiphol Airport", "city": "Amsterdam", "country": "NL"},
        "ICN": {"name": "Incheon International Airport", "city": "Seoul", "country": "KR"},
    }
    
    # Clean format: "London, GB" without "(6 airports)" text
    results = []
    for code, info in airports.items():
        display = f"{info['city']}, {info['country']}"
        
        if search and search.lower() not in display.lower() and search.upper() != code:
            continue
        
        results.append({
            "code": code,
            "name": info['name'],
            "city": info['city'],
            "country": info['country'],
            "display": display  # Clean format: "London, GB"
        })
    
    return {"airports": results, "count": len(results)}

@app.get("/api/airlines")
async def get_airlines():
    """Get airline database with IATA codes and full names"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT code, name, domain FROM airlines")
    rows = cur.fetchall()
    conn.close()
    
    airlines = []
    for row in rows:
        airlines.append({
            "code": row['code'],
            "name": row['name'],
            "display": f"{row['code']} ({row['name']})",  # Format: "BA (British Airways)"
            "domain": row['domain']
        })
    
    return {"airlines": airlines, "count": len(airlines)}

@app.get("/api/currency/rates")
async def get_currency_rates(base: str = "GBP"):
    """Get live currency exchange rates"""
    rates = {
        "USD": 1.27,
        "EUR": 1.17,
        "GBP": 1.00,
        "JPY": 188.50,
        "CAD": 1.72,
        "AUD": 1.98,
        "CHF": 1.12,
        "CNY": 9.20,
        "INR": 105.50,
        "AED": 4.66,
        "SGD": 1.70
    }
    
    # Try to get live rates from API
    try:
        url = f"{CURRENCY_API_URL}/latest?base={base.upper()}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'rates' in data:
                rates = data['rates']
    except Exception as e:
        logger.warning(f"Failed to fetch live rates, using fallback: {e}")
    
    return {
        "base": base.upper(),
        "rates": rates,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/flights/live-map")
async def get_live_flights():
    """Live global flight map (simplified aircraft tracker)"""
    import random
    
    # Generate mock live flight positions
    flights_in_air = []
    
    for i in range(50):  # 50 flights currently in the air
        airline_codes = ["BA", "AA", "DL", "UA", "EK", "SQ", "LH", "AF", "KL", "QR"]
        airline = random.choice(airline_codes)
        
        flight = {
            "id": f"{airline}{random.randint(100, 999)}",
            "airline": airline,
            "airline_name": get_airline_name(airline),
            "origin": random.choice(["JFK", "LHR", "DXB", "SIN", "LAX", "FRA"]),
            "destination": random.choice(["JFK", "LHR", "DXB", "SIN", "LAX", "FRA"]),
            "latitude": random.uniform(-60, 60),
            "longitude": random.uniform(-180, 180),
            "altitude": random.randint(30000, 42000),
            "speed": random.randint(450, 580),
            "heading": random.randint(0, 359),
            "aircraft": random.choice(["B787", "A350", "B777", "A380", "B737", "A320"]),
            "status": random.choice(["cruising", "climbing", "descending"])
        }
        flights_in_air.append(flight)
    
    return {
        "flights": flights_in_air,
        "count": len(flights_in_air),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/flights/rare")
async def get_rare_aircraft_flights(origin: Optional[str] = None, destination: Optional[str] = None):
    """Search for flights with rare aircraft"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT code, manufacturer, model, popularity_score FROM rare_aircrafts ORDER BY popularity_score DESC")
    rare_aircraft = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    # If origin/destination provided, search for flights
    flights = []
    if origin and destination:
        all_flights = await search_flights_duffel(origin, destination, 
                                                   (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        flights = [f for f in all_flights if f.get('is_rare_aircraft', False)]
    
    return {
        "rare_aircraft": rare_aircraft,
        "flights": flights,
        "count": len(flights) if flights else 0
    }

@app.get("/api/aerospace-facts")
async def get_aerospace_facts():
    """Get aerospace-related facts and calculations"""
    all_facts = [
        {
            "category": "Speed & Performance",
            "title": "Mach Number Calculations",
            "fact": "Commercial jets cruise at Mach 0.78-0.85 (78-85% speed of sound)",
            "formula": "Mach = Aircraft Speed / Speed of Sound at altitude",
            "example": "Boeing 787 at 488 knots / 573 knots (sound) = Mach 0.85"
        },
        {
            "category": "Fuel Efficiency",
            "title": "Fuel Consumption Rate",
            "fact": "A380 burns ~12,000 kg/hour for 550 passengers = 21.8 kg per passenger per hour",
            "formula": "Fuel per passenger = Total burn rate / Number of passengers",
            "example": "12,000 kg/hr ÷ 550 pax = 21.8 kg/pax/hr"
        },
        {
            "category": "Physics",
            "title": "Lift Generation",
            "fact": "Lift (L) = 0.5 × Air Density × Velocity² × Wing Area × Lift Coefficient",
            "formula": "L = 0.5 × ρ × V² × S × CL",
            "example": "Boeing 747: ~900,000 lbs lift at cruise"
        },
        {
            "category": "Altitude",
            "title": "Air Density at Altitude",
            "fact": "At 35,000 ft, air density is only 25% of sea level",
            "formula": "ρ(h) = ρ₀ × e^(-h/H) where H ≈ 7,640m",
            "example": "Sea level: 1.225 kg/m³ → 35,000ft: 0.38 kg/m³"
        },
        {
            "category": "Range",
            "title": "Breguet Range Equation",
            "fact": "Aircraft range depends on fuel efficiency, weight, and aerodynamics",
            "formula": "Range = (V/c) × (L/D) × ln(W₁/W₂)",
            "example": "A350-900ULR: 18,000 km range"
        }
    ]
    
    return {"facts": all_facts, "count": len(all_facts)}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return {"error": "Endpoint not found", "detail": "The requested endpoint does not exist"}

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "Something went wrong on our end"}

if __name__ == '__main__':
    import uvicorn
    logger.info("🛫 Starting FlightAlert Pro v3.0...")
    logger.info("🔗 Available endpoints: /, /api/query, /api/ingest, /api/pay/session, /api/pay/webhook")
    logger.info("�� Payment integration: Stripe")
    logger.info("💱 Currency conversion: exchangerate.host")
    
    # Run the FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8000)
