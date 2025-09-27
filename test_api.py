#!/usr/bin/env python3
"""
Test script for Flight Alert App API endpoints
Tests the /api/query endpoint to ensure 404 errors are resolved
"""

import requests
import json
import time
import subprocess
import sys
from threading import Thread

def test_api_endpoints():
    """Test all API endpoints"""
    base_url = "http://localhost:8000"
    
    print("Testing Flight Alert App API endpoints...")
    
    # Test home endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"GET / - Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Home endpoint working")
        else:
            print("✗ Home endpoint failed")
    except requests.exceptions.RequestException as e:
        print(f"✗ Home endpoint failed: {e}")
    
    # Test status endpoint
    try:
        response = requests.get(f"{base_url}/api/status")
        print(f"GET /api/status - Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Status endpoint working")
        else:
            print("✗ Status endpoint failed")
    except requests.exceptions.RequestException as e:
        print(f"✗ Status endpoint failed: {e}")
    
    # Test query endpoint with valid data
    try:
        query_data = {
            "departure": "JFK",
            "arrival": "LAX",
            "date": "2024-01-15",
            "max_price": 350
        }
        response = requests.post(f"{base_url}/api/query", json=query_data)
        print(f"POST /api/query - Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Query endpoint working")
            data = response.json()
            print(f"  Found {data['results']['count']} flights")
        else:
            print("✗ Query endpoint failed")
            print(f"  Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Query endpoint failed: {e}")
    
    # Test query endpoint with missing data (should return 400)
    try:
        response = requests.post(f"{base_url}/api/query", json={})
        print(f"POST /api/query (empty) - Status: {response.status_code}")
        if response.status_code == 400:
            print("✓ Query endpoint properly handles missing data")
        else:
            print("✗ Query endpoint should return 400 for missing data")
    except requests.exceptions.RequestException as e:
        print(f"✗ Query endpoint test failed: {e}")
    
    # Test non-existent endpoint (should return 404)
    try:
        response = requests.get(f"{base_url}/api/nonexistent")
        print(f"GET /api/nonexistent - Status: {response.status_code}")
        if response.status_code == 404:
            print("✓ 404 handling working correctly")
        else:
            print("✗ 404 handling not working")
    except requests.exceptions.RequestException as e:
        print(f"✗ 404 test failed: {e}")

if __name__ == "__main__":
    print("Flight Alert App API Test")
    print("=" * 40)
    
    # Wait a moment for server to start
    time.sleep(2)
    
    test_api_endpoints()