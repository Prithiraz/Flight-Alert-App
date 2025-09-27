#!/usr/bin/env python3
"""
Flight Alert App - Main Application
Provides flight search and alert functionality via REST API
"""

import logging
from datetime import datetime
from flask import Flask, request, jsonify
import requests
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Mock flight data for demonstration (in a real app, this would connect to airline APIs)
MOCK_FLIGHTS = [
    {
        "flight_number": "AA123",
        "airline": "American Airlines",
        "departure": "JFK",
        "arrival": "LAX",
        "departure_time": "2024-01-15T10:00:00",
        "arrival_time": "2024-01-15T13:30:00",
        "price": 299.99,
        "status": "on_time"
    },
    {
        "flight_number": "UA456",
        "airline": "United Airlines", 
        "departure": "LAX",
        "arrival": "ORD",
        "departure_time": "2024-01-15T14:00:00",
        "arrival_time": "2024-01-15T19:45:00",
        "price": 245.50,
        "status": "delayed"
    },
    {
        "flight_number": "DL789",
        "airline": "Delta Air Lines",
        "departure": "ORD",
        "arrival": "JFK", 
        "departure_time": "2024-01-15T16:30:00",
        "arrival_time": "2024-01-15T19:15:00",
        "price": 312.75,
        "status": "on_time"
    }
]

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        "message": "Welcome to Flight Alert App",
        "version": "1.0.0",
        "endpoints": {
            "/api/query": "POST - Search for flights",
            "/api/status": "GET - Check API status"
        }
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """API status check endpoint"""
    return jsonify({
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "service": "Flight Alert App API"
    })

@app.route('/api/query', methods=['POST'])
def query_flights():
    """
    Main query endpoint for flight searches
    Handles POST requests to search for flights based on criteria
    """
    try:
        # Log the incoming request
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        logger.info(f"Flight query request from {client_ip}")
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "No JSON data provided",
                "message": "Please provide search criteria in JSON format"
            }), 400
        
        # Extract search parameters
        departure = data.get('departure', '').upper()
        arrival = data.get('arrival', '').upper()
        date = data.get('date')
        max_price = data.get('max_price')
        
        logger.info(f"Search criteria: departure={departure}, arrival={arrival}, date={date}, max_price={max_price}")
        
        # Validate required parameters
        if not departure or not arrival:
            return jsonify({
                "error": "Missing required parameters",
                "message": "Both 'departure' and 'arrival' airport codes are required"
            }), 400
        
        # Filter flights based on search criteria
        matching_flights = []
        for flight in MOCK_FLIGHTS:
            # Check departure and arrival match
            if flight['departure'] == departure and flight['arrival'] == arrival:
                # Check price filter if provided
                if max_price is None or flight['price'] <= max_price:
                    matching_flights.append(flight)
        
        # Prepare response
        response = {
            "search_criteria": {
                "departure": departure,
                "arrival": arrival,
                "date": date,
                "max_price": max_price
            },
            "results": {
                "count": len(matching_flights),
                "flights": matching_flights
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Found {len(matching_flights)} matching flights")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing flight query: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": "An error occurred while processing your flight search"
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist",
        "available_endpoints": ["/", "/api/status", "/api/query"]
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 Method Not Allowed errors"""
    return jsonify({
        "error": "Method not allowed",
        "message": "The requested method is not allowed for this endpoint"
    }), 405

if __name__ == '__main__':
    logger.info("Starting Flight Alert App...")
    # Run the Flask development server
    app.run(host='0.0.0.0', port=8000, debug=True)