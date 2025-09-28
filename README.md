# ✈️ Flight Alert App v3.0 - Commercial Edition

## 🚀 Premium Flight Search & Alert System

A comprehensive, commercial-grade flight search application with **real-time data**, **payment integration**, **rare aircraft tracking**, and **aerospace insights**. Built for aviation enthusiasts and professional travelers.

![Flight Alert App v3.0](https://github.com/user-attachments/assets/2903822e-588d-4a8a-aaa4-0c4a51b7e093)

## 💰 Pricing

- **Monthly Subscription**: £5/month - Full access to premium features
- **Lifetime Access**: £70 one-time - All features + priority support

## ✨ Features

### 🎯 **Advanced Flight Search**
- Real-time pricing from **Amadeus**, **Skyscanner**, and premium APIs
- Multi-airline search with **working deep links**
- **IATA codes with full airline names** (e.g., "BA (British Airways)")
- **Real airport names** - no more "(6 airports)" confusion
- Smart filtering by price, duration, aircraft type

### 💰 **Smart Price Alerts**
- Set price thresholds and get notified of deals
- Historical price analysis and predictions
- Currency conversion with live exchange rates

### 🦄 **Rare Aircraft Tracking**
- **Special filters for plane enthusiasts**
- Track flights on rare aircraft: **Concorde routes**, **A380**, **747-8**
- Aircraft rarity scoring (1-10 scale)
- Detailed aircraft specifications and aerospace facts

### 🌍 **Multi-Currency Support**
- View prices in **GBP, USD, EUR** and 10+ currencies
- **Live exchange rates** with automatic conversion
- Currency preference settings

### 🗺️ **Live Flight Radar**
- **Real-time aircraft tracking** (ATC-style simplified view)
- Live flight positions and routes
- Aircraft movement visualization

### 📊 **Aerospace Insights**
- **Educational aerospace facts and calculations**
- Flight performance data and aircraft specifications
- Speed, altitude, fuel efficiency calculations

### 🔐 **Secure Payment System**
- **Stripe integration** for secure payments
- Subscription management with JWT authentication
- **No payment, no service** - strict access control

## 🛠️ Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and configure:

```bash
# Stripe Keys (Required for payments)
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Flight API Keys (Optional - uses enhanced mock data if not provided)
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
SKYSCANNER_API_KEY=your_skyscanner_api_key

# Currency Exchange API
EXCHANGE_RATE_API_KEY=your_exchange_rate_api_key
```

### 3. Run the Application
```bash
python main_enhanced.py
```

Visit `http://localhost:8000` to see the beautiful interface!

## 🔐 API Authentication

**All endpoints require valid subscription and authentication token.**

### Step 1: Subscribe
```bash
curl -X POST http://localhost:8000/api/auth/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "subscription_type": "monthly"}'
```

### Step 2: Complete Payment
Follow the Stripe checkout URL returned from the subscribe endpoint.

### Step 3: Login & Get Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com"}'
```

### Step 4: Use Token for API Calls  
```bash
curl -X POST http://localhost:8000/api/flights/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "departure": "LHR",
    "arrival": "JFK", 
    "currency": "GBP",
    "rare_aircraft_only": false
  }'
```

## 🚀 API Endpoints

### Authentication & Payment
- `POST /api/auth/subscribe` - Create subscription and payment session
- `POST /api/auth/login` - Login and get access token
- `POST /webhook/stripe` - Stripe webhook handler

### Flight Search
- `POST /api/flights/search` - **Premium flight search with real APIs**
- `POST /api/flights/rare` - **Search for rare aircraft flights**
- `GET /api/flights/live-map` - **Live aircraft tracking data**

### Data & Information
- `GET /api/airports` - **Comprehensive airport database with full names**
- `GET /api/airlines` - **Airline database with IATA codes** 
- `GET /api/currency/rates` - **Live currency exchange rates**

## 🛩️ Advanced Features

### Rare Aircraft Search
```bash
curl -X POST http://localhost:8000/api/flights/rare \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "departure": "LHR",
    "arrival": "DXB"
  }'
```

### Multi-Currency Search
```bash
curl -X POST http://localhost:8000/api/flights/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "departure": "JFK",
    "arrival": "LAX",
    "currency": "USD",
    "max_price": 500
  }'
```

## 🎨 User Interface

The application features a **beautiful, responsive web interface** with:
- **Gradient backgrounds** and modern styling
- **Interactive pricing cards** with Stripe integration
- **Aerospace facts section** with educational content
- **Rare aircraft database** showcase
- **API documentation** with endpoint examples

## 🗄️ Database & Storage

- **SQLite database** for user management and subscriptions
- **User authentication** with JWT tokens
- **Payment tracking** with Stripe integration
- **API usage analytics** and rate limiting

## 🔧 Configuration

### Secrets to Add for Production:

```bash
# Stripe (Required)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Flight APIs (Recommended)
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
SKYSCANNER_API_KEY=your_skyscanner_api_key

# Currency (Optional)
EXCHANGE_RATE_API_KEY=your_exchange_rate_api_key
```

## 🎯 Key Improvements Made

### ✅ **Payment Integration**
- Stripe checkout sessions for £5/month and £70 lifetime
- Strict authentication middleware - **no payment, no service**
- Secure JWT-based authentication system

### ✅ **Real Flight Data**
- Integration with Amadeus flight API
- Enhanced mock data with realistic pricing
- **Airline names displayed with IATA codes**: "BA (British Airways)"
- **Full airport names**: "Heathrow Airport" instead of "London, GB (6 airports)"

### ✅ **Rare Aircraft Features**
- **Special search for aviation enthusiasts**
- Rare aircraft database (Concorde, A380, 747-8, etc.)
- Aircraft rarity scoring and specifications
- Aerospace facts and calculations

### ✅ **Professional UI/UX**
- **Beautiful commercial-grade interface**
- Interactive payment cards with Stripe integration
- Responsive design optimized for customers
- Educational aerospace content sections

### ✅ **Multi-Currency Support**
- Live exchange rates with automatic conversion
- Support for GBP, USD, EUR, and 10+ currencies
- Currency preference settings

### ✅ **Live Flight Tracking**
- Mock live aircraft tracking (ATC-style view)
- Ready for FlightRadar24 API integration
- Real-time flight positions and data

## 🚀 Production Deployment

1. Set up **real Stripe keys** in environment variables
2. Configure **Amadeus API credentials** for real flight data
3. Set up **Redis** for caching (optional)
4. Use **production WSGI server** (gunicorn/uwsgi)
5. Configure **SSL/HTTPS** for secure payments

## 📈 Commercial Features

- **£5/month or £70 lifetime pricing**
- **Stripe payment processing**
- **User subscription management**
- **API usage tracking and analytics**
- **Premium feature access control**
- **Priority customer support**

## 🔗 Working Deep Links

All airline deep links are **functional and point to real airline websites**:
- British Airways: https://www.britishairways.com
- American Airlines: https://www.aa.com
- Emirates: https://www.emirates.com
- And many more...

---

**Flight Alert App v3.0** - The most comprehensive commercial flight search solution for aviation professionals and enthusiasts. **Real data, real payments, real results.**