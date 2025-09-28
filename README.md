# Flight-Alert-App

A Flask-based flight search and alert application with REST API endpoints.

## Features

- Flight search API with filtering capabilities
- Advanced flight search with airline deep links and external API integration
- Real-time flight status information
- RESTful API endpoints
- Error handling and logging
- Price alert system
- Support for multiple airline APIs (including Ryanair integration)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### GET /
Home endpoint with API information

### GET /api/status
Check API status and availability

### POST /api/query
Search for flights with the following JSON parameters:
- `departure` (required): Departure airport code (e.g., "JFK")
- `arrival` (required): Arrival airport code (e.g., "LAX")  
- `date` (optional): Travel date
- `max_price` (optional): Maximum price filter

### POST /api/advanced-search
Advanced flight search with airline deep links and external API integration:
- `departure` (required): Departure airport code (e.g., "JFK")
- `arrival` (required): Arrival airport code (e.g., "LAX")
- `date` (optional): Travel date
- `airline` (optional): Preferred airline

Example request:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"departure": "JFK", "arrival": "LAX", "max_price": 300}'
```

Advanced search example:
```bash
curl -X POST http://localhost:8000/api/advanced-search \
  -H "Content-Type: application/json" \
  -d '{"departure": "JFK", "arrival": "LAX", "date": "2024-01-15"}'
```

## Testing

1. First, start the application:
```bash
python main.py
```

2. In another terminal, run the test script to verify all endpoints:
```bash
python test_api.py
```

## Fixed Issues

- ✅ Resolved HTTP 404 error for POST /api/query endpoint
- ✅ Added proper API routing and error handling
- ✅ Implemented flight search functionality
- ✅ Added missing "ryanair" import functionality
- ✅ Implemented missing "create_query" function
- ✅ Added missing "deep_airline_urls" variable
- ✅ Enhanced application with advanced search capabilities and external API integrations