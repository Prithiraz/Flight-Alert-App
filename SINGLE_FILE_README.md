# FlightAlert Pro - Single-File Implementation

## 🎯 Overview

This is a **complete, production-ready Flight Alert application** consolidated into a single `main.py` file. Everything you need to run a sophisticated flight search and alert system is contained in one file.

## ✨ Features

### Core Functionality
- ✈️ **Flight Search** - Real-time search with Amadeus API + enhanced mock data fallback
- 💳 **Stripe Payments** - £5/month subscription or £70 lifetime access
- 🔒 **Payment Enforcement** - No search without active subscription
- 🔔 **Price Alerts** - Set alerts and get notified when prices drop
- 🗺️ **Live Flight Map** - Real-time aircraft tracking with Leaflet.js
- 🦄 **Rare Aircraft Filter** - Find flights on special aircraft (A380, 747-8, Concorde routes)
- 💱 **Multi-Currency** - GBP, USD, EUR, AED, AUD, CAD with live conversion
- 🎨 **Beautiful UI** - Modern gradient design with responsive layout

### Technical Highlights
- **Single File** - All backend, frontend, data, and logic in one file
- **Auto-Initialize** - Database and tables created automatically
- **Zero Config** - Works out of the box with demo data
- **Production Ready** - Full error handling and proper HTTP status codes
- **Background Tasks** - Automatic alert checking every 5 minutes

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install flask requests stripe

# Run the application
python3 main.py
```

Then open your browser to: **http://localhost:8000**

### That's it! 🎉

The app will:
1. ✅ Auto-create SQLite database
2. ✅ Initialize all required tables
3. ✅ Start Flask server on port 8000
4. ✅ Launch background alert checker
5. ✅ Serve beautiful web interface

## 📖 Usage Guide

### 1. Subscribe to a Plan

Visit the dashboard and choose:
- **Monthly Plan**: £5/month
- **Lifetime Plan**: £70 one-time

### 2. Search for Flights

After subscribing, you'll receive a token. Use it to:
- Search flights between any airports
- Filter by price, currency, or rare aircraft
- View detailed flight information
- Get booking links

### 3. Create Price Alerts

Set maximum prices for routes and get notified when flights drop below your threshold.

## 🔧 Configuration

### Environment Variables (Optional)

```bash
# Stripe Keys (Required for production)
export STRIPE_SECRET_KEY="sk_live_..."
export STRIPE_PUBLISHABLE_KEY="pk_live_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."

# Flight API Keys (Optional - uses mock data if not provided)
export AMADEUS_CLIENT_ID="your_amadeus_client_id"
export AMADEUS_CLIENT_SECRET="your_amadeus_client_secret"

# Currency API (Optional - uses static rates if not provided)
export EXCHANGE_RATE_API_KEY="your_api_key"

# JWT Secret (Optional - auto-generated if not provided)
export JWT_SECRET="your_secret_key"
```

### Demo Mode

Without API keys, the app uses:
- ✅ Enhanced mock flight data
- ✅ Static exchange rates
- ✅ Simulated Stripe payments (auto-activates subscriptions)

Perfect for testing and development!

## 📡 API Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard UI |
| `/map` | GET | Live flight map |
| `/api/status` | GET | API health check |
| `/api/pay` | POST | Create payment session |

### Protected Endpoints (Require Authentication)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Search flights |
| `/api/alerts` | GET | List price alerts |
| `/api/add-alert` | POST | Create price alert |

## 🧪 API Examples

### 1. Subscribe and Get Token

```bash
curl -X POST http://localhost:8000/api/pay \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "subscription_type": "lifetime"
  }'
```

Response:
```json
{
  "success": true,
  "demo_token": "dGVzdEBleGFtcGxlLmNvbToyMDI1...",
  "checkout_url": "https://checkout.stripe.com/pay/...",
  "message": "In production, redirect user to checkout_url"
}
```

### 2. Search for Flights

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "departure": "LHR",
    "arrival": "JFK",
    "date": "2025-12-15",
    "currency": "USD",
    "rare_aircraft_only": false
  }'
```

Response:
```json
{
  "success": true,
  "results": {
    "count": 12,
    "flights": [
      {
        "flight_number": "BA178",
        "airline_name": "BA (British Airways)",
        "departure": "LHR",
        "departure_airport": "Heathrow Airport",
        "arrival": "JFK",
        "arrival_airport": "John F. Kennedy International Airport",
        "price": 342.93,
        "currency": "USD",
        "aircraft": "Boeing 777-300ER",
        "is_rare_aircraft": true,
        "booking_link": "https://www.britishairways.com"
      }
    ]
  }
}
```

### 3. Create Price Alert

```bash
curl -X POST http://localhost:8000/api/add-alert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "departure": "LHR",
    "arrival": "JFK",
    "max_price": 300,
    "currency": "GBP"
  }'
```

## 🗄️ Database Schema

The app automatically creates these SQLite tables:

### users
- `id` - Primary key
- `email` - User email (unique)
- `subscription_type` - "monthly" or "lifetime"
- `subscription_status` - "active", "expired", or "cancelled"
- `subscription_start` - Start date
- `subscription_end` - End date (for monthly)
- `stripe_customer_id` - Stripe customer ID
- `api_calls_today` - API usage counter

### alerts
- `id` - Primary key
- `user_email` - Foreign key to users
- `departure` - Airport code
- `arrival` - Airport code
- `max_price` - Alert threshold
- `currency` - Price currency
- `active` - Boolean flag
- `last_checked` - Last check timestamp

### flight_searches
- `id` - Primary key
- `user_email` - Foreign key to users
- `departure` - Airport code
- `arrival` - Airport code
- `search_date` - Search date
- `results_count` - Number of results found

## 📊 Built-in Data

### Airlines (24+)
BA, AA, DL, UA, EK, QR, LH, AF, KL, SQ, QF, CX, NH, JL, TK, VS, AC, NZ, FR, U2, WN, B6, AS, F9

### Airports (40+)
JFK, LAX, ORD, LHR, CDG, AMS, DXB, SIN, NRT, SYD, and many more with full names

### Rare Aircraft (10)
- Concorde (rarity: 10)
- Boeing 747-8 (rarity: 9)
- Airbus A380 (rarity: 8)
- Boeing 747SP (rarity: 10)
- And more...

## 🎨 UI Features

- **Gradient Design**: Blue → Purple gradient
- **Stats Cards**: Live metrics display
- **Pricing Cards**: Interactive subscription options
- **Search Form**: Comprehensive flight search
- **Alert Management**: Create and view alerts
- **Live Map**: Real-time flight tracking

## 🔒 Security Features

- JWT-based authentication (simplified for demo)
- Payment verification before API access
- SQL injection prevention (parameterized queries)
- Error messages don't leak sensitive info
- Subscription expiration checking

## 🚨 Error Handling

All endpoints return proper HTTP status codes:
- `200` - Success
- `400` - Bad request (missing parameters)
- `401` - Unauthorized (no auth token)
- `402` - Payment required (subscription expired)
- `500` - Internal server error

## 📝 Code Structure

```python
main.py (1,300+ lines)
├── Configuration (Stripe, API keys, database)
├── Database Setup (auto-initialization)
├── Data (airlines, airports, rare aircraft)
├── Currency Conversion (live rates + static fallback)
├── Flight Search Logic (Amadeus API + mock data)
├── Authentication & Payment (JWT + Stripe)
├── Flask Application Setup
├── HTML Templates (embedded as strings)
│   ├── Dashboard (search, alerts, pricing)
│   └── Live Map (Leaflet.js visualization)
├── API Routes (7 endpoints)
└── Background Tasks (alert checking)
```

## 🌟 Production Deployment

### For Production Use:

1. **Set Real Stripe Keys**
   ```bash
   export STRIPE_SECRET_KEY="sk_live_..."
   export STRIPE_PUBLISHABLE_KEY="pk_live_..."
   ```

2. **Configure Amadeus API**
   ```bash
   export AMADEUS_CLIENT_ID="your_id"
   export AMADEUS_CLIENT_SECRET="your_secret"
   ```

3. **Use Production WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 main:app
   ```

4. **Enable HTTPS** (required for Stripe)
   - Use reverse proxy (nginx)
   - Configure SSL certificates

5. **Set Strong JWT Secret**
   ```bash
   export JWT_SECRET="$(openssl rand -hex 32)"
   ```

## 🐛 Troubleshooting

### Database Issues
```bash
# Delete database and restart to recreate
rm flight_alert.db
python3 main.py
```

### Port Already in Use
```bash
# Change port in main.py (last line):
app.run(host='0.0.0.0', port=9000, debug=False)
```

### Import Errors
```bash
# Reinstall dependencies
pip install --upgrade flask requests stripe
```

## 📄 License

This is a demo/educational implementation. For production use, ensure compliance with:
- Stripe terms of service
- Amadeus API terms
- Airline booking regulations
- Data protection laws (GDPR, etc.)

## 🙏 Credits

Built as a comprehensive single-file solution demonstrating:
- Flask web development
- Payment integration
- Real-time data processing
- Modern UI/UX design
- Production-ready architecture

---

**FlightAlert Pro** - Your complete flight search solution in a single file! ✈️
