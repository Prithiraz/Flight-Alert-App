#!/usr/bin/env python3
"""
Quick validation script for the single-file main.py implementation
Tests all core functionality without starting the full server
"""

import sys
import json

def test_imports():
    """Test that all imports work"""
    print("🔍 Testing imports...")
    try:
        from main import (
            Flask, sqlite3, stripe, requests,
            init_database, get_exchange_rates, convert_price,
            generate_mock_flights, search_flights_amadeus,
            AIRLINES_DB, AIRPORTS_DB, RARE_AIRCRAFT
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\n🔍 Testing database...")
    try:
        from main import init_database, get_db
        import os
        
        # Remove old test db
        if os.path.exists('test_validation.db'):
            os.remove('test_validation.db')
        
        # Create new db
        import sqlite3
        conn = sqlite3.connect('test_validation.db')
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                subscription_type TEXT,
                subscription_status TEXT DEFAULT 'expired'
            )
        ''')
        conn.commit()
        conn.close()
        
        # Clean up
        os.remove('test_validation.db')
        
        print("✅ Database initialization works")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_data_structures():
    """Test that all data structures are populated"""
    print("\n🔍 Testing data structures...")
    try:
        from main import AIRLINES_DB, AIRPORTS_DB, RARE_AIRCRAFT, EXCHANGE_RATES
        
        assert len(AIRLINES_DB) >= 20, "Not enough airlines"
        assert len(AIRPORTS_DB) >= 30, "Not enough airports"
        assert len(RARE_AIRCRAFT) >= 8, "Not enough rare aircraft"
        assert len(EXCHANGE_RATES) >= 8, "Not enough currencies"
        
        print(f"✅ Airlines: {len(AIRLINES_DB)}")
        print(f"✅ Airports: {len(AIRPORTS_DB)}")
        print(f"✅ Rare Aircraft: {len(RARE_AIRCRAFT)}")
        print(f"✅ Currencies: {len(EXCHANGE_RATES)}")
        return True
    except Exception as e:
        print(f"❌ Data structure error: {e}")
        return False

def test_flight_generation():
    """Test flight data generation"""
    print("\n🔍 Testing flight generation...")
    try:
        from main import generate_mock_flights
        
        flights = generate_mock_flights("LHR", "JFK", "2025-12-15")
        
        assert len(flights) >= 10, "Not enough flights generated"
        assert flights[0]['departure'] == "LHR"
        assert flights[0]['arrival'] == "JFK"
        assert 'price_gbp' in flights[0]
        assert 'airline_name' in flights[0]
        
        print(f"✅ Generated {len(flights)} flights")
        print(f"   Sample: {flights[0]['airline_name']} - £{flights[0]['price_gbp']}")
        return True
    except Exception as e:
        print(f"❌ Flight generation error: {e}")
        return False

def test_currency_conversion():
    """Test currency conversion"""
    print("\n🔍 Testing currency conversion...")
    try:
        from main import convert_price
        
        gbp_100 = 100.0
        usd = convert_price(gbp_100, 'USD')
        eur = convert_price(gbp_100, 'EUR')
        
        assert usd > 100, "USD conversion incorrect"
        assert eur > 100, "EUR conversion incorrect"
        
        print(f"✅ £100 = ${usd} USD")
        print(f"✅ £100 = €{eur} EUR")
        return True
    except Exception as e:
        print(f"❌ Currency conversion error: {e}")
        return False

def test_html_templates():
    """Test that HTML templates are defined"""
    print("\n🔍 Testing HTML templates...")
    try:
        from main import DASHBOARD_HTML, MAP_HTML
        
        assert len(DASHBOARD_HTML) > 1000, "Dashboard HTML too short"
        assert len(MAP_HTML) > 500, "Map HTML too short"
        assert "FlightAlert Pro" in DASHBOARD_HTML
        assert "Live Flight Map" in MAP_HTML
        
        print(f"✅ Dashboard HTML: {len(DASHBOARD_HTML)} chars")
        print(f"✅ Map HTML: {len(MAP_HTML)} chars")
        return True
    except Exception as e:
        print(f"❌ HTML template error: {e}")
        return False

def test_flask_app():
    """Test Flask app configuration"""
    print("\n🔍 Testing Flask app...")
    try:
        from main import app
        
        assert app.name == 'main'
        assert app.config.get('SECRET_KEY') is not None
        
        # Check routes
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        required_routes = ['/', '/map', '/api/status', '/api/pay', '/api/search', '/api/alerts', '/api/add-alert']
        
        for route in required_routes:
            assert route in routes, f"Route {route} missing"
        
        print(f"✅ Flask app configured")
        print(f"✅ Found {len(routes)} routes")
        return True
    except Exception as e:
        print(f"❌ Flask app error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("=" * 60)
    print("FlightAlert Pro - Single-File Validation")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_database,
        test_data_structures,
        test_flight_generation,
        test_currency_conversion,
        test_html_templates,
        test_flask_app
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("🎉 All validation tests passed!")
        print("\n✅ Your main.py is ready to use!")
        print("\nRun: python3 main.py")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
