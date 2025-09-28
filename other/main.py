#!/usr/bin/env python3
"""
Flight Alert App - Main Application
Provides flight search and alert functionality via REST API
"""

import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from typing import Dict, Any, Optional
import urllib.parse

# Mock ryanair module - in a real app this would be a proper airline API integration
class ryanair:
    @staticmethod
    def get_flights(departure, arrival, date=None):
        """Mock Ryanair API integration"""
        return {
            "flights": [],
            "status": "success",
            "airline": "Ryanair"
        }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Flight Alert App", version="2.0.0")
templates = Jinja2Templates(directory="templates")

# Pydantic models for request/response validation
class FlightQuery(BaseModel):
    departure: str
    arrival: str
    date: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    airline: Optional[str] = None
    max_duration: Optional[int] = None
    alert_price: Optional[float] = None

class AdvancedSearchQuery(BaseModel):
    departure: str
    arrival: str
    date: Optional[str] = None
    airline: Optional[str] = None

# Mock flight data for demonstration (in a real app, this would connect to airline APIs)
MOCK_FLIGHTS = [
    # JFK to LAX routes
    {
        "flight_number": "AA123",
        "airline": "American Airlines",
        "departure": "JFK",
        "arrival": "LAX",
        "departure_time": "2024-01-15T06:00:00",
        "arrival_time": "2024-01-15T09:30:00",
        "price": 299.99,
        "status": "on_time",
        "aircraft": "Boeing 737-800",
        "duration_minutes": 390
    },
    {
        "flight_number": "DL456",
        "airline": "Delta Air Lines",
        "departure": "JFK",
        "arrival": "LAX",
        "departure_time": "2024-01-15T10:00:00",
        "arrival_time": "2024-01-15T13:30:00",
        "price": 325.50,
        "status": "on_time",
        "aircraft": "Airbus A321",
        "duration_minutes": 390
    },
    {
        "flight_number": "UA789",
        "airline": "United Airlines",
        "departure": "JFK",
        "arrival": "LAX",
        "departure_time": "2024-01-15T18:00:00",
        "arrival_time": "2024-01-15T21:30:00",
        "price": 275.00,
        "status": "on_time",
        "aircraft": "Boeing 777-200",
        "duration_minutes": 390
    },
    # LAX to ORD routes
    {
        "flight_number": "UA456",
        "airline": "United Airlines", 
        "departure": "LAX",
        "arrival": "ORD",
        "departure_time": "2024-01-15T14:00:00",
        "arrival_time": "2024-01-15T19:45:00",
        "price": 245.50,
        "status": "delayed",
        "aircraft": "Boeing 737-900",
        "duration_minutes": 285
    },
    {
        "flight_number": "AA654",
        "airline": "American Airlines", 
        "departure": "LAX",
        "arrival": "ORD",
        "departure_time": "2024-01-15T08:30:00",
        "arrival_time": "2024-01-15T14:15:00",
        "price": 289.99,
        "status": "on_time",
        "aircraft": "Boeing 737-800",
        "duration_minutes": 285
    },
    # ORD to JFK routes
    {
        "flight_number": "DL789",
        "airline": "Delta Air Lines",
        "departure": "ORD",
        "arrival": "JFK", 
        "departure_time": "2024-01-15T16:30:00",
        "arrival_time": "2024-01-15T19:15:00",
        "price": 312.75,
        "status": "on_time",
        "aircraft": "Airbus A320",
        "duration_minutes": 165
    },
    {
        "flight_number": "UA321",
        "airline": "United Airlines",
        "departure": "ORD",
        "arrival": "JFK", 
        "departure_time": "2024-01-15T11:00:00",
        "arrival_time": "2024-01-15T13:45:00",
        "price": 298.50,
        "status": "on_time",
        "aircraft": "Boeing 737-800",
        "duration_minutes": 165
    },
    # Additional popular routes
    {
        "flight_number": "SW101",
        "airline": "Southwest Airlines",
        "departure": "LAX",
        "arrival": "DEN",
        "departure_time": "2024-01-15T12:00:00",
        "arrival_time": "2024-01-15T15:30:00",
        "price": 199.99,
        "status": "on_time",
        "aircraft": "Boeing 737-700",
        "duration_minutes": 150
    },
    {
        "flight_number": "B6202",
        "airline": "JetBlue Airways",
        "departure": "JFK",
        "arrival": "BOS",
        "departure_time": "2024-01-15T15:45:00",
        "arrival_time": "2024-01-15T17:00:00",
        "price": 159.99,
        "status": "on_time",
        "aircraft": "Airbus A220",
        "duration_minutes": 75
    },
    {
        "flight_number": "AS303",
        "airline": "Alaska Airlines",
        "departure": "LAX",
        "arrival": "SEA",
        "departure_time": "2024-01-15T09:15:00",
        "arrival_time": "2024-01-15T11:45:00",
        "price": 225.00,
        "status": "boarding",
        "aircraft": "Boeing 737-900",
        "duration_minutes": 150
    }
]

# Price alert tracking (in a real app, this would be stored in a database)
PRICE_ALERTS = []

# Deep airline URLs for advanced flight search functionality
deep_airline_urls = {
    "american": "https://www.aa.com/homePage.do",
    "delta": "https://www.delta.com",
    "united": "https://www.united.com", 
    "southwest": "https://www.southwest.com",
    "jetblue": "https://www.jetblue.com",
    "alaska": "https://www.alaskaair.com",
    "ryanair": "https://www.ryanair.com"
}

def create_query(departure, arrival, date=None, passengers=1, airline=None):
    """
    Create a standardized flight query object for airline APIs
    
    Args:
        departure (str): Departure airport code
        arrival (str): Arrival airport code  
        date (str, optional): Travel date in YYYY-MM-DD format
        passengers (int): Number of passengers
        airline (str, optional): Preferred airline
        
    Returns:
        dict: Standardized query object
    """
    query = {
        "departure": departure.upper(),
        "arrival": arrival.upper(),
        "passengers": passengers,
        "query_timestamp": datetime.now().isoformat()
    }
    
    if date:
        query["date"] = date
    if airline:
        query["airline"] = airline.lower()
        
    return query

@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    """Home endpoint with comprehensive API documentation"""
    return templates.TemplateResponse("home.html", {
        "request": request,
        "message": "Welcome to Flight Alert App",
        "version": "2.0.0",
        "description": "Advanced flight search and price alert system"
    })

@app.get('/api/alerts')
def get_alerts():
    """Get active price alerts"""
    try:
        # In a real app, this would query a database
        recent_alerts = PRICE_ALERTS[-10:]  # Get last 10 alerts
        
        return {
            "alerts": recent_alerts,
            "total_alerts": len(PRICE_ALERTS),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving alerts")

@app.get('/api/routes')
def get_routes():
    """Get available flight routes and basic statistics"""
    try:
        # Extract unique routes from mock data
        routes = {}
        airlines = set()
        
        for flight in MOCK_FLIGHTS:
            route_key = f"{flight['departure']}-{flight['arrival']}"
            if route_key not in routes:
                routes[route_key] = {
                    "departure": flight['departure'],
                    "arrival": flight['arrival'],
                    "flights_available": 0,
                    "price_range": {"min": float('inf'), "max": 0},
                    "airlines": set()
                }
            
            routes[route_key]["flights_available"] += 1
            routes[route_key]["price_range"]["min"] = min(routes[route_key]["price_range"]["min"], flight['price'])
            routes[route_key]["price_range"]["max"] = max(routes[route_key]["price_range"]["max"], flight['price'])
            routes[route_key]["airlines"].add(flight['airline'])
            airlines.add(flight['airline'])
        
        # Convert sets to lists for JSON serialization
        for route in routes.values():
            route["airlines"] = list(route["airlines"])
            route["price_range"]["min"] = round(route["price_range"]["min"], 2)
            route["price_range"]["max"] = round(route["price_range"]["max"], 2)
        
        return {
            "routes": list(routes.values()),
            "total_routes": len(routes),
            "total_flights": len(MOCK_FLIGHTS),
            "airlines": list(airlines),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving routes: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving routes")

@app.post('/api/advanced-search')
def advanced_search(query: AdvancedSearchQuery):
    """
    Advanced flight search using external airline APIs and deep linking
    Demonstrates usage of create_query, deep_airline_urls, and ryanair integration
    """
    try:
        departure = query.departure.upper()
        arrival = query.arrival.upper()
        date = query.date
        airline = query.airline.lower() if query.airline else None
        
        # Create standardized query using the create_query function
        search_query = create_query(departure, arrival, date, passengers=1, airline=airline)
        
        # Get deep airline URLs for the search
        available_airlines = []
        for airline_name, url in deep_airline_urls.items():
            available_airlines.append({
                "name": airline_name,
                "deep_link": url,
                "search_url": f"{url}?from={departure}&to={arrival}&date={date or ''}"
            })
        
        # Integrate with Ryanair API (mock)
        ryanair_results = ryanair.get_flights(departure, arrival, date)
        
        response = {
            "query": search_query,
            "deep_links": available_airlines,
            "ryanair_integration": ryanair_results,
            "search_metadata": {
                "total_airlines": len(deep_airline_urls),
                "query_type": "advanced_search",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in advanced search: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during advanced search")

@app.get('/api/status')
def api_status():
    """API status check endpoint"""
    return {
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "service": "Flight Alert App API"
    }

@app.post('/api/query')
def query_flights(query: FlightQuery, request: Request):
    """
    Main query endpoint for flight searches
    Handles POST requests to search for flights based on criteria
    Supports: departure, arrival, date, max_price, min_price, airline, max_duration, alert_price
    """
    try:
        # Log the incoming request
        client_ip = request.client.host
        logger.info(f"Flight query request from {client_ip}")
        
        # Extract search parameters from Pydantic model
        departure = query.departure.upper()
        arrival = query.arrival.upper()
        date = query.date
        max_price = query.max_price
        min_price = query.min_price
        airline = query.airline.lower() if query.airline else None
        max_duration = query.max_duration  # in minutes
        alert_price = query.alert_price  # price threshold for alerts
        
        logger.info(f"Search criteria: departure={departure}, arrival={arrival}, date={date}, "
                   f"max_price={max_price}, min_price={min_price}, airline={airline}, "
                   f"max_duration={max_duration}, alert_price={alert_price}")
        
        # Create query object for consistency with advanced search
        search_query = create_query(departure, arrival, date, airline=airline)
        
        # Validate price range if both provided
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(status_code=400, detail="min_price cannot be greater than max_price")
        
        # Filter flights based on search criteria
        matching_flights = []
        alert_flights = []  # Flights that meet alert criteria
        
        for flight in MOCK_FLIGHTS:
            # Check departure and arrival match
            if flight['departure'] == departure and flight['arrival'] == arrival:
                include_flight = True
                
                # Check price filters
                if max_price is not None and flight['price'] > max_price:
                    include_flight = False
                if min_price is not None and flight['price'] < min_price:
                    include_flight = False
                
                # Check airline filter
                if airline and airline not in flight['airline'].lower():
                    include_flight = False
                
                # Check duration filter
                if max_duration is not None and flight.get('duration_minutes', 0) > max_duration:
                    include_flight = False
                
                if include_flight:
                    # Add calculated fields to flight data
                    enhanced_flight = flight.copy()
                    enhanced_flight['duration_formatted'] = format_duration(flight.get('duration_minutes', 0))
                    enhanced_flight['price_per_hour'] = round(flight['price'] / (flight.get('duration_minutes', 60) / 60), 2)
                    matching_flights.append(enhanced_flight)
                    
                    # Check if flight meets alert criteria
                    if alert_price is not None and flight['price'] <= alert_price:
                        alert_flights.append(enhanced_flight)
        
        # Sort flights by price (ascending)
        matching_flights.sort(key=lambda x: x['price'])
        
        # Calculate statistics
        if matching_flights:
            prices = [f['price'] for f in matching_flights]
            avg_price = round(sum(prices) / len(prices), 2)
            min_flight_price = min(prices)
            max_flight_price = max(prices)
        else:
            avg_price = min_flight_price = max_flight_price = None
        
        # Process price alerts if requested
        alert_info = None
        if alert_price is not None:
            alert_info = {
                "alert_price_threshold": alert_price,
                "flights_below_threshold": len(alert_flights),
                "lowest_price_found": min_flight_price,
                "alert_active": len(alert_flights) > 0
            }
            
            # Store alert for tracking (in a real app, this would go to a database)
            if len(alert_flights) > 0:
                PRICE_ALERTS.append({
                    "departure": departure,
                    "arrival": arrival,
                    "alert_price": alert_price,
                    "matching_flights": len(alert_flights),
                    "timestamp": datetime.now().isoformat(),
                    "client_ip": client_ip
                })
        
        # Prepare response
        response = {
            "search_criteria": {
                "departure": departure,
                "arrival": arrival,
                "date": date,
                "max_price": max_price,
                "min_price": min_price,
                "airline": airline if airline else None,
                "max_duration": max_duration,
                "alert_price": alert_price
            },
            "query_metadata": search_query,
            "results": {
                "count": len(matching_flights),
                "flights": matching_flights
            },
            "statistics": {
                "average_price": avg_price,
                "min_price": min_flight_price,
                "max_price": max_flight_price,
                "route": f"{departure} → {arrival}"
            },
            "alert_info": alert_info,
            "deep_links": {
                "available_airlines": list(deep_airline_urls.keys()),
                "external_search_available": True
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Found {len(matching_flights)} matching flights for {departure} → {arrival}")
        if alert_flights:
            logger.info(f"Found {len(alert_flights)} flights below alert price threshold of ${alert_price}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing flight query: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your flight search")

def format_duration(minutes):
    """Convert duration in minutes to human-readable format"""
    if minutes <= 0:
        return "Unknown"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"

if __name__ == '__main__':
    import uvicorn
    logger.info("Starting Flight Alert App v2.0...")
    logger.info(f"Loaded {len(MOCK_FLIGHTS)} mock flights across multiple routes")
    logger.info("Available endpoints: /, /api/status, /api/query, /api/alerts, /api/routes") 
    logger.info("Enhanced features: price alerts, advanced filtering, route analytics")
    
    # Run the FastAPI server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)