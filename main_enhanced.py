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

# HTML template for the main page
MAIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Flight Alert App v3.0 - Premium Flight Search</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .container { 
            max-width: 1200px; margin: 0 auto; 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(45deg, #1e3c72, #2a5298); 
            color: white; 
            padding: 40px; 
            text-align: center; 
        }
        .header h1 { margin: 0; font-size: 3em; font-weight: 300; }
        .header p { margin: 10px 0; opacity: 0.9; font-size: 1.2em; }
        .pricing { 
            display: flex; 
            justify-content: center; 
            gap: 30px; 
            padding: 40px; 
            background: #f8f9fa;
        }
        .price-card { 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center; 
            flex: 1; 
            max-width: 300px;
        }
        .price-card.featured { 
            border: 3px solid #667eea; 
            transform: scale(1.05);
        }
        .price { font-size: 2.5em; color: #667eea; font-weight: bold; }
        .button { 
            background: #667eea; 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 1.1em;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
        }
        .button:hover { background: #5a6fd8; }
        .features { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 30px; 
            padding: 40px; 
        }
        .feature { 
            background: #f8f9fa; 
            padding: 30px; 
            border-radius: 10px; 
            border-left: 4px solid #667eea;
        }
        .endpoints { 
            padding: 40px; 
            background: #f1f3f4;
        }
        .endpoint { 
            background: white; 
            margin: 10px 0; 
            padding: 20px; 
            border-radius: 5px; 
            border-left: 4px solid #28a745;
        }
        .method { 
            color: white; 
            padding: 5px 10px; 
            border-radius: 3px; 
            font-weight: bold; 
            margin-right: 10px;
        }
        .get { background: #007bff; }
        .post { background: #28a745; }
        .aerospace-facts { 
            padding: 40px; 
            background: linear-gradient(135deg, #74b9ff, #0984e3);
            color: white;
        }
        .fact-card { 
            background: rgba(255,255,255,0.1); 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        .rare-aircraft { 
            padding: 40px; 
            background: #2d3436;
            color: white;
        }
        .aircraft-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-top: 20px;
        }
        .aircraft-card { 
            background: #636e72; 
            padding: 20px; 
            border-radius: 10px;
        }
        .rarity { 
            color: #fdcb6e; 
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✈️ Flight Alert App v3.0</h1>
            <p>Premium Flight Search & Alert System</p>
            <p><strong>Real-time data • Advanced filtering • Rare aircraft tracking</strong></p>
        </div>

        <div class="pricing">
            <div class="price-card">
                <h3>Monthly Subscription</h3>
                <div class="price">£5</div>
                <p>per month</p>
                <ul style="text-align: left; margin: 20px 0;">
                    <li>Unlimited flight searches</li>
                    <li>Real-time price alerts</li>
                    <li>Multi-currency support</li>
                    <li>Basic aircraft filters</li>
                </ul>
                <button class="button" onclick="subscribe('monthly')">Subscribe Monthly</button>
            </div>
            
            <div class="price-card featured">
                <h3>Lifetime Access</h3>
                <div class="price">£70</div>
                <p>one-time payment</p>
                <ul style="text-align: left; margin: 20px 0;">
                    <li>Everything in Monthly</li>
                    <li>Rare aircraft tracking</li>
                    <li>Live flight radar</li>
                    <li>Aerospace calculations</li>
                    <li>Priority support</li>
                </ul>
                <button class="button" onclick="subscribe('lifetime')">Get Lifetime Access</button>
            </div>
        </div>

        <div class="features">
            <div class="feature">
                <h3>🎯 Advanced Flight Search</h3>
                <p>Search across multiple airlines with real-time pricing from Amadeus, Skyscanner, and other premium APIs.</p>
            </div>
            <div class="feature">
                <h3>💰 Smart Price Alerts</h3>
                <p>Set price thresholds and get notified when flights drop below your target price.</p>
            </div>
            <div class="feature">
                <h3>🌍 Multi-Currency Support</h3>
                <p>View prices in GBP, USD, EUR, and 10+ other currencies with live exchange rates.</p>
            </div>
            <div class="feature">
                <h3>✈️ Rare Aircraft Tracking</h3>
                <p>Special filters for plane enthusiasts to find flights on rare aircraft like A380, Concorde routes, and vintage planes.</p>
            </div>
            <div class="feature">
                <h3>🗺️ Live Flight Radar</h3>
                <p>Real-time aircraft tracking with simplified ATC-style global map showing live flights.</p>
            </div>
            <div class="feature">
                <h3>📊 Aerospace Insights</h3>
                <p>Educational content with flight calculations, aircraft specifications, and aviation facts.</p>
            </div>
        </div>

        <div class="aerospace-facts">
            <h2>🚀 Aerospace Facts & Calculations</h2>
            {% for fact in aerospace_facts %}
            <div class="fact-card">
                <h4>{{ fact.title }}</h4>
                <p>{{ fact.fact }}</p>
                <small><strong>Calculation:</strong> {{ fact.calculation }}</small>
            </div>
            {% endfor %}
        </div>

        <div class="rare-aircraft">
            <h2>🦄 Rare Aircraft Database</h2>
            <p>Track flights on the world's most exclusive and rare aircraft</p>
            <div class="aircraft-grid">
                {% for aircraft, info in rare_aircraft.items() %}
                <div class="aircraft-card">
                    <h4>{{ aircraft }}</h4>
                    <p><strong>Manufacturer:</strong> {{ info.manufacturer }}</p>
                    <p><strong>Status:</strong> {{ info.status }}</p>
                    <p><strong>Max Speed:</strong> Mach {{ info.max_speed_mach }}</p>
                    <p class="rarity">Rarity: {{ info.rarity }}/10</p>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="endpoints">
            <h2>🚀 API Endpoints</h2>
            <p><strong>All endpoints require valid subscription and authentication token</strong></p>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/auth/subscribe</strong> - Create subscription and payment session
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/auth/login</strong> - Login and get access token
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/flights/search</strong> - Premium flight search with real APIs
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/flights/rare</strong> - Search for rare aircraft flights
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/airports</strong> - Get comprehensive airport database
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/airlines</strong> - Get airline database with IATA codes
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/currency/rates</strong> - Get live currency exchange rates
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/flights/live-map</strong> - Live aircraft tracking data
            </div>
        </div>
    </div>

    <script>
        function subscribe(type) {
            const email = prompt("Enter your email address:");
            if (!email) return;

            fetch('/api/auth/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, subscription_type: type })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = data.checkout_url;
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    """Enhanced home page with payment integration"""
    return render_template_string(
        MAIN_PAGE_HTML, 
        aerospace_facts=AEROSPACE_FACTS[:4],
        rare_aircraft=dict(list(RARE_AIRCRAFT_DB.items())[:8])
    )

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