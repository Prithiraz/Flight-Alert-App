#!/usr/bin/env python3
"""
Flight Alert App v3.0 - Enhanced Commercial Version
Advanced flight search with payment integration, real APIs, and premium features
"""

import logging
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g, render_template_string
import stripe
from typing import Dict, Any, Optional, List
import json

# Import our custom modules
from config import settings
from models import db, User, FlightQuery, PaymentRequest, SubscriptionType, SubscriptionStatus
from auth import require_payment, generate_token, create_stripe_checkout_session, handle_stripe_webhook
from flight_apis import flight_provider, AIRPORTS_DB, AIRLINES_DB, RARE_AIRCRAFT_DB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = settings.jwt_secret_key

# Configure Stripe
stripe.api_key = settings.stripe_secret_key

# Aerospace facts and calculations for educational content
AEROSPACE_FACTS = [
    {
        "title": "Fastest Commercial Aircraft",
        "fact": "The Concorde could fly at Mach 2.04 (2,180 km/h), making it the fastest commercial airliner ever built.",
        "calculation": "At cruising speed, Concorde could fly from London to New York in 3.5 hours vs 8 hours for subsonic aircraft."
    },
    {
        "title": "Fuel Efficiency",
        "fact": "Modern aircraft like the A350 consume approximately 2.9 liters of fuel per 100 passenger-kilometers.",
        "calculation": "A Boeing 787 uses about 20% less fuel than previous generation aircraft of similar size."
    },
    {
        "title": "Flight Altitude",
        "fact": "Commercial aircraft typically cruise at 35,000-42,000 feet to optimize fuel efficiency and avoid weather.",
        "calculation": "At 40,000 feet, air density is only 23% of sea level, reducing drag significantly."
    },
    {
        "title": "Takeoff Speed",
        "fact": "A Boeing 747 typically takes off at speeds between 160-180 mph (257-290 km/h).",
        "calculation": "Takeoff speed varies with aircraft weight: heavier aircraft need higher speeds to generate sufficient lift."
    }
]

# HTML template for the main page - Modern FlightAlert Pro Dashboard
MAIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlightAlert Pro - Smart Flight Search & Alerts</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }
        
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 2rem;
        }
        
        .logo {
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            text-decoration: none;
        }
        
        .nav-buttons {
            display: flex;
            gap: 1rem;
        }
        
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s ease;
            display: inline-block;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5a67d8;
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: transparent;
            color: #667eea;
            border: 2px solid #667eea;
        }
        
        .btn-secondary:hover {
            background: #667eea;
            color: white;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }
        
        .hero {
            text-align: center;
            padding: 4rem 0;
            color: white;
        }
        
        .hero h1 {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #fff, #e2e8f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .hero p {
            font-size: 1.25rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }
        
        .search-section {
            background: white;
            border-radius: 20px;
            padding: 3rem;
            margin: 2rem 0;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        
        .search-form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
        }
        
        .form-group label {
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #4a5568;
        }
        
        .form-group input, .form-group select {
            padding: 1rem;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .search-btn {
            grid-column: 1 / -1;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 1.25rem;
            border: none;
            border-radius: 12px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .search-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }
        
        .feature-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
        }
        
        .feature-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .feature-card h3 {
            font-size: 1.4rem;
            margin-bottom: 1rem;
            color: #2d3748;
        }
        
        .feature-card p {
            color: #4a5568;
            line-height: 1.6;
        }
        
        .stats-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 3rem;
            margin: 3rem 0;
            text-align: center;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }
        
        .stat-item {
            padding: 1.5rem;
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: #667eea;
            display: block;
        }
        
        .stat-label {
            color: #4a5568;
            font-weight: 600;
            margin-top: 0.5rem;
        }
        
        .benefits-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 3rem;
            margin: 3rem 0;
        }
        
        .benefits-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        
        .benefit-item {
            display: flex;
            align-items: center;
            padding: 1rem;
            background: #f7fafc;
            border-radius: 12px;
        }
        
        .benefit-item::before {
            content: '✓';
            color: #48bb78;
            font-weight: bold;
            font-size: 1.2rem;
            margin-right: 1rem;
        }
        
        .cta-section {
            background: linear-gradient(45deg, #4299e1, #667eea);
            color: white;
            text-align: center;
            padding: 4rem;
            border-radius: 20px;
            margin: 3rem 0;
        }
        
        .cta-section h2 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .cta-section p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }
        
        .tracking-map {
            background: #2d3748;
            border-radius: 16px;
            padding: 2rem;
            margin: 2rem 0;
            color: white;
            text-align: center;
            min-height: 300px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        
        .map-placeholder {
            width: 100%;
            height: 200px;
            background: linear-gradient(45deg, #4a5568, #2d3748);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            margin-bottom: 1rem;
        }
        
        @media (max-width: 768px) {
            .hero h1 {
                font-size: 2.5rem;
            }
            
            .search-form {
                grid-template-columns: 1fr;
            }
            
            .nav-container {
                flex-direction: column;
                gap: 1rem;
            }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="nav-container">
            <a href="/" class="logo">FlightAlert Pro</a>
            <div class="nav-buttons">
                <a href="#" class="btn btn-secondary" onclick="showLogin()">Login</a>
                <a href="#" class="btn btn-primary" onclick="showSignup()">Sign Up</a>
            </div>
        </div>
    </header>

    <main>
        <section class="hero">
            <div class="container">
                <h1>FlightAlert Pro</h1>
                <p>Get instant alerts for flight deals, rare aircraft, and delays. Never miss a great flight deal again!</p>
            </div>
        </section>

        <section class="container">
            <div class="search-section">
                <h2 style="text-align: center; margin-bottom: 2rem; color: #2d3748; font-size: 2rem;">Smart Flight Search</h2>
                <p style="text-align: center; margin-bottom: 2rem; color: #4a5568;">Search across 100+ airlines and booking sites to find the best deals. Our AI-powered system tracks prices 24/7.</p>
                
                <form class="search-form" onsubmit="searchFlights(event)">
                    <div class="form-group">
                        <label for="from">From</label>
                        <input type="text" id="from" placeholder="Departure city or airport" required>
                    </div>
                    <div class="form-group">
                        <label for="to">To</label>
                        <input type="text" id="to" placeholder="Destination city or airport" required>
                    </div>
                    <div class="form-group">
                        <label for="departure">Departure</label>
                        <input type="date" id="departure" required>
                    </div>
                    <div class="form-group">
                        <label for="return">Return (Optional)</label>
                        <input type="date" id="return">
                    </div>
                    <div class="form-group">
                        <label for="passengers">Passengers</label>
                        <select id="passengers">
                            <option value="1">1 Passenger</option>
                            <option value="2">2 Passengers</option>
                            <option value="3">3 Passengers</option>
                            <option value="4">4+ Passengers</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="class">Class</label>
                        <select id="class">
                            <option value="economy">Economy</option>
                            <option value="premium">Premium Economy</option>
                            <option value="business">Business</option>
                            <option value="first">First Class</option>
                        </select>
                    </div>
                    <button type="submit" class="search-btn">🔍 Search Flights</button>
                </form>
            </div>

            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">🔍</div>
                    <h3>Smart Flight Search</h3>
                    <p>Search across 100+ airlines and booking sites to find the best deals. Our AI-powered system tracks prices 24/7.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🚨</div>
                    <h3>Instant Alerts</h3>
                    <p>Get notified immediately when flight prices drop, rare aircraft are spotted, or your flight is delayed.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🗺️</div>
                    <h3>Live Flight Tracking</h3>
                    <p>Track flights in real-time with our 3D map. Monitor delays, airport conditions, and trending routes.</p>
                </div>
            </div>

            <div class="tracking-map">
                <h3 style="margin-bottom: 1rem;">Live Flight Tracking</h3>
                <div class="map-placeholder">
                    🌍 3D Flight Map - Real-time Aircraft Tracking
                </div>
                <p>Interactive map showing live flights, delays, and routing information</p>
            </div>

            <div class="benefits-section">
                <h2 style="text-align: center; margin-bottom: 1rem; color: #2d3748;">Why Choose FlightAlert Pro?</h2>
                <div class="benefits-list">
                    <div class="benefit-item">Real-time price monitoring across 100+ booking sites</div>
                    <div class="benefit-item">Instant notifications via email and push alerts</div>
                    <div class="benefit-item">Advanced filters for airlines, airports, and budgets</div>
                    <div class="benefit-item">Premium features including 3D flight maps</div>
                </div>
            </div>

            <div class="stats-section">
                <h2 style="color: #2d3748; margin-bottom: 1rem;">Live Flight Stats</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-number">12,847</span>
                        <div class="stat-label">Flights Tracked</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">195</span>
                        <div class="stat-label">Countries</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">37,000ft</span>
                        <div class="stat-label">Avg Altitude</div>
                    </div>
                </div>
            </div>

            <div class="cta-section">
                <h2>Ready to Start Saving?</h2>
                <p>Join thousands of travelers who save money with FlightAlert Pro</p>
                <a href="#" class="btn btn-primary" onclick="showSignup()" style="font-size: 1.2rem; padding: 1rem 2rem;">Get Started Now</a>
            </div>
        </section>
    </main>

    <script>
        // Define functions first
        function showLogin() {
            const email = prompt("Enter your email to login:");
            if (email) {
                fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Login successful! Token: ' + data.token.substring(0, 20) + '...');
                    } else {
                        alert('Login failed: ' + data.error);
                    }
                })
                .catch(err => alert('Login error: ' + err.message));
            }
        }

        function showSignup() {
            const email = prompt("Enter your email to sign up:");
            if (email) {
                const subscriptionType = confirm("Choose subscription:\nOK for Monthly (£5/month)\nCancel for Lifetime (£70 one-time)") ? 'monthly' : 'lifetime';
                
                fetch('/api/auth/subscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, subscription_type: subscriptionType })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = data.checkout_url;
                    } else {
                        alert('Signup failed: ' + data.error);
                    }
                })
                .catch(err => alert('Signup error: ' + err.message));
            }
        }

        function searchFlights(event) {
            event.preventDefault();
            
            const formData = {
                from: document.getElementById('from').value,
                to: document.getElementById('to').value,
                departure: document.getElementById('departure').value,
                return: document.getElementById('return').value,
                passengers: document.getElementById('passengers').value,
                class: document.getElementById('class').value
            };
            
            // For demo purposes, show alert. In real app, this would search flights
            alert(`Searching flights from ${formData.from} to ${formData.to} on ${formData.departure}`);
            
            // In real implementation, this would call the flight search API
            // fetch('/api/flights/search', { method: 'POST', body: JSON.stringify(formData) })
        }

        // Set default departure date to tomorrow
        document.addEventListener('DOMContentLoaded', function() {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            document.getElementById('departure').value = tomorrow.toISOString().split('T')[0];
        });

        // Simulate live stats updates
        setInterval(() => {
            const flightsElement = document.querySelector('.stat-number');
            if (flightsElement) {
                const currentFlights = parseInt(flightsElement.textContent.replace(',', ''));
                const newFlights = currentFlights + Math.floor(Math.random() * 10);
                flightsElement.textContent = newFlights.toLocaleString();
            }
        }, 5000);
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    """Modern FlightAlert Pro dashboard"""
    return MAIN_PAGE_HTML

@app.route('/api/auth/subscribe', methods=['POST'])
def create_subscription():
    """Create subscription and Stripe checkout session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        email = data.get('email')
        subscription_type = data.get('subscription_type')
        
        if not email or not subscription_type:
            return jsonify({'error': 'Email and subscription_type required'}), 400
        
        if subscription_type not in ['monthly', 'lifetime']:
            return jsonify({'error': 'Invalid subscription type'}), 400
        
        # Create Stripe checkout session
        session_result = create_stripe_checkout_session(email, subscription_type)
        
        if session_result['success']:
            return jsonify({
                'success': True,
                'checkout_url': session_result['checkout_url'],
                'session_id': session_result['session_id']
            })
        else:
            return jsonify({
                'success': False,
                'error': session_result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Subscription creation error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint for existing subscribers"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        user = db.get_user_by_email(email)
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'Please subscribe first',
                'subscribe_url': '/api/auth/subscribe'
            }), 404
        
        if user.subscription_status != SubscriptionStatus.ACTIVE:
            return jsonify({
                'error': 'Subscription inactive',
                'message': 'Your subscription has expired',
                'subscribe_url': '/api/auth/subscribe'
            }), 402
        
        # Generate token
        token = generate_token(user.id, user.email)
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'email': user.email,
                'subscription_type': user.subscription_type,
                'subscription_end': user.subscription_end.isoformat() if user.subscription_end else None
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/flights/search', methods=['POST'])
@require_payment
async def search_flights():
    """Premium flight search with real APIs"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No search criteria provided'}), 400
        
        # Parse search criteria
        departure = data.get('departure', '').upper()
        arrival = data.get('arrival', '').upper()
        date = data.get('date')
        max_price = data.get('max_price')
        min_price = data.get('min_price')
        airline = data.get('airline', '').upper()
        currency = data.get('currency', 'GBP').upper()
        rare_aircraft_only = data.get('rare_aircraft_only', False)
        
        if not departure or not arrival:
            return jsonify({
                'error': 'Missing required parameters',
                'message': 'Both departure and arrival airport codes are required'
            }), 400
        
        # Get flights from real APIs
        flights = await flight_provider.search_flights_amadeus(departure, arrival, date)
        
        # Apply filters
        filtered_flights = []
        for flight in flights:
            include = True
            
            # Price filters
            if max_price and flight.get('price_gbp', 0) > max_price:
                include = False
            if min_price and flight.get('price_gbp', 0) < min_price:
                include = False
            
            # Airline filter
            if airline and flight.get('airline_code', '') != airline:
                include = False
            
            # Rare aircraft filter
            if rare_aircraft_only and not flight.get('is_rare_aircraft', False):
                include = False
            
            if include:
                filtered_flights.append(flight)
        
        # Sort by price
        filtered_flights.sort(key=lambda x: x.get('price_gbp', 0))
        
        # Get exchange rates if different currency requested
        exchange_rates = await flight_provider.get_exchange_rates('GBP')
        
        # Convert prices if needed
        if currency != 'GBP':
            rate = exchange_rates.get(currency, 1.0)
            for flight in filtered_flights:
                if 'price_gbp' in flight:
                    flight[f'price_{currency.lower()}'] = round(flight['price_gbp'] * rate, 2)
        
        # Calculate statistics
        if filtered_flights:
            prices = [f.get('price_gbp', 0) for f in filtered_flights]
            avg_price = round(sum(prices) / len(prices), 2)
            min_price_found = min(prices)
            max_price_found = max(prices)
        else:
            avg_price = min_price_found = max_price_found = None
        
        # Get random aerospace fact
        import random
        random_fact = random.choice(AEROSPACE_FACTS)
        
        response = {
            'search_criteria': {
                'departure': departure,
                'arrival': arrival,
                'date': date,
                'currency': currency,
                'rare_aircraft_only': rare_aircraft_only
            },
            'results': {
                'count': len(filtered_flights),
                'flights': filtered_flights[:20],  # Limit to 20 results
                'total_available': len(flights)
            },
            'statistics': {
                'average_price_gbp': avg_price,
                'min_price_gbp': min_price_found,
                'max_price_gbp': max_price_found,
                'currency_used': currency,
                'exchange_rates': exchange_rates if currency != 'GBP' else None
            },
            'aerospace_fact': random_fact,
            'user_info': {
                'api_calls_today': g.current_user.api_calls_today,
                'subscription_type': g.current_user.subscription_type
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Flight search error: {e}")
        return jsonify({
            'error': 'Search failed',
            'message': 'An error occurred while searching for flights'
        }), 500

@app.route('/api/flights/rare', methods=['POST'])
@require_payment
async def search_rare_aircraft():
    """Search for flights with rare aircraft"""
    try:
        data = request.get_json()
        departure = data.get('departure', '').upper()
        arrival = data.get('arrival', '').upper()
        date = data.get('date')
        
        if not departure or not arrival:
            return jsonify({'error': 'Missing departure or arrival'}), 400
        
        # Get all flights and filter for rare aircraft
        flights = await flight_provider.search_flights_amadeus(departure, arrival, date)
        rare_flights = [f for f in flights if f.get('is_rare_aircraft', False)]
        
        # Sort by aircraft rarity
        rare_flights.sort(key=lambda x: x.get('aircraft_info', {}).get('rarity', 0), reverse=True)
        
        return jsonify({
            'search_criteria': {'departure': departure, 'arrival': arrival, 'date': date},
            'rare_aircraft_flights': rare_flights,
            'count': len(rare_flights),
            'aircraft_database': RARE_AIRCRAFT_DB,
            'message': 'Showing flights with rare and special aircraft',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Rare aircraft search error: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/airports', methods=['GET'])
@require_payment
def get_airports():
    """Get comprehensive airport database"""
    return jsonify({
        'airports': AIRPORTS_DB,
        'count': len(AIRPORTS_DB),
        'message': 'Comprehensive airport database with full names',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/airlines', methods=['GET'])
@require_payment
def get_airlines():
    """Get airline database with IATA codes"""
    return jsonify({
        'airlines': AIRLINES_DB,
        'count': len(AIRLINES_DB),
        'message': 'Complete airline database with IATA codes and websites',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/currency/rates', methods=['GET'])
@require_payment
async def get_currency_rates():
    """Get live currency exchange rates"""
    try:
        base_currency = request.args.get('base', 'GBP').upper()
        rates = await flight_provider.get_exchange_rates(base_currency)
        
        return jsonify({
            'base_currency': base_currency,
            'rates': rates,
            'timestamp': datetime.now().isoformat(),
            'message': 'Live currency exchange rates'
        })
    except Exception as e:
        logger.error(f"Currency rates error: {e}")
        return jsonify({'error': 'Failed to fetch rates'}), 500

@app.route('/api/flights/live-map', methods=['GET'])
@require_payment
def get_live_flights():
    """Mock live flight tracking data (simplified ATC view)"""
    # This would integrate with FlightRadar24 or similar APIs in production
    mock_live_flights = [
        {
            'callsign': 'BAW178',
            'airline': 'BA (British Airways)',
            'aircraft': 'Boeing 777-300ER',
            'departure': 'LHR',
            'arrival': 'JFK',
            'latitude': 51.4700,
            'longitude': -0.4543,
            'altitude': 37000,
            'speed': 520,
            'heading': 285,
            'status': 'en_route'
        },
        {
            'callsign': 'AAL100',
            'airline': 'AA (American Airlines)',
            'aircraft': 'Boeing 787-9',
            'departure': 'JFK',
            'arrival': 'LAX',
            'latitude': 40.6413,
            'longitude': -73.7781,
            'altitude': 39000,
            'speed': 485,
            'heading': 245,
            'status': 'climbing'
        }
    ]
    
    return jsonify({
        'live_flights': mock_live_flights,
        'count': len(mock_live_flights),
        'message': 'Live aircraft tracking (simplified ATC view)',
        'note': 'Production version integrates with real flight tracking APIs',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data(as_text=True)
    signature = request.headers.get('Stripe-Signature')
    
    result = handle_stripe_webhook(payload, signature)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@app.route('/payment/success')
def payment_success():
    """Payment success page"""
    return render_template_string("""
    <html>
    <head><title>Payment Successful</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🎉 Payment Successful!</h1>
        <p>Your subscription is now active. You can start using the premium flight search features.</p>
        <p><a href="/api/auth/login">Login to get your access token</a></p>
    </body>
    </html>
    """)

@app.route('/payment/cancel')
def payment_cancel():
    """Payment cancelled page"""
    return render_template_string("""
    <html>
    <head><title>Payment Cancelled</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>Payment Cancelled</h1>
        <p>Your payment was cancelled. You can try again anytime.</p>
        <p><a href="/">Back to home</a></p>
    </body>
    </html>
    """)

@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Valid subscription required to access this endpoint',
        'pricing': {
            'monthly': f'£{settings.monthly_price_gbp}/month',
            'lifetime': f'£{settings.lifetime_price_gbp} one-time'
        },
        'subscribe_url': '/api/auth/subscribe'
    }), 401

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': [
            '/', '/api/auth/subscribe', '/api/auth/login', 
            '/api/flights/search', '/api/airports', '/api/airlines'
        ]
    }), 404

if __name__ == '__main__':
    logger.info("🚀 Starting Flight Alert App v3.0 - Commercial Edition")
    logger.info(f"💰 Pricing: Monthly £{settings.monthly_price_gbp} | Lifetime £{settings.lifetime_price_gbp}")
    logger.info(f"✅ Payment integration: Stripe")
    logger.info(f"🗄️  Database initialized: {db.db_path}")
    logger.info("🔐 All endpoints require valid subscription")
    logger.info(f"🌐 Server starting on http://0.0.0.0:8000")
    
    # Initialize database
    db.init_db()
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=8000, debug=settings.debug)