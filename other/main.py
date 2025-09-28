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
TEMPLATE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "templates")

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
    """Main query endpoint - saves query and triggers search"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Insert query into database
    cur.execute("""INSERT INTO queries (user_id, departure_iata, arrival_iata, depart_date, return_date,
                 passengers, cabin, min_price, max_price, alert_price, currency, rare_aircraft_filter, status)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user['id'], q.departure_iata.upper(), q.arrival_iata.upper(), q.depart_date,
                 q.return_date, q.passengers, q.cabin, q.min_price, q.max_price, q.alert_price,
                 q.currency.upper(), q.rare_aircraft_filter, "pending"))
    conn.commit()
    query_id = cur.lastrowid
    conn.close()

    # Log query creation
    logger.info(f"�� Created query {query_id}: {q.departure_iata} → {q.arrival_iata} on {q.depart_date}")

    # TODO: Trigger search pipeline (Duffel/BYOB/Playwright)
    
    return {"ok": True, "query_id": query_id, "status": "accepted"}

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
