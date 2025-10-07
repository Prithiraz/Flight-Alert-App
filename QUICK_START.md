# 🚀 FlightAlert Pro - Quick Reference

## Installation & Launch (3 Commands)

```bash
pip install flask requests stripe
python3 main.py
# Open http://localhost:8000
```

## What You Get

✅ **Complete Flight Alert App in One File**
- Beautiful web dashboard
- Real-time flight search
- Stripe payment integration
- Price alerts system
- Live flight map
- Multi-currency support
- Rare aircraft filter

## File Overview

| File | Purpose | Size |
|------|---------|------|
| `main.py` | Complete application | 54KB |
| `SINGLE_FILE_README.md` | User guide | 9.2KB |
| `IMPLEMENTATION_COMPLETE.md` | Implementation summary | 9.6KB |
| `validate_main.py` | Validation tests | 6.4KB |

## Quick Test

```bash
# Run validation tests
python3 validate_main.py

# Expected output:
# 🎉 All validation tests passed!
# 7/7 tests passed
```

## API Quick Reference

### Get Status
```bash
curl http://localhost:8000/api/status
```

### Subscribe (Demo Mode)
```bash
curl -X POST http://localhost:8000/api/pay \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "subscription_type": "lifetime"}'
```

### Search Flights
```bash
# Use token from subscribe response
curl -X POST http://localhost:8000/api/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "departure": "LHR",
    "arrival": "JFK",
    "date": "2025-12-15",
    "currency": "USD"
  }'
```

## Features Checklist

- [x] Single-file implementation (main.py)
- [x] Flask backend (7 API endpoints)
- [x] Stripe payments (£5/month, £70 lifetime)
- [x] Payment enforcement (no search without subscription)
- [x] Flight search (Amadeus API + mock fallback)
- [x] Price alerts (SQLite storage)
- [x] Live map (Leaflet.js)
- [x] Rare aircraft filter
- [x] Multi-currency (10 currencies)
- [x] Modern UI (blue→purple gradient)
- [x] Auto-initialize database
- [x] Background alert checking
- [x] Full error handling
- [x] Comprehensive documentation

## Configuration (Optional)

```bash
# Stripe (Required for production)
export STRIPE_SECRET_KEY="sk_live_..."
export STRIPE_PUBLISHABLE_KEY="pk_live_..."

# Flight API (Optional)
export AMADEUS_CLIENT_ID="your_id"
export AMADEUS_CLIENT_SECRET="your_secret"

# Currency API (Optional)
export EXCHANGE_RATE_API_KEY="your_key"
```

## Production Deployment

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

## Troubleshooting

**Port in use?**
```bash
# Edit last line in main.py:
app.run(host='0.0.0.0', port=9000, debug=False)
```

**Database issues?**
```bash
rm flight_alert.db
python3 main.py  # Will auto-recreate
```

**Import errors?**
```bash
pip install --upgrade flask requests stripe
```

## Support

📚 See `SINGLE_FILE_README.md` for detailed documentation  
📊 See `IMPLEMENTATION_COMPLETE.md` for full implementation details  
🧪 Run `python3 validate_main.py` to test installation

## Key Statistics

- **Code**: 1,300+ lines
- **Dependencies**: 3 packages
- **Airlines**: 24
- **Airports**: 33
- **Currencies**: 10
- **Endpoints**: 7
- **Tests**: 7/7 passing

---

**Ready to fly! ✈️** Launch with `python3 main.py`
