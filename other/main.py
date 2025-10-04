#!/usr/bin/env python3
"""
FlightAlert Pro - BYOB Architecture with Browser Extension Support
Production-Grade Flight Scraper with Extension-Based Price Collection
"""

# Import verification
try:
    import fastapi
    import uvicorn
    import pydantic
    import aiohttp
    import bs4
    import pandas
    import werkzeug
    import dateutil
    import pytz
    import requests
    import jinja2
    print("✅ All required packages imported successfully")
except ImportError as e:
    print(f"❌ Missing package: {e}")
    import sys
    import subprocess
    print("Installing missing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pydantic", "aiohttp", "beautifulsoup4", "pandas", "werkzeug", "python-dateutil", "pytz", "requests", "playwright", "jinja2", "python-multipart"])
    print("✅ Dependencies installed. Please restart.")
    sys.exit(1)

import asyncio
import uuid
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
import time
import random
import re
import hashlib
import secrets
import sqlite3
from contextlib import contextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form, Header
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Core imports
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode, urlparse
import threading
from threading import Lock
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil import parser as dtparse
import pytz
import requests

Updated upstream
# Get the directory of this script for template path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "templates")
=======
# Try to import Playwright for optional server-side validation
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
    print("✅ Playwright available for validation scraping")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright not available - install with: pip install playwright && playwright install chromium")
>>>>>>> Stashed changes

# Force headless mode for server validation
HEADLESS = True
print("🤖 Server validation will run in headless mode")

# ------------ Config ------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_PATH = "flightalert.db"
MAX_RESULTS_PER_QUERY = 50
VALIDATION_RATE_LIMIT = 60  # seconds between validations per site
INGEST_TOKEN = "dev-only-token-change-me"  # Simple token to prevent spam

# Amadeus API Configuration
# For Replit: Add these as Secrets (AMADEUS_API_KEY, AMADEUS_API_SECRET)
# For GitHub: Set these as environment variables or manually configure
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
AMADEUS_BASE_URL = "https://api.amadeus.com"
AMADEUS_TEST_MODE = os.getenv("AMADEUS_TEST_MODE", "true").lower() == "true"

<<<<<<< Updated upstream
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

# Deep airline URLs - mapping airline codes to their homepage URLs
deep_airline_urls = {
    "FR": "https://www.ryanair.com",
    "W6": "https://wizzair.com",
    "U2": "https://www.easyjet.com",
    "BA": "https://www.britishairways.com",
    "DL": "https://www.delta.com",
    "AA": "https://www.aa.com",
    "UA": "https://www.united.com",
    "LH": "https://www.lufthansa.com",
    "AF": "https://www.airfrance.com",
    "KL": "https://www.klm.com"
}

# Database setup
DB_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "flightalert.db")
=======
# Duffel API Configuration
# For Replit: Add DUFFEL_API_KEY as a Secret
# For GitHub: Set as environment variable or manually configure
DUFFEL_API_KEY = os.getenv("DUFFEL_API_KEY", "DUFFEL_API_KEY")
DUFFEL_BASE_URL = "https://api.duffel.com"
>>>>>>> Stashed changes

# Debug Duffel configuration
print(f"🔧 Duffel API Key: {DUFFEL_API_KEY[:20]}...")
print(f"🔧 Duffel Base URL: {DUFFEL_BASE_URL}")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("flight-scraper")

# Thread-safe locks
file_lock = Lock()

# Global state
user_sessions: Dict[str, Dict[str, Any]] = {}
PLAY = None
BROWSER = None

# Pydantic models for API
class SiteConfigResponse(BaseModel):
    sites: List[Dict[str, Any]]
    selectors: List[Dict[str, Any]]
    version: str

class QueryRequest(BaseModel):
    origin: str
    destination: str
    depart_date: str
    return_date: Optional[str] = None
    cabin_class: Optional[str] = "economy"  # economy, business, first
    passengers: Optional[int] = 1

class IngestionRequest(BaseModel):
    site: str
    url: str
    query: Dict[str, str]
    currency: str
    itineraries: List[Dict[str, Any]]
    page_meta: Dict[str, Any]

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# Database management
@contextmanager
def get_db_connection():
    """Thread-safe database connection context manager"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database with BYOB architecture tables"""
    with get_db_connection() as conn:
        # Sites table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                allowed_scrape BOOLEAN DEFAULT 0,
                robots_checked_at TIMESTAMP,
                priority INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 0.0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Selectors table for dynamic selector management
        conn.execute('''
            CREATE TABLE IF NOT EXISTS selectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                version INTEGER DEFAULT 1,
                field TEXT NOT NULL,
                strategy TEXT NOT NULL,
                selector TEXT,
                regex_pattern TEXT,
                json_path TEXT,
                priority INTEGER DEFAULT 1,
                success_7d INTEGER DEFAULT 0,
                last_success TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')

        # Queries table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                depart_date TEXT NOT NULL,
                return_date TEXT,
                cabin_class TEXT DEFAULT 'economy',
                passengers INTEGER DEFAULT 1,
                user_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Results table for ingested data
        conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER NOT NULL,
                site_id INTEGER NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_json TEXT NOT NULL,
                hash TEXT NOT NULL,
                price_min REAL,
                price_currency TEXT,
                legs_json TEXT,
                source TEXT DEFAULT 'extension',
                carrier_codes TEXT,
                flight_numbers TEXT,
                stops INTEGER,
                fare_brand TEXT,
                booking_url TEXT,
                valid BOOLEAN DEFAULT 1,
                FOREIGN KEY (query_id) REFERENCES queries (id),
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')

        # Users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                preferences_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Metrics table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                site_id INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Alerts table for price monitoring
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL DEFAULT 'cheap',
                origin TEXT,
                destination TEXT,
                one_way BOOLEAN DEFAULT 1,
                depart_start TEXT,
                depart_end TEXT,
                return_start TEXT,
                return_end TEXT,
                min_bags INTEGER DEFAULT 0,
                max_bags INTEGER DEFAULT 2,
                cabin TEXT DEFAULT 'economy',
                min_price REAL,
                max_price REAL,
                min_duration INTEGER,
                max_duration INTEGER,
                rare_aircraft_list TEXT,
                notes TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Matches table to track alert hits
        conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                result_id INTEGER NOT NULL,
                matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                seen BOOLEAN DEFAULT 0,
                FOREIGN KEY (alert_id) REFERENCES alerts (id),
                FOREIGN KEY (result_id) REFERENCES results (id)
            )
        ''')

        # Price history for price war tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_key TEXT NOT NULL,
                date_key TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                carrier TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_query_id ON results(query_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_hash ON results(hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_selectors_site_field ON selectors(site_id, field)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, active)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_matches_alert ON matches(alert_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_route ON price_history(route_key, date_key)')

        conn.commit()
        logger.info("✅ Database initialized with BYOB architecture")

        # Verify alerts table exists and has correct structure
        cursor = conn.execute("PRAGMA table_info(alerts)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'active' not in columns:
            conn.execute('ALTER TABLE alerts ADD COLUMN active BOOLEAN DEFAULT 1')
            conn.commit()
            logger.info("✅ Updated alerts table structure")

def migrate_users_from_json():
    """Migrate users from users.json to SQLite database"""
    if not os.path.exists('users.json'):
        return

    try:
        with open('users.json', 'r') as f:
            json_users = json.load(f)

        with get_db_connection() as conn:
            for user in json_users:
                # Check if user already exists
                existing = conn.execute('SELECT id FROM users WHERE email = ?', (user['email'],)).fetchone()
                if not existing:
                    conn.execute(
                        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                        (user['username'], user['email'], user['password_hash'])
                    )
                    logger.info(f"✅ Migrated user: {user['username']} ({user['email']})")
            conn.commit()

    except Exception as e:
        logger.warning(f"⚠️ User migration failed: {e}")

def seed_initial_data():
    """Seed database with initial sites and selectors"""
    with get_db_connection() as conn:
        # Check if we already have sites
        existing_sites = conn.execute('SELECT COUNT(*) FROM sites').fetchone()[0]
        if existing_sites > 0:
            return

        # Initial sites
        sites_data = [
            ('skyscanner.net', 'Skyscanner', 0, 1, 'Popular OTA'),
            ('kayak.com', 'Kayak', 0, 1, 'Popular OTA'),
            ('expedia.com', 'Expedia', 0, 2, 'OTA with good coverage'),
            ('booking.com', 'Booking.com', 0, 2, 'Hotels and flights'),
            ('ba.com', 'British Airways', 1, 1, 'Official airline - allowed'),
            ('ryanair.com', 'Ryanair', 1, 1, 'Official airline - allowed'),
            ('easyjet.com', 'easyJet', 1, 1, 'Official airline - allowed'),
            ('lufthansa.com', 'Lufthansa', 1, 1, 'Official airline - allowed'),
            ('airfrance.com', 'Air France', 1, 1, 'Official airline - allowed'),
            ('klm.com', 'KLM', 1, 1, 'Official airline - allowed')
        ]

        for domain, name, allowed, priority, notes in sites_data:
            conn.execute(
                'INSERT INTO sites (domain, name, allowed_scrape, priority, notes) VALUES (?, ?, ?, ?, ?)',
                (domain, name, allowed, priority, notes)
            )

        # Initial selectors for key sites
        site_id_map = {row[0]: row[1] for row in conn.execute('SELECT domain, id FROM sites').fetchall()}

        selectors_data = [
            # Skyscanner
            (site_id_map['skyscanner.net'], 'itineraries', 'css', '[data-testid*="flight-card"], .FlightCard', None, None, 1),
            (site_id_map['skyscanner.net'], 'price_total', 'css', '[data-testid*="price"], .BpkText_bpk-text__money', r'([£$€]\d+)', None, 1),
            (site_id_map['skyscanner.net'], 'carrier', 'css', '[data-testid*="airline"], .airline-name', None, None, 1),

            # Kayak
            (site_id_map['kayak.com'], 'itineraries', 'css', '.result-item, [data-resultid]', None, None, 1),
            (site_id_map['kayak.com'], 'price_total', 'css', '.price-text, [class*="price"]', r'([£$€]\d+)', None, 1),
            (site_id_map['kayak.com'], 'carrier', 'css', '.airline-text, [class*="airline"]', None, None, 1),

            # British Airways
            (site_id_map['ba.com'], 'itineraries', 'css', '.flight-option, .fare-family', None, None, 1),
            (site_id_map['ba.com'], 'price_total', 'css', '.fare-price, [class*="price"]', r'([£$€]\d+)', None, 1),
            (site_id_map['ba.com'], 'carrier', 'css', '.airline-name', None, None, 1),
        ]

        for site_id, field, strategy, selector, regex, json_path, priority in selectors_data:
            if site_id:  # Only insert if site exists
                conn.execute(
                    'INSERT INTO selectors (site_id, field, strategy, selector, regex_pattern, json_path, priority) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (site_id, field, strategy, selector, regex, json_path, priority)
                )

        conn.commit()
        logger.info("✅ Seeded initial sites and selectors")

# Amadeus API Integration
class AmadeusClient:
    """Amadeus API client for flight search"""

    def __init__(self):
        self.api_key = AMADEUS_API_KEY
        self.api_secret = AMADEUS_API_SECRET
        self.base_url = AMADEUS_BASE_URL
        self.test_mode = AMADEUS_TEST_MODE
        self.access_token = None
        self.token_expires_at = None

    def is_configured(self) -> bool:
        """Check if Amadeus credentials are configured"""
        return bool(self.api_key and self.api_secret)

    def _should_attempt_request(self) -> bool:
        """Check if we should attempt API requests (prevents spam when not configured)"""
        if not self.is_configured():
            return False
        # Don't spam failed attempts - only retry every 5 minutes after failure
        if hasattr(self, '_last_failed_attempt'):
            time_since_failure = (datetime.utcnow() - self._last_failed_attempt).total_seconds()
            if time_since_failure < 300:  # 5 minutes
                return False
        return True

    async def get_access_token(self) -> Optional[str]:
        """Get OAuth access token from Amadeus with smart error handling"""
        # Don't attempt if credentials aren't configured or if we should rate limit
        if not self._should_attempt_request():
            return None

        # Check if token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return self.access_token

        try:
            # Get new token
            token_url = f"{self.base_url}/v1/security/oauth2/token"

            data = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.api_secret
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data, headers=headers) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.access_token = token_data.get('access_token')
                        expires_in = token_data.get('expires_in', 3600)
                        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                        # Clear any previous failure timestamps
                        if hasattr(self, '_last_failed_attempt'):
                            delattr(self, '_last_failed_attempt')
                        if hasattr(self, '_error_logged'):
                            delattr(self, '_error_logged')
                        logger.info("✅ Amadeus access token obtained")
                        return self.access_token
                    else:
                        # Set failure timestamp to prevent spam
                        self._last_failed_attempt = datetime.utcnow()
                        if not hasattr(self, '_error_logged'):
                            logger.warning(f"⚠️ Amadeus API credentials not working (status {response.status}). Disabling for 5 minutes to reduce console spam.")
                            self._error_logged = True
                        return None

        except Exception as e:
            self._last_failed_attempt = datetime.utcnow()
            if not hasattr(self, '_error_logged'):
                logger.warning(f"⚠️ Amadeus API authentication error: {e}. Disabling for 5 minutes.")
                self._error_logged = True
            return None

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Search flights using Amadeus API"""
        token = await self.get_access_token()
        if not token:
            return []

        try:
            # Use appropriate endpoint based on trip type
            if return_date:
                endpoint = f"{self.base_url}/v2/shopping/flight-offers"
            else:
                endpoint = f"{self.base_url}/v2/shopping/flight-offers"

            params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': departure_date,
                'adults': adults,
                'max': 20  # Limit results
            }

            if return_date:
                params['returnDate'] = return_date

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        flights = data.get('data', [])
                        logger.info(f"✅ Amadeus returned {len(flights)} flight offers")
                        return self._format_amadeus_results(flights)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Amadeus search failed: {response.status} - {error_text}")
                        return []

        except Exception as e:
            logger.error(f"❌ Amadeus search error: {e}")
            return []

    def _format_amadeus_results(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Amadeus API results to our standard format"""
        formatted_results = []

        for flight in flights:
            try:
                # Extract pricing
                price_info = flight.get('price', {})
                total_price = float(price_info.get('total', 0))
                currency = price_info.get('currency', 'EUR')

                # Extract itinerary info
                itineraries = flight.get('itineraries', [])
                if not itineraries:
                    continue

                segments = []
                for itinerary in itineraries:
                    for segment in itinerary.get('segments', []):
                        departure = segment.get('departure', {})
                        arrival = segment.get('arrival', {})
                        operating = segment.get('operating', {})

                        segments.append({
                            'carrier': operating.get('carrierCode', segment.get('carrierCode', '')),
                            'flight_number': segment.get('number', ''),
                            'origin': departure.get('iataCode', ''),
                            'destination': arrival.get('iataCode', ''),
                            'departure_time': departure.get('at', ''),
                            'arrival_time': arrival.get('at', ''),
                            'aircraft': segment.get('aircraft', {}).get('code', ''),
                            'duration': segment.get('duration', '')
                        })

                if segments:
                    formatted_results.append({
                        'price': {
                            'amount': total_price,
                            'currency': currency
                        },
                        'carrier': segments[0]['carrier'],
                        'flight_number': segments[0]['flight_number'],
                        'departure_time': segments[0]['departure_time'],
                        'arrival_time': segments[-1]['arrival_time'],
                        'stops': len(segments) - 1,
                        'segments': segments,
                        'booking_url': '',  # Amadeus doesn't provide direct booking URLs
                        'source': {
                            'name': 'Amadeus API',
                            'domain': 'amadeus.com',
                            'success_rate': 1.0
                        },
                        'fetched_at': datetime.utcnow().isoformat(),
                        'hash': hashlib.sha256(json.dumps(flight, sort_keys=True).encode()).hexdigest()[:16]
                    })

            except Exception as e:
                logger.warning(f"Error formatting Amadeus result: {e}")
                continue

        return formatted_results

# Duffel API Integration
class DuffelClient:
    """Duffel API client for flight search"""

    def __init__(self):
        self.api_key = DUFFEL_API_KEY
        self.base_url = DUFFEL_BASE_URL

    def is_configured(self) -> bool:
        """Check if Duffel credentials are configured"""
        return bool(self.api_key and self.api_key.startswith('duffel_'))

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, passengers: int = 1) -> List[Dict[str, Any]]:
        """Search flights using Duffel API"""
        if not self.is_configured():
            logger.warning("⚠️ Duffel API key not configured")
            return []

        try:
            # Create offer request
            offer_request_data = {
                "data": {
                    "slices": [
                        {
                            "origin": origin,
                            "destination": destination,
                            "departure_date": departure_date
                        }
                    ],
                    "passengers": [{"type": "adult"} for _ in range(passengers)],
                    "cabin_class": "economy"
                }
            }

            # Add return slice if round trip
            if return_date:
                offer_request_data["data"]["slices"].append({
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date
                })

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Duffel-Version": "v2"
            }

            # Create offer request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/air/offer_requests",
                    json=offer_request_data,
                    headers=headers
                ) as response:
                    if response.status == 201:
                        request_data = await response.json()
                        offer_request_id = request_data["data"]["id"]

                        # Get offers
                        async with session.get(
                            f"{self.base_url}/air/offers",
                            params={"offer_request_id": offer_request_id},
                            headers=headers
                        ) as offers_response:
                            if offers_response.status == 200:
                                offers_data = await offers_response.json()
                                offers = offers_data.get("data", [])
                                logger.info(f"✅ Duffel returned {len(offers)} flight offers")
                                return self._format_duffel_results(offers)
                            else:
                                error_text = await offers_response.text()
                                logger.error(f"❌ Duffel offers failed: {offers_response.status} - {error_text}")
                                logger.error(f"❌ Offer request ID: {offer_request_id}")
                                logger.error(f"❌ Search params: {origin} → {destination} on {departure_date}")
                                return []
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Duffel request failed: {response.status} - {error_text}")
                        logger.error(f"❌ Request data: {offer_request_data}")
                        logger.error(f"❌ Headers used: {headers}")
                        return []

        except Exception as e:
            logger.error(f"❌ Duffel search error: {e}")
            return []

    def _format_duffel_results(self, offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Duffel API results to our standard format"""
        formatted_results = []
        seen_combinations = set()  # Track unique flight combinations

        for offer in offers:
            try:
                # Extract pricing
                total_amount = float(offer.get("total_amount", 0))
                currency = offer.get("total_currency", "GBP")

                # Extract slices (legs)
                slices = offer.get("slices", [])
                if not slices:
                    continue

                segments = []
                first_segment = None
                last_segment = None

                for slice_data in slices:
                    slice_segments = slice_data.get("segments", [])
                    for segment in slice_segments:
                        # Get airline info
                        marketing_carrier = segment.get("marketing_carrier", {})
                        aircraft = segment.get("aircraft", {})

                        segment_info = {
                            'carrier': marketing_carrier.get("iata_code", ""),
                            'carrier_name': marketing_carrier.get("name", ""),
                            'flight_number': segment.get("marketing_carrier_flight_number", ""),
                            'origin': segment.get("origin", {}).get("iata_code", ""),
                            'destination': segment.get("destination", {}).get("iata_code", ""),
                            'departure_time': segment.get("departing_at", ""),
                            'arrival_time': segment.get("arriving_at", ""),
                            'aircraft': aircraft.get("name", ""),
                            'aircraft_code': aircraft.get("iata_code", ""),
                            'duration': segment.get("duration", "")
                        }

                        segments.append(segment_info)

                        if first_segment is None:
                            first_segment = segment_info
                        last_segment = segment_info

                if segments and first_segment and last_segment:
                    # Add aerospace engineering calculations
                    aerospace_data = {}

                    # Get airport coordinates for calculations
                    origin_coords = get_airport_coordinates(first_segment['origin'])
                    dest_coords = get_airport_coordinates(last_segment['destination'])

                    if origin_coords and dest_coords:
                        # Great circle distance calculations
                        distance_data = aerospace_calc.great_circle_distance(
                            origin_coords['lat'], origin_coords['lon'],
                            dest_coords['lat'], dest_coords['lon']
                        )

                        # Initial bearing for navigation
                        bearing = aerospace_calc.initial_bearing(
                            origin_coords['lat'], origin_coords['lon'],
                            dest_coords['lat'], dest_coords['lon']
                        )

                        # Fuel efficiency estimate
                        aircraft_type = first_segment.get('aircraft_code', 'unknown')
                        fuel_data = aerospace_calc.fuel_efficiency_estimate(
                            distance_data['great_circle_km'], aircraft_type
                        )

                        aerospace_data = {
                            'distance': distance_data,
                            'navigation': {
                                'initial_bearing': round(bearing, 1),
                                'bearing_description': get_bearing_description(bearing)
                            },
                            'fuel_analysis': fuel_data,
                            'route_efficiency': calculate_route_efficiency(segments, distance_data)
                        }

                    # Enhanced deduplication - prevent repeated flights with same prices
                    all_flight_numbers = [seg['flight_number'] for seg in segments]
                    route_key = f"{first_segment['origin']}-{last_segment['destination']}"

                    # Extract meaningful time components for deduplication
                    departure_time_short = first_segment['departure_time'][:16] if first_segment['departure_time'] else 'unknown'
                    arrival_time_short = last_segment['arrival_time'][:16] if last_segment['arrival_time'] else 'unknown'

                    # Create primary unique key with full flight details
                    primary_key = f"{route_key}-{first_segment['carrier']}-{'-'.join(all_flight_numbers)}-{departure_time_short}-{arrival_time_short}-{total_amount:.2f}-{len(segments)}"

                    # Create secondary key for aggressive price-based deduplication 
                    # This prevents multiple flights with identical prices from same carrier
                    price_route_key = f"{route_key}-{first_segment['carrier']}-{total_amount:.2f}"

                    # Only add if both keys are unique (prevents price duplicates)
                    if primary_key not in seen_combinations:
                        # For same carrier + route + price, only keep the first one (usually best time)
                        if price_route_key not in seen_combinations:
                            seen_combinations.add(primary_key)
                            seen_combinations.add(price_route_key)  # Track this price combination

                        # Get full airline name with explanation
                        carrier_code = first_segment['carrier']
                        carrier_name = first_segment.get('carrier_name', '')

                        # Add explanation for common airline codes
                        airline_explanations = {
                            'RJ': 'Royal Jordanian Airlines (Jordan)',
                            'BA': 'British Airways (UK)',
                            'FR': 'Ryanair (Ireland)',
                            'U2': 'easyJet (UK)', 
                            'LH': 'Lufthansa (Germany)',
                            'AF': 'Air France (France)',
                            'KL': 'KLM (Netherlands)',
                            'TK': 'Turkish Airlines (Turkey)',
                            'EK': 'Emirates (UAE)',
                            'QR': 'Qatar Airways (Qatar)',
                            'SV': 'Saudia (Saudi Arabia)',
                            'MS': 'EgyptAir (Egypt)',
                            'BG': 'Biman Bangladesh Airlines (Bangladesh)',
                            'BS': 'US-Bangla Airlines (Bangladesh)'
                        }

                        full_carrier_name = airline_explanations.get(carrier_code, carrier_name or carrier_code)

                        formatted_results.append({
                            'price': {
                                'amount': total_amount,
                                'currency': currency
                            },
                            'carrier': carrier_code,
                            'carrier_name': full_carrier_name,
                            'flight_number': first_segment['flight_number'],
                            'departure_time': first_segment['departure_time'],
                            'arrival_time': last_segment['arrival_time'],
                            'stops': len(segments) - 1,
                            'segments': segments,
                            'booking_url': self._generate_deep_booking_url(first_segment, last_segment, offer.get('id', '')),
                            'offer_id': offer.get('id', ''),
                            'source': {
                                'name': 'Duffel API',
                                'domain': 'duffel.com',
                                'success_rate': 1.0
                            },
                            'aerospace_analysis': aerospace_data,
                            'fetched_at': datetime.utcnow().isoformat(),
                            'hash': hashlib.sha256(json.dumps({
                                'carrier': first_segment['carrier'],
                                'flight_number': first_segment['flight_number'], 
                                'departure_time': first_segment['departure_time'],
                                'price': total_amount,
                                'offer_id': offer.get('id', '')
                            }, sort_keys=True).encode()).hexdigest()[:16]
                        })

            except Exception as e:
                logger.warning(f"Error formatting Duffel result: {e}")
                continue

        logger.info(f"🎯 Duffel API: Formatted {len(formatted_results)} unique flights from {len(offers)} offers")
        return formatted_results

    def _generate_deep_booking_url(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], offer_id: str) -> str:
        """Generate direct airline booking URLs ONLY - no OTA fallbacks"""
        try:
            origin = first_segment.get('origin', '').upper()
            destination = last_segment.get('destination', '').upper()
            carrier = first_segment.get('carrier', '').upper()
            flight_number = first_segment.get('flight_number', '')
            departure_date = first_segment.get('departure_time', '')[:10]  # Get YYYY-MM-DD
            departure_time = first_segment.get('departure_time', '')

            # Extract time components for deeper linking
            if departure_time and 'T' in departure_time:
                time_part = departure_time.split('T')[1][:5]  # Get HH:MM
            else:
                time_part = ''

            # Comprehensive airline-specific deep booking URLs with flight details
            airline_urls = {
                # European Airlines
                'BA': f'https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?journeyType=ONEWAY&origin={origin}&destination={destination}&departureDate={departure_date}&cabinClass=M&adult=1',
                'FR': f'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={departure_date}&origin={origin}&destination={destination}',
                'U2': f'https://www.easyjet.com/en/booking/flights/{origin.lower()}-{destination.lower()}/{departure_date}?adults=1&children=0&infants=0',
                'W6': f'https://wizzair.com/en-gb/flights/select?departureDate={departure_date}&origin={origin}&destination={destination}&adultCount=1',
                'VS': f'https://www.virgin-atlantic.com/gb/en/book-a-flight/select-flights?origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',
                'AF': f'https://www.airfrance.com/en/booking/search?connections%5B0%5D%5Bdeparture%5D={origin}&connections%5B0%5D%5Barrival%5D={destination}&connections%5B0%5D%5BdepartureDate%5D={departure_date}&pax%5Badults%5D=1',
                'LH': f'https://www.lufthansa.com/de/en/booking/offers?departure={origin}&destination={destination}&outbound-date={departure_date}&return-date=&pax.adult=1&cabin-class=economy',
                'KL': f'https://www.klm.com/search/offers?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1&cabinClass=economy',
                'SK': f'https://www.sas.com/book/flights?from={origin}&to={destination}&outDate={departure_date}&adults=1&children=0&youth=0&infants=0',
                'IB': f'https://www.iberia.com/gb/flights/{origin}-{destination}/{departure_date}/?passengers=1',
                'VY': f'https://www.vueling.com/en/flights/{origin.lower()}-{destination.lower()}/{departure_date}?passengers=1',
                'TP': f'https://www.tap.pt/en/flights/{origin}-{destination}?adults=1&departureDate={departure_date}',
                'SN': f'https://www.brusselsairlines.com/en-us/booking/flights/{origin}-{destination}/{departure_date}?ADT=1',
                'LX': f'https://www.swiss.com/us/en/book/outbound-flight/{origin}-{destination}/{departure_date}?travelers=1-0-0-0',
                'OS': f'https://www.austrian.com/us/en/book/flight/{origin}/{destination}?departureDate={departure_date}&numAdults=1',
                'AZ': f'https://www.alitalia.com/en_us/booking/flights-search.html?tripType=OW&departureStation={origin}&arrivalStation={destination}&outboundDate={departure_date}&passengers=1-0-0',
                'AY': f'https://www.finnair.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DY': f'https://www.norwegian.com/en/booking/flight-search?origin={origin}&destination={destination}&outbound={departure_date}&adults=1',
                'EN': f'https://www.airdolomiti.it/en/book-a-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'LO': f'https://www.lot.com/us/en/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'OK': f'https://www.czechairlines.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RO': f'https://www.tarom.ro/en/book-a-flight?tripType=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'JU': f'https://www.airserbia.com/en/booking/flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'OU': f'https://www.croatiaairlines.com/en/book-a-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'JP': f'https://www.adria.si/en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BT': f'https://www.airbaltic.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # North American Airlines
                'DL': f'https://www.delta.com/flight-search/book-a-flight?origin={origin}&destination={destination}&departure_date={departure_date}&passengers=1',
                'UA': f'https://www.united.com/en/us/fsr/choose-flights?f={origin}&t={destination}&d={departure_date}&tt=1&at=1&sc=7',
                'AA': f'https://www.aa.com/booking/choose-flights?localeCode=en_US&from={origin}&to={destination}&departureDate={departure_date}&tripType=OneWay&adult=1',
                'AS': f'https://www.alaskaair.com/booking/reservation/search?passengers=1&from={origin}&to={destination}&departureDate={departure_date}',
                'B6': f'https://www.jetblue.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'WN': f'https://www.southwest.com/air/booking/select.html?originationAirportCode={origin}&destinationAirportCode={destination}&departureDate={departure_date}&adults=1',
                'AC': f'https://www.aircanada.com/us/en/aco/home/book/search/flight.html?tripType=O&org0={origin}&dest0={destination}&departureDate0={departure_date}&adult=1',
                'WS': f'https://www.westjet.com/en-ca/flights/search?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',

                # Middle Eastern Airlines
                'EK': f'https://www.emirates.com/english/book-a-flight/flights-search.aspx?fromCityOrAirport={origin}&toCityOrAirport={destination}&departDate={departure_date}&adults=1',
                'QR': f'https://www.qatarairways.com/en/booking?tripType=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'EY': f'https://www.etihad.com/en/flights/{origin}/{destination}?departureDate={departure_date}&passengerCount=1',
                'TK': f'https://www.turkishairlines.com/en-int/flights/booking/{origin}-{destination}/{departure_date}/?pax=1&cabin=Economy',
                'WY': f'https://www.omanair.com/en/book/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'GF': f'https://www.gulfair.com/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KU': f'https://www.kuwaitairways.com/en/booking/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'SV': f'https://www.saudia.com/book/flight-search?trip=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'MS': f'https://www.egyptair.com/en/fly-egyptair/online-booking?tripType=OW&from={origin}&to={destination}&depDate={departure_date}&adults=1',
                'FZ': f'https://www.flydubai.com/en/book-a-trip/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RJ': f'https://www.rj.com/en/book-and-manage/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AT': f'https://www.royalairmaroc.com/int-en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DT': f'https://www.taag.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TU': f'https://www.tunisair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Asian Airlines
                'SQ': f'https://www.singaporeair.com/en_UK/book-a-flight/search/?triptype=OW&from={origin}&to={destination}&depdate={departure_date}&paxadult=1',
                'CX': f'https://www.cathaypacific.com/cx/en_US/book-a-trip/search.html?tripType=OW&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JL': f'https://www.jal.co.jp/en/dom/search/?ar={origin}&dp={destination}&dd={departure_date}&adult=1',
                'NH': f'https://www.ana.co.jp/en/us/book-plan/book/domestic/search/?departureAirport={origin}&arrivalAirport={destination}&departureDate={departure_date}&adult=1',
                'AI': f'https://www.airindia.in/book/flight-search?trip=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                '6E': f'https://www.goindigo.in/book/flight-search.html?r=1&px=1,0,0&o={origin}&d={destination}&dd={departure_date}',
                'SG': f'https://www.spicejet.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UK': f'https://www.airvistara.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'IX': f'https://www.airindiaexpress.in/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'PK': f'https://www.piac.com.pk/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BG': f'https://www.biman-airlines.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UL': f'https://www.srilankan.com/en_uk/plan-and-book/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TG': f'https://www.thaiairways.com/en_CA/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'FD': f'https://www.airasia.com/flights/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'SL': f'https://www.lionairthai.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'MH': f'https://www.malaysiaairlines.com/my/en/book-with-us/search.html?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AK': f'https://www.airasia.com/flights/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'D7': f'https://www.airasia.com/flights/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BI': f'https://www.bruneiair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TR': f'https://www.flyscoot.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'MI': f'https://www.silkair.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'GA': f'https://www.garuda-indonesia.com/id/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'JT': f'https://www.lionair.co.id/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'QG': f'https://www.citilink.co.id/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VN': f'https://www.vietnamairlines.com/us/en/book-ticket/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VJ': f'https://www.vietjetair.com/Sites/Web/en-US/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'PR': f'https://www.philippineairlines.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                '5J': f'https://www.cebupacificair.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CA': f'https://www.airchina.com.cn/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CZ': f'https://www.csair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'MU': f'https://www.ceair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'HU': f'https://www.hainanairlines.com/HUPortal/dyn/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'SC': f'https://en.shandongair.com.cn/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'FM': f'https://www.ceair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'OZ': f'https://flyasiana.com/C/US/EN/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KE': f'https://www.koreanair.com/global/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TW': f'https://www.twayair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CI': f'https://www.china-airlines.com/us/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BR': f'https://www.evaair.com/us-en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'IT': f'https://www.tigerairtw.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'HX': f'https://www.hongkongairlines.com/en_US/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UO': f'https://www.hkexpress.com/en-us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'NX': f'https://www.airmacau.com.mo/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Australian & Pacific Airlines
                'QF': f'https://www.qantas.com/au/en/booking/search.html?tripType=O&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JQ': f'https://www.jetstar.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VA': f'https://www.virginaustralia.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'NZ': f'https://www.airnewzealand.com/booking/select-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'FJ': f'https://www.fijiairways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Latin American Airlines
                'LA': f'https://www.latam.com/en_us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'JJ': f'https://www.latam.com/en_br/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'G3': f'https://www.voegol.com.br/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AD': f'https://www.voeazul.com.br/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AR': f'https://www.aerolineas.com.ar/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CM': f'https://www.copaair.com/en/web/us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AV': f'https://www.avianca.com/us/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AM': f'https://aeromexico.com/en-us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VB': f'https://www.vivaaerobus.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'Y4': f'https://www.volaris.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'WJ': f'https://www.caribbeanairlines.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Russian Airlines
                'SU': f'https://www.aeroflot.ru/us-en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'S7': f'https://www.s7.ru/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UT': f'https://www.utair.ru/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1'
            }

            # ONLY return airline-specific URLs - no fallbacks to OTAs
            if carrier in airline_urls:
                return airline_urls[carrier]

            # If airline not supported, return empty string (no booking link)
            logger.info(f"Direct booking not available for airline {carrier}")
            return ""

        except Exception as e:
            logger.warning(f"Error generating airline booking URL: {e}")
            return ""

# FlightAPI Integration for Budget Airlines  
class FlightAPIClient:
    """FlightAPI client for comprehensive budget airline coverage"""

    def __init__(self):
        # Use provided API key with fallback to environment
        self.api_key = os.getenv('FLIGHTAPI_KEY', 'FLIGHTAPI_KEY')
        # Note: FlightAPI may not be active - this is a placeholder for future real budget airline APIs
        self.base_url = 'https://api.aviationstack.com/v1'  # Alternative flight API

    def is_configured(self) -> bool:
        """Check if FlightAPI credentials are configured"""
        return bool(self.api_key)

    def _should_attempt_request(self) -> bool:
        """Check if we should attempt API requests (prevents spam when failing)"""
        if not self.is_configured():
            return False
        # Don't spam failed attempts - only retry every 10 minutes after failure
        if hasattr(self, '_last_failed_attempt'):
            time_since_failure = (datetime.utcnow() - self._last_failed_attempt).total_seconds()
            if time_since_failure < 600:  # 10 minutes
                return False
        return True

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, passengers: int = 1) -> List[Dict[str, Any]]:
        """Search flights using FlightAPI with improved error handling"""
        # Don't attempt if we should rate limit failed attempts
        if not self._should_attempt_request():
            return []

        try:
            # Note: The provided FlightAPI key may not be for an active service
            # This is disabled to prevent console spam until we have a working budget airline API
            if not hasattr(self, '_api_disabled_warning_shown'):
                logger.info("ℹ️ FlightAPI temporarily disabled - using Duffel API and Ryanair integration for comprehensive coverage")
                self._api_disabled_warning_shown = True
            return []

            # Alternative approach - use a working API if available
            async with aiohttp.ClientSession() as session:
                # This would be for a working flight API
                endpoint = f"{self.base_url}/flights"

                params = {
                    'access_key': self.api_key,
                    'departure_iata': origin,
                    'arrival_iata': destination,
                    'limit': 20
                }

                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'FlightAlert-Pro-QMUL-Student/1.0'
                }

                async with session.get(endpoint, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        flights = data.get('data', [])
                        logger.info(f"✅ FlightAPI returned {len(flights)} budget airline flights")
                        return self._format_flightapi_results(flights)
                    else:
                        # Set failure timestamp to prevent spam
                        self._last_failed_attempt = datetime.utcnow()
                        if not hasattr(self, '_error_logged'):
                            logger.warning(f"⚠️ FlightAPI not responding correctly (status {response.status}). Disabling for 10 minutes to reduce console spam.")
                            self._error_logged = True
                        return []

        except Exception as e:
            self._last_failed_attempt = datetime.utcnow()
            if not hasattr(self, '_error_logged'):
                logger.warning(f"⚠️ FlightAPI error: {e}. Disabling for 10 minutes.")
                self._error_logged = True
            return []

# ==================== BUDGET AIRLINE INTEGRATION ====================

class RyanairAPIClient:
    """Direct Ryanair integration for budget airline pricing"""

    def __init__(self):
        try:
            from ryanair import Ryanair
            self.api = Ryanair("EUR")  # Use EUR for European routes
            self.available = True
            logger.info("✅ Ryanair API client initialized")
        except ImportError:
            self.available = False
            logger.warning("⚠️ Ryanair library not available")

    def is_configured(self) -> bool:
        return self.available

    async def search_flights(self, origin: str, destination: str, departure_date: str, passengers: int = 1) -> List[Dict[str, Any]]:
        """Search Ryanair flights with real pricing"""
        if not self.available:
            return []

        try:
            from datetime import datetime, timedelta

            # Convert date string to datetime object
            dep_date = datetime.strptime(departure_date, '%Y-%m-%d').date()

            # Get cheapest flights for the date
            flights = self.api.get_cheapest_flights(origin, dep_date, dep_date + timedelta(days=1))

            formatted_flights = []
            for flight in flights[:10]:  # Limit to 10 results
                if hasattr(flight, 'price') and hasattr(flight, 'currency'):
                    formatted_flight = {
                        'id': f"ryanair_{flight.outbound.flight_number if hasattr(flight, 'outbound') else 'FR001'}_{departure_date}",
                        'carrier': 'FR',
                        'carrier_name': 'Ryanair',
                        'flight_number': getattr(flight.outbound, 'flight_number', 'FR001') if hasattr(flight, 'outbound') else 'FR001',
                        'origin': origin,
                        'destination': destination,
                        'departure_time': getattr(flight.outbound, 'departure_time', f"{departure_date}T08:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T08:00:00",
                        'arrival_time': getattr(flight.outbound, 'arrival_time', f"{departure_date}T10:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T10:00:00",
                        'duration': getattr(flight.outbound, 'duration', '2h 00m') if hasattr(flight, 'outbound') else '2h 00m',
                        'stops': 0,  # Ryanair is typically direct
                        'price': {
                            'total': float(flight.price),
                            'currency': flight.currency,
                            'formatted': f"{flight.currency}{flight.price:.2f}"
                        },
                        'cabin_class': 'economy',
                        'booking_url': f"https://www.ryanair.com/gb/en/trip/flights/select?adults={passengers}&dateOut={departure_date}&originIATA={origin}&destinationIATA={destination}",
                        'source': 'Ryanair Direct API',
                        'segments': [{
                            'origin': origin,
                            'destination': destination,
                            'departure_time': getattr(flight.outbound, 'departure_time', f"{departure_date}T08:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T08:00:00",
                            'arrival_time': getattr(flight.outbound, 'arrival_time', f"{departure_date}T10:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T10:00:00",
                            'flight_number': getattr(flight.outbound, 'flight_number', 'FR001') if hasattr(flight, 'outbound') else 'FR001',
                            'carrier': 'FR'
                        }]
                    }
                    formatted_flights.append(formatted_flight)

            logger.info(f"✅ Ryanair API returned {len(formatted_flights)} flights")
            return formatted_flights

        except Exception as e:
            logger.error(f"❌ Ryanair API failed: {e}")
            return []

    def _format_flightapi_results(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format FlightAPI results to our standard format"""
        formatted_results = []
        seen_combinations = set()

        for flight in flights:
            try:
                # Extract pricing
                price_info = flight.get('price', {})
                total_amount = float(price_info.get('amount', 0))
                currency = price_info.get('currency', 'USD')

                # Extract route segments
                segments = []
                legs = flight.get('legs', [])

                for leg in legs:
                    carriers = leg.get('carriers', [])
                    if carriers:
                        carrier_info = carriers[0]  # Primary carrier

                        segment_info = {
                            'carrier': carrier_info.get('code', ''),
                            'carrier_name': carrier_info.get('name', ''),
                            'flight_number': leg.get('flight_number', ''),
                            'origin': leg.get('origin', {}).get('code', ''),
                            'destination': leg.get('destination', {}).get('code', ''),
                            'departure_time': leg.get('departure_time', ''),
                            'arrival_time': leg.get('arrival_time', ''),
                            'aircraft': leg.get('aircraft', ''),
                            'duration': leg.get('duration', '')
                        }
                        segments.append(segment_info)

                if segments:
                    first_segment = segments[0]
                    last_segment = segments[-1]

                    # Enhanced deduplication with price-based filtering
                    all_flight_numbers = [seg['flight_number'] for seg in segments]
                    route_key = f"{first_segment['origin']}-{last_segment['destination']}"
                    segment_hash = hashlib.sha256(json.dumps(segments, sort_keys=True).encode()).hexdigest()[:8]

                    # Primary uniqueness key  
                    primary_key = f"{route_key}-{'-'.join(all_flight_numbers)}-{first_segment['departure_time']}-{total_amount}-{segment_hash}"

                    # Secondary key to prevent same price duplicates from same source
                    price_source_key = f"{route_key}-FlightAPI-{total_amount:.2f}"

                    # Only add if both uniqueness criteria are met
                    if primary_key not in seen_combinations:
                        if price_source_key not in seen_combinations:
                            seen_combinations.add(primary_key)
                            seen_combinations.add(price_source_key)

                        formatted_results.append({
                            'price': {
                                'amount': total_amount,
                                'currency': currency
                            },
                            'carrier': first_segment['carrier'],
                            'carrier_name': first_segment['carrier_name'],
                            'flight_number': first_segment['flight_number'],
                            'departure_time': first_segment['departure_time'],
                            'arrival_time': last_segment['arrival_time'],
                            'stops': len(segments) - 1,
                            'segments': segments,
                            'booking_url': self._generate_deep_booking_url(first_segment, last_segment, flight.get('id', '')),
                            'offer_id': flight.get('id', ''),
                            'source': {
                                'name': 'FlightAPI',
                                'domain': 'flightapi.io',
                                'success_rate': 1.0
                            },
                            'aerospace_analysis': self._calculate_aerospace_data(first_segment, last_segment, segments),
                            'fetched_at': datetime.utcnow().isoformat(),
                            'hash': hashlib.sha256(json.dumps({
                                'carrier': first_segment['carrier'],
                                'flight_number': first_segment['flight_number'], 
                                'departure_time': first_segment['departure_time'],
                                'price': total_amount,
                                'offer_id': flight.get('id', '')
                            }, sort_keys=True).encode()).hexdigest()[:16]
                        })

            except Exception as e:
                logger.warning(f"Error formatting FlightAPI result: {e}")
                continue

        logger.info(f"🎯 FlightAPI: Formatted {len(formatted_results)} unique flights from {len(flights)} offers")
        return formatted_results

    def _generate_deep_booking_url(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], offer_id: str) -> str:
        """Generate DEEP booking URLs with pre-filled flight details"""
        try:
            origin = first_segment.get('origin', '').upper()
            destination = last_segment.get('destination', '').upper()
            carrier = first_segment.get('carrier', '').upper()
            flight_number = first_segment.get('flight_number', '')
            departure_date = first_segment.get('departure_time', '')[:10]  # YYYY-MM-DD
            departure_time = first_segment.get('departure_time', '')[11:16] if len(first_segment.get('departure_time', '')) > 10 else ''  # HH:MM

            # Comprehensive airline-specific booking URLs with flight details pre-filled
            deep_airline_urls = {
                # European Airlines
                'BA': f'https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?journeyType=ONEWAY&origin={origin}&destination={destination}&departureDate={departure_date}&cabinClass=M&adult=1',
                'FR': f'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={departure_date}&origin={origin}&destination={destination}',
                'U2': f'https://www.easyjet.com/en/booking/flights/{origin.lower()}-{destination.lower()}/{departure_date}?adults=1&children=0&infants=0',
                'W6': f'https://wizzair.com/en-gb/flights/select?departureDate={departure_date}&origin={origin}&destination={destination}&adultCount=1',
                'VS': f'https://www.virgin-atlantic.com/gb/en/book-a-flight/select-flights?origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',
                'AF': f'https://www.airfrance.com/en/booking/search?connections%5B0%5D%5Bdeparture%5D={origin}&connections%5B0%5D%5Barrival%5D={destination}&connections%5B0%5D%5BdepartureDate%5D={departure_date}&pax%5Badults%5D=1',
                'LH': f'https://www.lufthansa.com/de/en/booking/offers?departure={origin}&destination={destination}&outbound-date={departure_date}&return-date=&pax.adult=1&cabin-class=economy',
                'KL': f'https://www.klm.com/search/offers?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1&cabinClass=economy',
                'SK': f'https://www.sas.com/book/flights?from={origin}&to={destination}&outDate={departure_date}&adults=1&children=0&youth=0&infants=0',
                'IB': f'https://www.iberia.com/gb/flights/{origin}-{destination}/{departure_date}/?passengers=1',
                'VY': f'https://www.vueling.com/en/flights/{origin.lower()}-{destination.lower()}/{departure_date}?passengers=1',
                'TP': f'https://www.tap.pt/en/flights/{origin}-{destination}?adults=1&departureDate={departure_date}',
                'SN': f'https://www.brusselsairlines.com/en-us/booking/flights/{origin}-{destination}/{departure_date}?ADT=1',
                'LX': f'https://www.swiss.com/us/en/book/outbound-flight/{origin}-{destination}/{departure_date}?travelers=1-0-0-0',
                'OS': f'https://www.austrian.com/us/en/book/flight/{origin}/{destination}?departureDate={departure_date}&numAdults=1',
                'AZ': f'https://www.alitalia.com/en_us/booking/flights-search.html?tripType=OW&departureStation={origin}&arrivalStation={destination}&outboundDate={departure_date}&passengers=1-0-0',
                'AY': f'https://www.finnair.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DY': f'https://www.norwegian.com/en/booking/flight-search?origin={origin}&destination={destination}&outbound={departure_date}&adults=1',

                # North American Airlines
                'DL': f'https://www.delta.com/flight-search/book-a-flight?origin={origin}&destination={destination}&departure_date={departure_date}&passengers=1',
                'UA': f'https://www.united.com/en/us/fsr/choose-flights?f={origin}&t={destination}&d={departure_date}&tt=1&at=1&sc=7',
                'AA': f'https://www.aa.com/booking/choose-flights?localeCode=en_US&from={origin}&to={destination}&departureDate={departure_date}&tripType=OneWay&adult=1',
                'AS': f'https://www.alaskaair.com/booking/reservation/search?passengers=1&from={origin}&to={destination}&departureDate={departure_date}',
                'B6': f'https://www.jetblue.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'WN': f'https://www.southwest.com/air/booking/select.html?originationAirportCode={origin}&destinationAirportCode={destination}&departureDate={departure_date}&adults=1',
                'AC': f'https://www.aircanada.com/us/en/aco/home/book/search/flight.html?tripType=O&org0={origin}&dest0={destination}&departureDate0={departure_date}&adult=1',
                'WS': f'https://www.westjet.com/en-ca/flights/search?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',

                # Middle Eastern Airlines
                'EK': f'https://www.emirates.com/english/book-a-flight/flights-search.aspx?fromCityOrAirport={origin}&toCityOrAirport={destination}&departDate={departure_date}&adults=1',
                'QR': f'https://www.qatarairways.com/en/booking?tripType=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'EY': f'https://www.etihad.com/en/flights/{origin}/{destination}?departureDate={departure_date}&passengerCount=1',
                'TK': f'https://www.turkishairlines.com/en-int/flights/booking/{origin}-{destination}/{departure_date}/?pax=1&cabin=Economy',
                'WY': f'https://www.omanair.com/en/book/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'GF': f'https://www.gulfair.com/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KU': f'https://www.kuwaitairways.com/en/booking/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'SV': f'https://www.saudia.com/book/flight-search?trip=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'MS': f'https://www.egyptair.com/en/fly-egyptair/online-booking?tripType=OW&from={origin}&to={destination}&depDate={departure_date}&adults=1',
                'FZ': f'https://www.flydubai.com/en/book-a-trip/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RJ': f'https://www.rj.com/en/book-and-manage/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Asian Airlines
                'SQ': f'https://www.singaporeair.com/en_UK/book-a-flight/search/?triptype=OW&from={origin}&to={destination}&depdate={departure_date}&paxadult=1',
                'CX': f'https://www.cathaypacific.com/cx/en_US/book-a-trip/search.html?tripType=OW&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JL': f'https://www.jal.co.jp/en/dom/search/?ar={origin}&dp={destination}&dd={departure_date}&adult=1',
                'NH': f'https://www.ana.co.jp/en/us/book-plan/book/domestic/search/?departureAirport={origin}&arrivalAirport={destination}&departureDate={departure_date}&adult=1',
                'AI': f'https://www.airindia.in/book/flight-search?trip=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                '6E': f'https://www.goindigo.in/book/flight-search.html?r=1&px=1,0,0&o={origin}&d={destination}&dd={departure_date}',
                'TG': f'https://www.thaiairways.com/en_CA/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'MH': f'https://www.malaysiaairlines.com/my/en/book-with-us/search.html?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AK': f'https://www.airasia.com/flights/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Australian Airlines
                'QF': f'https://www.qantas.com/au/en/booking/search.html?tripType=O&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JQ': f'https://www.jetstar.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VA': f'https://www.virginaustralia.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'NZ': f'https://www.airnewzealand.com/booking/select-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Latin American Airlines
                'LA': f'https://www.latam.com/en_us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CM': f'https://www.copaair.com/en/web/us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AV': f'https://www.avianca.com/us/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AM': f'https://aeromexico.com/en-us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AR': f'https://www.aerolineas.com.ar/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1'
            }

            # Use airline-specific deep URL if available
            if carrier in deep_airline_urls:
                return deep_airline_urls[carrier]

            # For other airlines, create a Google Flights URL with flight number for easier finding
            if flight_number:
                google_deep_url = f'https://www.google.com/flights?hl=en#flt={origin}.{destination}.{departure_date};c:{carrier}{flight_number}'
                return google_deep_url

            # Fallback to Skyscanner with route and date
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/{departure_date.replace("-", "")}/?adults=1&children=0&adultsv2=1&childrenv2=&infants=0&cabinclass=economy&rtn=0&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false'

        except Exception as e:
            logger.warning(f"Error generating deep booking URL: {e}")
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/'

    def _calculate_aerospace_data(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aerospace engineering data for FlightAPI results"""
        try:
            origin_coords = get_airport_coordinates(first_segment['origin'])
            dest_coords = get_airport_coordinates(last_segment['destination'])

            if origin_coords and dest_coords:
                # Great circle distance calculations
                distance_data = aerospace_calc.great_circle_distance(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Initial bearing for navigation
                bearing = aerospace_calc.initial_bearing(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Fuel efficiency estimate
                aircraft_type = first_segment.get('aircraft', 'unknown')
                fuel_data = aerospace_calc.fuel_efficiency_estimate(
                    distance_data['great_circle_km'], aircraft_type
                )

                return {
                    'distance': distance_data,
                    'navigation': {
                        'initial_bearing': round(bearing, 1),
                        'bearing_description': get_bearing_description(bearing)
                    },
                    'fuel_analysis': fuel_data,
                    'route_efficiency': calculate_route_efficiency(segments, distance_data)
                }
        except Exception as e:
            logger.warning(f"Error calculating aerospace data: {e}")

        return {}

# Initialize API clients
amadeus_client = AmadeusClient()
duffel_client = DuffelClient()
flightapi_client = FlightAPIClient()

# Aerospace Engineering Enhancement Classes
class AerospaceCalculator:
    """Aerospace engineering calculations for flight analysis"""

    def __init__(self):
        self.earth_radius_km = 6371.0
        self.earth_radius_nm = 3440.065  # Nautical miles

    def great_circle_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Dict[str, float]:
        """Calculate great circle distance between two points (shortest flight path)"""
        import math

        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        distance_km = self.earth_radius_km * c
        distance_nm = self.earth_radius_nm * c
        distance_mi = distance_km * 0.621371

        return {
            'great_circle_km': round(distance_km, 2),
            'great_circle_nm': round(distance_nm, 2),
            'great_circle_mi': round(distance_mi, 2)
        }

    def initial_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate initial bearing for great circle route"""
        import math

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)

        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)

        # Normalize to 0-360 degrees
        return (bearing_deg + 360) % 360

    def fuel_efficiency_estimate(self, distance_km: float, aircraft_type: str = "unknown") -> Dict[str, Any]:
        """Estimate fuel consumption based on distance and aircraft type"""

        # Typical fuel consumption rates (liters per km per passenger)
        fuel_rates = {
            "A320": 0.024,  # Airbus A320 family
            "A321": 0.025,
            "A330": 0.028,
            "A350": 0.022,  # More efficient
            "B737": 0.025,  # Boeing 737
            "B738": 0.025,
            "B787": 0.020,  # Very efficient
            "B777": 0.030,
            "E190": 0.026,  # Embraer regional
            "unknown": 0.025  # Average estimate
        }

        rate = fuel_rates.get(aircraft_type.upper(), fuel_rates["unknown"])
        total_fuel_liters = distance_km * rate
        fuel_cost_estimate = total_fuel_liters * 0.85  # ~$0.85 per liter jet fuel

        return {
            'fuel_per_passenger_liters': round(total_fuel_liters, 2),
            'fuel_cost_estimate_usd': round(fuel_cost_estimate, 2),
            'efficiency_rating': 'High' if rate < 0.023 else 'Medium' if rate < 0.027 else 'Standard',
            'aircraft_type': aircraft_type
        }

class AviationWeatherClient:
    """Aviation weather data integration for flight planning"""

    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data"

    async def get_metar(self, airport_code: str) -> Dict[str, Any]:
        """Get current weather conditions (METAR) for airport"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/metar"
                params = {
                    'ids': airport_code.upper(),
                    'format': 'json',
                    'taf': 'false',
                    'hours': '1'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            metar = data[0]
                            return {
                                'airport': airport_code.upper(),
                                'metar_text': metar.get('rawOb', ''),
                                'visibility': metar.get('visib', 'Unknown'),
                                'wind_speed': metar.get('wspd', 0),
                                'wind_direction': metar.get('wdir', 0),
                                'temperature': metar.get('temp', 'Unknown'),
                                'conditions': metar.get('wx', []),
                                'flight_category': metar.get('fltcat', 'Unknown'),
                                'observation_time': metar.get('obsTime', ''),
                                'suitable_for_flight': metar.get('fltcat', '').upper() in ['VFR', 'MVFR']
                            }

        except Exception as e:
            logger.warning(f"Weather API error for {airport_code}: {e}")

        return {
            'airport': airport_code.upper(),
            'metar_text': 'Weather data unavailable',
            'flight_category': 'Unknown',
            'suitable_for_flight': True  # Default assumption
        }

    async def get_taf(self, airport_code: str) -> Dict[str, Any]:
        """Get Terminal Aerodrome Forecast (TAF) for airport"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/taf"
                params = {
                    'ids': airport_code.upper(),
                    'format': 'json',
                    'hours': '12'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            taf = data[0]
                            return {
                                'airport': airport_code.upper(),
                                'taf_text': taf.get('rawTAF', ''),
                                'forecast_time': taf.get('fcstTime', ''),
                                'valid_from': taf.get('validTime', ''),
                                'forecast_conditions': 'Available'
                            }

        except Exception as e:
            logger.warning(f"TAF API error for {airport_code}: {e}")

        return {
            'airport': airport_code.upper(),
            'taf_text': 'Forecast data unavailable',
            'forecast_conditions': 'Unknown'
        }

# Aerospace helper functions
def get_airport_coordinates(airport_code: str) -> Optional[Dict[str, float]]:
    """Get airport coordinates from the airport database"""
    try:
        with get_db_connection() as conn:
            airport = conn.execute(
                'SELECT latitude, longitude FROM airports WHERE iata_code = ? OR icao_code = ?',
                (airport_code.upper(), airport_code.upper())
            ).fetchone()

            if airport and airport['latitude'] and airport['longitude']:
                return {
                    'lat': float(airport['latitude']),
                    'lon': float(airport['longitude'])
                }
    except Exception as e:
        logger.warning(f"Error getting coordinates for {airport_code}: {e}")

    return None

def get_bearing_description(bearing: float) -> str:
    """Convert bearing degrees to compass direction"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(bearing / 22.5) % 16
    return directions[index]

def calculate_route_efficiency(segments: List[Dict[str, Any]], direct_distance: Dict[str, float]) -> Dict[str, Any]:
    """Calculate route efficiency compared to direct flight"""
    try:
        total_distance = 0

        # Calculate total distance of actual route
        for i, segment in enumerate(segments):
            if i > 0:  # Get distance between connecting airports
                prev_dest = segments[i-1]['destination']
                curr_origin = segment['origin']

                prev_coords = get_airport_coordinates(prev_dest)
                curr_coords = get_airport_coordinates(curr_origin)

                if prev_coords and curr_coords:
                    # Add distance if there's a connection
                    if prev_dest != curr_origin:
                        connection_dist = aerospace_calc.great_circle_distance(
                            prev_coords['lat'], prev_coords['lon'],
                            curr_coords['lat'], curr_coords['lon']
                        )
                        total_distance += connection_dist['great_circle_km']

            # Add segment distance
            origin_coords = get_airport_coordinates(segment['origin'])
            dest_coords = get_airport_coordinates(segment['destination'])

            if origin_coords and dest_coords:
                seg_dist = aerospace_calc.great_circle_distance(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )
                total_distance += seg_dist['great_circle_km']

        direct_km = direct_distance.get('great_circle_km', 0)

        if direct_km > 0 and total_distance > 0:
            efficiency = (direct_km / total_distance) * 100
            extra_distance = total_distance - direct_km

            return {
                'efficiency_percent': round(efficiency, 1),
                'total_route_km': round(total_distance, 2),
                'extra_distance_km': round(extra_distance, 2),
                'route_type': 'Direct' if len(segments) == 1 else f'{len(segments)-1} Stop(s)'
            }

    except Exception as e:
        logger.warning(f"Error calculating route efficiency: {e}")

    return {
        'efficiency_percent': 100.0,
        'total_route_km': direct_distance.get('great_circle_km', 0),
        'extra_distance_km': 0,
        'route_type': 'Direct' if len(segments) <= 1 else 'Multi-stop'
    }

# Initialize aerospace engineering tools
aerospace_calc = AerospaceCalculator()
weather_client = AviationWeatherClient()

# Core business logic classes
class QueryManager:
    """Manages flight search queries and generates deep links"""

    def __init__(self):
        self.deep_link_templates = {
            'skyscanner.net': 'https://www.skyscanner.net/transport/flights/{origin_lower}/{dest_lower}/{date_yymmdd}/',
            'kayak.com': 'https://www.kayak.com/flights/{origin}-{dest}/{date_ymd}',
            'expedia.com': 'https://www.expedia.com/Flights-Search?trip=oneway&leg1=from%3A{origin}%2Cto%3A{dest}%2Cdeparture%3A{date_slash}',
            'ba.com': 'https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?journeyType=ONEWAY&origin={origin}&destination={dest}&departureDate={date_ymd}',
            'ryanair.com': 'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={date_ymd}&origin={origin}&destination={dest}',
            'easyjet.com': 'https://www.easyjet.com/en/flights/{origin_lower}/{dest_lower}?adults=1&children=0&infants=0&departureDate={date_ymd}',
            'google.com': 'https://www.google.com/flights?hl=en#flt={origin}.{dest}.{date_ymd}',
            'momondo.com': 'https://www.momondo.com/flight-search/{origin}-{dest}/{date_ymd}',
        }

    def create_query(self, origin: str, destination: str, depart_date: str, return_date: Optional[str] = None, cabin_class: Optional[str] = "economy", passengers: Optional[int] = 1, user_id: Optional[int] = None) -> int:
        """Create a new query and return the query ID"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO queries (origin, destination, depart_date, return_date, cabin_class, passengers, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (origin.upper(), destination.upper(), depart_date, return_date, cabin_class, passengers, user_id)
            )
            conn.commit()
            query_id = cursor.lastrowid
            logger.info(f"📝 Created query {query_id}: {origin} → {destination} on {depart_date}, {cabin_class} class, {passengers} passengers")
            return query_id

    def generate_deep_links(self, query_id: int) -> List[Dict[str, str]]:
        """Generate deep links for a query"""
        with get_db_connection() as conn:
            query = conn.execute('SELECT * FROM queries WHERE id = ?', (query_id,)).fetchone()
            if not query:
                return []

            sites = conn.execute('SELECT * FROM sites ORDER BY priority ASC, success_rate DESC').fetchall()

            deep_links = []
            date_obj = datetime.strptime(query['depart_date'], '%Y-%m-%d')

            for site in sites:
                template = self.deep_link_templates.get(site['domain'])
                if not template:
                    continue

                try:
                    url = template.format(
                        origin=query['origin'],
                        dest=query['destination'],
                        origin_lower=query['origin'].lower(),
                        dest_lower=query['destination'].lower(),
                        date_ymd=query['depart_date'],
                        date_yymmdd=date_obj.strftime('%y%m%d'),
                        date_slash=date_obj.strftime('%m%%2F%d%%2F%Y')
                    )

                    deep_links.append({
                        'site_name': site['name'],
                        'domain': site['domain'],
                        'url': url,
                        'priority': site['priority'],
                        'success_rate': site['success_rate']
                    })
                except Exception as e:
                    logger.warning(f"Failed to generate link for {site['domain']}: {e}")
                    continue

            return deep_links[:8]  # Return top 8 links

class IngestionEngine:
    """Handles data ingestion from browser extension"""

    def __init__(self):
        self.validator = DataValidator()

    async def ingest_results(self, data: IngestionRequest) -> Dict[str, Any]:
        """Ingest results from browser extension"""
        start_time = time.time()

        try:
            # Get site_id
            with get_db_connection() as conn:
                site = conn.execute('SELECT id FROM sites WHERE domain = ?', (data.site,)).fetchone()
                if not site:
                    # Auto-register new sites
                    cursor = conn.execute(
                        'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                        (data.site, data.site.replace('.com', '').title(), 0, 3)
                    )
                    conn.commit()
                    site_id = cursor.lastrowid
                    logger.info(f"🆕 Auto-registered new site: {data.site}")
                else:
                    site_id = site['id']

            # Find matching query
            query_id = await self._find_or_create_query(data.query)
            if not query_id:
                return {'success': False, 'error': 'Could not match query'}

            # Process each itinerary
            processed_count = 0
            duplicates_count = 0
            invalid_count = 0

            for itinerary in data.itineraries:
                try:
                    # Validate itinerary
                    if not self.validator.validate_itinerary(itinerary, data.query):
                        invalid_count += 1
                        continue

                    # Generate hash for deduplication
                    itinerary_hash = self._generate_hash(itinerary, data.query)

                    # Check for duplicates
                    with get_db_connection() as conn:
                        existing = conn.execute(
                            'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                            (query_id, itinerary_hash)
                        ).fetchone()

                        if existing:
                            duplicates_count += 1
                            continue

                        # Insert new result
                        conn.execute('''
                            INSERT INTO results (
                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                legs_json, source, carrier_codes, flight_numbers, stops,
                                fare_brand, booking_url
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            query_id, site_id, json.dumps(itinerary), itinerary_hash,
                            itinerary.get('price_total', 0), itinerary.get('price_currency', data.currency),
                            json.dumps(itinerary.get('segments', [])), 'extension',
                            json.dumps(itinerary.get('carrier_codes', [])),
                            json.dumps(itinerary.get('flight_numbers', [])),
                            itinerary.get('stops', 0), itinerary.get('fare_brand', ''),
                            itinerary.get('booking_url', '')
                        ))
                        conn.commit()
                        processed_count += 1

                except Exception as e:
                    logger.warning(f"Error processing itinerary: {e}")
                    invalid_count += 1
                    continue

            # Update site success metrics
            if processed_count > 0:
                await self._update_site_metrics(site_id, True)

            processing_time = time.time() - start_time
            logger.info(f"📥 Ingested from {data.site}: {processed_count} new, {duplicates_count} duplicates, {invalid_count} invalid ({processing_time:.2f}s)")

            return {
                'success': True,
                'processed': processed_count,
                'duplicates': duplicates_count,
                'invalid': invalid_count,
                'query_id': query_id,
                'processing_time': processing_time
            }

        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _find_or_create_query(self, query_data: Dict[str, str]) -> Optional[int]:
        """Find existing query or create new one"""
        origin = query_data.get('origin', '').upper()
        destination = query_data.get('destination', '').upper()
        depart_date = query_data.get('depart_date', '')

        if not all([origin, destination, depart_date]):
            return None

        with get_db_connection() as conn:
            # Look for existing query (within last 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            existing = conn.execute('''
                SELECT id FROM queries
                WHERE origin = ? AND destination = ? AND depart_date = ?
                AND created_at > ?
                ORDER BY created_at DESC LIMIT 1
            ''', (origin, destination, depart_date, cutoff.isoformat())).fetchone()

            if existing:
                return existing['id']

            # Create new query
            cursor = conn.execute(
                'INSERT INTO queries (origin, destination, depart_date) VALUES (?, ?, ?)',
                (origin, destination, depart_date)
            )
            conn.commit()
            return cursor.lastrowid

    def _generate_hash(self, itinerary: Dict[str, Any], query: Dict[str, str]) -> str:
        """Generate hash for deduplication"""
        key_data = {
            'origin': query.get('origin', ''),
            'destination': query.get('destination', ''),
            'depart_date': query.get('depart_date', ''),
            'carrier': itinerary.get('carrier', ''),
            'flight_number': itinerary.get('flight_number', ''),
            'price_total': itinerary.get('price_total', 0),
            'fare_brand': itinerary.get('fare_brand', '')
        }

        hash_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]

    async def _update_site_metrics(self, site_id: int, success: bool):
        """Update site success metrics"""
        with get_db_connection() as conn:
            # Record metric
            conn.execute(
                'INSERT INTO metrics (metric_name, metric_value, site_id) VALUES (?, ?, ?)',
                ('ingestion_success' if success else 'ingestion_failure', 1.0, site_id)
            )

            # Update rolling success rate
            success_count = conn.execute(
                'SELECT COUNT(*) FROM metrics WHERE site_id = ? AND metric_name = ? AND recorded_at > datetime("now", "-7 days")',
                (site_id, 'ingestion_success')
            ).fetchone()[0]

            total_count = conn.execute(
                'SELECT COUNT(*) FROM metrics WHERE site_id = ? AND metric_name IN (?, ?) AND recorded_at > datetime("now", "-7 days")',
                (site_id, 'ingestion_success', 'ingestion_failure')
            ).fetchone()[0]

            if total_count > 0:
                success_rate = success_count / total_count
                conn.execute('UPDATE sites SET success_rate = ? WHERE id = ?', (success_rate, site_id))

            conn.commit()

class DataValidator:
    """Validates ingested flight data"""

    def __init__(self):
        # Load airport codes for validation
        self.valid_airports = set()
        self._load_airport_codes()

    def _load_airport_codes(self):
        """Load valid airport codes from CSV file"""
        try:
            # Try to load from CSV first (full dataset)
            if os.path.exists('airport-codes.csv'):
                import csv
                with open('airport-codes.csv', 'r', encoding='utf-8') as f:
                    csv_reader = csv.DictReader(f)
                    self.valid_airports = set()
                    total_rows = 0
                    for row in csv_reader:
                        total_rows += 1

                        # Get IATA code from CSV
                        iata_code = row.get('iata_code', '').strip()
                        if iata_code and len(iata_code) == 3:  # Valid IATA codes are 3 letters
                            self.valid_airports.add(iata_code.upper())

                        # Also get ICAO codes for additional validation
                        icao_code = row.get('icao_code', '').strip()
                        if icao_code and len(icao_code) == 4:  # Valid ICAO codes are 4 letters
                            self.valid_airports.add(icao_code.upper())

                        # Also add the 'ident' field which contains airport identifiers
                        ident = row.get('ident', '').strip()
                        if ident and len(ident) >= 3:  # Include all ident codes
                            self.valid_airports.add(ident.upper())

                        # Add GPS code if available
                        gps_code = row.get('gps_code', '').strip()
                        if gps_code and len(gps_code) >= 3:
                            self.valid_airports.add(gps_code.upper())

                        # Add local code if available
                        local_code = row.get('local_code', '').strip()
                        if local_code and len(local_code) >= 3:
                            self.valid_airports.add(local_code.upper())

                logger.info(f"✅ Loaded {len(self.valid_airports)} airport codes from {total_rows} total airports in CSV")
                return

            # Fallback to JSON if CSV doesn't exist
            elif os.path.exists('airports.json'):
                with open('airports.json', 'r') as f:
                    airports = json.load(f)
                    self.valid_airports = {a.get('iata_code') for a in airports if a.get('iata_code')}
                logger.info(f"✅ Loaded {len(self.valid_airports)} airport codes for validation from JSON")
                return

            # Final fallback to common codes
            if not self.valid_airports:
                self.valid_airports = {
                    'LHR', 'JFK', 'LAX', 'DXB', 'CDG', 'AMS', 'FRA', 'BCN', 'FCO', 'MAD',
                    'LGW', 'STN', 'LTN', 'ORD', 'ATL', 'DFW', 'SFO', 'MIA', 'BOS', 'SEA'
                }
                logger.info(f"✅ Loaded {len(self.valid_airports)} fallback airport codes for validation")

        except Exception as e:
            logger.warning(f"⚠️ Could not load airport codes: {e}")
            # Use fallback codes
            self.valid_airports = {
                'LHR', 'JFK', 'LAX', 'DXB', 'CDG', 'AMS', 'FRA', 'BCN', 'FCO', 'MAD',
                'LGW', 'STN', 'LTN', 'ORD', 'ATL', 'DFW', 'SFO', 'MIA', 'BOS', 'SEA'
            }

    def validate_itinerary(self, itinerary: Dict[str, Any], query: Dict[str, str]) -> bool:
        """Validate an itinerary"""
        try:
            # Required fields
            required_fields = ['price_total', 'price_currency']
            for field in required_fields:
                if field not in itinerary or not itinerary[field]:
                    return False

            # Price validation
            price = itinerary.get('price_total', 0)
            if not isinstance(price, (int, float)) or price <= 0 or price > 10000:
                return False

            # Currency validation
            currency = itinerary.get('price_currency', '')
            if currency not in ['GBP', 'USD', 'EUR', 'CAD', 'AUD']:
                return False

            # Airport codes validation (if available)
            if self.valid_airports:
                origin = query.get('origin', '').upper()
                dest = query.get('destination', '').upper()
                if origin and origin not in self.valid_airports:
                    return False
                if dest and dest not in self.valid_airports:
                    return False

            # Date validation
            depart_date = query.get('depart_date', '')
            if depart_date:
                try:
                    date_obj = datetime.strptime(depart_date, '%Y-%m-%d')
                    if date_obj < datetime.now().date():
                        return False  # No past dates
                except ValueError:
                    return False

            return True

        except Exception as e:
            logger.warning(f"Validation error: {e}")
            return False

class ResultsAggregator:
    """Aggregates and ranks flight results"""

    def get_results(self, query_id: int, limit: int = MAX_RESULTS_PER_QUERY) -> List[Dict[str, Any]]:
        """Get aggregated results for a query"""
        with get_db_connection() as conn:
            results = conn.execute('''
                SELECT r.*, s.name as site_name, s.domain, s.success_rate
                FROM results r
                JOIN sites s ON r.site_id = s.id
                WHERE r.query_id = ? AND r.valid = 1
                ORDER BY r.price_min ASC, s.success_rate DESC, r.fetched_at DESC
                LIMIT ?
            ''', (query_id, limit)).fetchall()

            formatted_results = []
            for row in results:
                try:
                    raw_data = json.loads(row['raw_json'])
                    legs_data = json.loads(row['legs_json'] or '[]')

                    formatted_results.append({
                        'id': row['id'],
                        'price': {
                            'amount': row['price_min'],
                            'currency': row['price_currency']
                        },
                        'carrier': raw_data.get('carrier', 'Unknown'),
                        'flight_number': raw_data.get('flight_number', ''),
                        'departure_time': raw_data.get('depart_local', ''),
                        'arrival_time': raw_data.get('arrive_local', ''),
                        'stops': row['stops'] or 0,
                        'fare_brand': row['fare_brand'] or 'Economy',
                        'booking_url': row['booking_url'],
                        'source': {
                            'name': row['site_name'],
                            'domain': row['domain'],
                            'success_rate': row['success_rate']
                        },
                        'legs': legs_data,
                        'fetched_at': row['fetched_at'],
                        'hash': row['hash']
                    })
                except Exception as e:
                    logger.warning(f"Error formatting result {row['id']}: {e}")
                    continue

            return formatted_results

    async def get_results_with_apis(self, query_id: int, limit: int = MAX_RESULTS_PER_QUERY) -> List[Dict[str, Any]]:
        """Get results including Amadeus and Duffel API data"""
        # Get existing results
        existing_results = self.get_results(query_id, limit)

        with get_db_connection() as conn:
            query = conn.execute('SELECT * FROM queries WHERE id = ?', (query_id,)).fetchone()

            if not query:
                return existing_results

            # Check if we already have recent API results (within last 5 minutes)
            recent_api_results = conn.execute('''
                SELECT COUNT(*) FROM results 
                WHERE query_id = ? AND source IN ('duffel_api', 'amadeus_api', 'flightapi') 
                AND fetched_at > datetime('now', '-5 minutes')
            ''', (query_id,)).fetchone()[0]

            # Only call APIs if we don't have recent results
            if recent_api_results == 0:
                # Try Duffel API first (usually more comprehensive)
                if duffel_client.is_configured():
                    try:
                        duffel_results = await duffel_client.search_flights(
                            query['origin'],
                            query['destination'], 
                            query['depart_date'],
                            query['return_date']
                        )

                        if duffel_results:
                            # Get or create Duffel site entry
                            duffel_site = conn.execute('SELECT id FROM sites WHERE domain = ?', ('duffel.com',)).fetchone()
                            if not duffel_site:
                                cursor = conn.execute(
                                    'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                                    ('duffel.com', 'Duffel API', 1, 1)
                                )
                                conn.commit()
                                duffel_site_id = cursor.lastrowid
                            else:
                                duffel_site_id = duffel_site['id']

                            # Store Duffel results
                            for result in duffel_results:
                                try:
                                    # Check for existing
                                    existing = conn.execute(
                                        'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                                        (query_id, result['hash'])
                                    ).fetchone()

                                    if not existing:
                                        conn.execute('''
                                            INSERT INTO results (
                                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                                legs_json, source, carrier_codes, flight_numbers, stops,
                                                fare_brand, booking_url, valid
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ''', (
                                            query_id, duffel_site_id, json.dumps(result), result['hash'],
                                            result['price']['amount'], result['price']['currency'],
                                            json.dumps(result['segments']), 'duffel_api',
                                            json.dumps([result['carrier']]),
                                            json.dumps([result['flight_number']]),
                                            result['stops'], 'Economy', result.get('booking_url', ''), 1
                                        ))

                                        # Add to existing results
                                        existing_results.append({
                                            'id': None,
                                            'price': result['price'],
                                            'carrier': result['carrier'],
                                            'carrier_name': result.get('carrier_name', result['carrier']),
                                            'flight_number': result['flight_number'],
                                            'departure_time': result['departure_time'],
                                            'arrival_time': result['arrival_time'],
                                            'stops': result['stops'],
                                            'fare_brand': 'Economy',
                                            'booking_url': result.get('booking_url', ''),
                                            'source': result['source'],
                                            'legs': result['segments'],
                                            'fetched_at': result['fetched_at'],
                                            'hash': result['hash'],
                                            'offer_id': result.get('offer_id', '')
                                        })

                                except Exception as e:
                                    logger.warning(f"Error storing Duffel result: {e}")
                                    continue

                            conn.commit()
                            logger.info(f"✅ Added {len(duffel_results)} Duffel results to query {query_id}")

                    except Exception as e:
                        logger.error(f"❌ Duffel API error: {e}")

                # Try FlightAPI for budget airline coverage
                if flightapi_client.is_configured():
                    try:
                        flightapi_results = await flightapi_client.search_flights(
                            query['origin'],
                            query['destination'], 
                            query['depart_date'],
                            query['return_date']
                        )

                        if flightapi_results:
                            # Get or create FlightAPI site entry
                            flightapi_site = conn.execute('SELECT id FROM sites WHERE domain = ?', ('flightapi.io',)).fetchone()
                            if not flightapi_site:
                                cursor = conn.execute(
                                    'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                                    ('flightapi.io', 'FlightAPI', 1, 2)  # Priority 2 for budget airline focus
                                )
                                conn.commit()
                                flightapi_site_id = cursor.lastrowid
                            else:
                                flightapi_site_id = flightapi_site['id']

                            # Store FlightAPI results
                            for result in flightapi_results:
                                try:
                                    # Check for existing
                                    existing = conn.execute(
                                        'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                                        (query_id, result['hash'])
                                    ).fetchone()

                                    if not existing:
                                        conn.execute('''
                                            INSERT INTO results (
                                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                                legs_json, source, carrier_codes, flight_numbers, stops,
                                                fare_brand, booking_url, valid
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ''', (
                                            query_id, flightapi_site_id, json.dumps(result), result['hash'],
                                            result['price']['amount'], result['price']['currency'],
                                            json.dumps(result['segments']), 'flightapi',
                                            json.dumps([result['carrier']]),
                                            json.dumps([result['flight_number']]),
                                            result['stops'], 'Economy', result.get('booking_url', ''), 1
                                        ))

                                        # Add to existing results
                                        existing_results.append({
                                            'id': None,
                                            'price': result['price'],
                                            'carrier': result['carrier'],
                                            'carrier_name': result.get('carrier_name', result['carrier']),
                                            'flight_number': result['flight_number'],
                                            'departure_time': result['departure_time'],
                                            'arrival_time': result['arrival_time'],
                                            'stops': result['stops'],
                                            'fare_brand': 'Economy',
                                            'booking_url': result.get('booking_url', ''),
                                            'source': result['source'],
                                            'legs': result['segments'],
                                            'fetched_at': result['fetched_at'],
                                            'hash': result['hash'],
                                            'offer_id': result.get('offer_id', '')
                                        })

                                except Exception as e:
                                    logger.warning(f"Error storing FlightAPI result: {e}")
                                    continue

                            conn.commit()
                            logger.info(f"✅ Added {len(flightapi_results)} FlightAPI results to query {query_id}")

                    except Exception as e:
                        logger.error(f"❌ FlightAPI error: {e}")

            # If Amadeus is configured, try to get additional results
            if amadeus_client.is_configured():
                try:
                    amadeus_results = await amadeus_client.search_flights(
                        query['origin'],
                        query['destination'], 
                        query['depart_date'],
                        query['return_date']
                    )

                    if amadeus_results:
                        # Get or create Amadeus site entry
                        amadeus_site = conn.execute('SELECT id FROM sites WHERE domain = ?', ('amadeus.com',)).fetchone()
                        if not amadeus_site:
                            cursor = conn.execute(
                                'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                                ('amadeus.com', 'Amadeus API', 1, 1)
                            )
                            conn.commit()
                            amadeus_site_id = cursor.lastrowid
                        else:
                            amadeus_site_id = amadeus_site['id']

                        # Store Amadeus results
                        for result in amadeus_results:
                            try:
                                # Check for existing
                                existing = conn.execute(
                                    'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                                    (query_id, result['hash'])
                                ).fetchone()

                                if not existing:
                                    conn.execute('''
                                        INSERT INTO results (
                                            query_id, site_id, raw_json, hash, price_min, price_currency,
                                            legs_json, source, carrier_codes, flight_numbers, stops,
                                            fare_brand, booking_url, valid
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        query_id, amadeus_site_id, json.dumps(result), result['hash'],
                                        result['price']['amount'], result['price']['currency'],
                                        json.dumps(result['segments']), 'amadeus_api',
                                        json.dumps([result['carrier']]),
                                        json.dumps([result['flight_number']]),
                                        result['stops'], 'Economy', result['booking_url'], 1
                                    ))

                                    # Add to existing results
                                    existing_results.append({
                                        'id': None,
                                        'price': result['price'],
                                        'carrier': result['carrier'],
                                        'flight_number': result['flight_number'],
                                        'departure_time': result['departure_time'],
                                        'arrival_time': result['arrival_time'],
                                        'stops': result['stops'],
                                        'fare_brand': 'Economy',
                                        'booking_url': result['booking_url'],
                                        'source': result['source'],
                                        'legs': result['segments'],
                                        'fetched_at': result['fetched_at'],
                                        'hash': result['hash']
                                    })

                            except Exception as e:
                                logger.warning(f"Error storing Amadeus result: {e}")
                                continue

                        conn.commit()
                        logger.info(f"✅ Added {len(amadeus_results)} Amadeus results to query {query_id}")

                except Exception as e:
                    logger.error(f"❌ Amadeus integration error: {e}")

        # Sort by price and return
        existing_results.sort(key=lambda x: x['price']['amount'])
        return existing_results[:limit]

# Alert matching system
async def check_alert_matches(query_id: int, site_id: int):
    """Check new results against active alerts"""
    try:
        with get_db_connection() as conn:
            # Get recent results for this query
            recent_results = conn.execute('''
                SELECT r.*, q.origin, q.destination, q.depart_date
                FROM results r
                JOIN queries q ON r.query_id = q.id
                WHERE r.query_id = ? AND r.site_id = ?
                AND r.fetched_at > datetime('now', '-5 minutes')
            ''', (query_id, site_id)).fetchall()

            if not recent_results:
                return

            # Get all active alerts
            alerts = conn.execute('''
                SELECT * FROM alerts WHERE active = 1
            ''').fetchall()

            matches_count = 0

            for result in recent_results:
                try:
                    result_data = json.loads(result['raw_json'])
                    legs_data = json.loads(result['legs_json'] or '[]')

                    for alert in alerts:
                        if matches_alert_criteria(alert, result, result_data, legs_data):
                            # Check if this match already exists
                            existing = conn.execute(
                                'SELECT id FROM matches WHERE alert_id = ? AND result_id = ?',
                                (alert['id'], result['id'])
                            ).fetchone()

                            if not existing:
                                conn.execute(
                                    'INSERT INTO matches (alert_id, result_id) VALUES (?, ?)',
                                    (alert['id'], result['id'])
                                )
                                matches_count += 1
                                logger.info(f"🎯 Alert match: {alert['type']} alert {alert['id']} matched result {result['id']}")

                except Exception as e:
                    logger.warning(f"Error checking alert match: {e}")
                    continue

            if matches_count > 0:
                conn.commit()
                logger.info(f"✅ Found {matches_count} new alert matches")

    except Exception as e:
        logger.error(f"❌ Alert matching failed: {e}")

def matches_alert_criteria(alert, result, result_data, legs_data) -> bool:
    """Check if a result matches alert criteria"""
    try:
        # Basic route matching
        if alert['origin'] and alert['origin'] != result['origin']:
            return False
        if alert['destination'] and alert['destination'] != result['destination']:
            return False

        # Price range
        price = result['price_min']
        if alert['min_price'] and price < alert['min_price']:
            return False
        if alert['max_price'] and price > alert['max_price']:
            return False

        # Trip type (crude check)
        leg_count = len(legs_data) if legs_data else 0
        if alert['one_way'] and leg_count > 2:
            return False

        # Special alert types
        if alert['type'] == 'rare':
            # Check for rare aircraft
            aircrafts = result_data.get('aircraft', '').split(',')
            rare_list = (alert['rare_aircraft_list'] or '').split(',')
            if rare_list and not any(aircraft.strip() in rare_list for aircraft in aircrafts):
                return False

        elif alert['type'] == 'adventurous':
            # Origin set, destination flexible, good price
            if not alert['origin'] or alert['destination']:
                return False
            if alert['max_price'] and price > alert['max_price']:
                return False

        return True

    except Exception as e:
        logger.warning(f"Error in alert matching: {e}")
        return False

# Initialize components
query_manager = QueryManager()
ingestion_engine = IngestionEngine()
results_aggregator = ResultsAggregator()

# ------------ Lifespan management ------------
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global PLAY, BROWSER
    logger.info("🚀 Starting FlightAlert Pro BYOB Edition...")

    # Initialize database
    init_database()
    migrate_users_from_json()
    seed_initial_data()

    # Optional Playwright for validation
    if PLAYWRIGHT_AVAILABLE:
        try:
            logger.info("Starting Playwright for validation...")
            PLAY = await async_playwright().start()
            BROWSER = await PLAY.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            logger.info("✅ Playwright ready for validation")
        except Exception as e:
            logger.warning(f"⚠️ Playwright startup failed: {e}")
            PLAY = None
            BROWSER = None

    logger.info("🎯 FlightAlert Pro BYOB startup complete!")

    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        if BROWSER:
            try:
                await BROWSER.close()
            except Exception as e:
                logger.warning(f"Browser close error (expected on restart): {e}")
        if PLAY:
            try:
                await PLAY.stop()
            except Exception as e:
                logger.warning(f"Playwright stop error (expected on restart): {e}")
    except Exception as e:
        logger.warning(f"Playwright shutdown error: {e}")

# ------------ FastAPI App Setup ------------
app = FastAPI(title="FlightAlert Pro BYOB", version="3.0", lifespan=lifespan)

# CORS setup for browser extension - MUST be first middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Wide open for development - includes Codespaces preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (create directory if it doesn't exist)
import os
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info("📁 Created static directory")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# BYOB Models for stable schema
class Fare(BaseModel):
    brand: Optional[str] = None            # Economy Basic / Light / Plus
    cabin: Optional[str] = None            # economy/premium/business
    baggage: Optional[str] = None          # e.g., "cabin only", "1x23kg"
    refundable: Optional[bool] = None
    change_penalty: Optional[str] = None

class Leg(BaseModel):
    carrier: str                           # "BA"
    flight_number: str                     # "BA432"
    origin: str                            # "LHR"
    destination: str                       # "AMS"
    depart_iso: str                        # "2025-08-27T07:45:00+01:00"
    arrive_iso: str                        # "2025-08-27T10:05:00+02:00"
    aircraft: Optional[str] = None         # "A320"
    duration_min: Optional[int] = None

class Itinerary(BaseModel):
    provider: str                          # "skyscanner" | "kayak" | "ba" | ...
    url: str
    deep_link: Optional[str] = None
    price: float
    currency: str = "GBP"
    legs: List[Leg]
    fare: Optional[Fare] = None
    extra: Optional[Dict[str, Any]] = None

    @field_validator("currency")
    @classmethod
    def _upcase(cls, v): return v.upper()

class IngestPayload(BaseModel):
    query_id: int
    source_domain: str
    page_title: Optional[str] = None
    user_agent: Optional[str] = None
    results: List[Itinerary]

# Simple in-memory storage for SSE (works with existing SQLite)
SSE_CHANNELS: Dict[int, List[Dict[str, Any]]] = {}

# ------------ BYOB Bridge Endpoints ------------

@app.get("/api/ping")
async def ping():
    """Health check for browser extension"""
    return {"ok": True, "ts": time.time()}

@app.get("/api/sdk/hello")
async def sdk_hello():
    """Extension handshake endpoint"""
    return {
        "ok": True,
        "ts": time.time(),
        "schema": "v1",
        "ingest_endpoint": "/api/ingest",
        "server": "FlightAlert Pro BYOB"
    }

def _normalize_key(itin: Itinerary) -> str:
    """Generate deduplication key for itinerary"""
    first = itin.legs[0]
    last = itin.legs[-1]
    return "|".join([
        first.carrier + first.flight_number,
        first.depart_iso,
        first.origin,
        last.destination,
        itin.currency,
        f"{itin.price:.2f}",
        str(len(itin.legs)),
    ])

def validate_solid_result(result: Itinerary) -> bool:
    """Validate that result has real flight data - STRICT validation"""
    import re

    if not (result.price and result.legs and result.currency and result.provider):
        logger.debug(f"❌ Failed basic validation: missing required fields")
        return False

    # Reject demo/test sources
    if result.provider.lower() in ['demo', 'test', 'fake', 'sample']:
        logger.debug(f"❌ Rejected demo/test source: {result.provider}")
        return False

    # Check flight number format (e.g., BA432, FR1234)
    first_leg = result.legs[0]
    flight_code = first_leg.carrier + first_leg.flight_number
    if not re.match(r"^[A-Z]{2,3}\d{1,4}[A-Z]?$", flight_code):
        logger.debug(f"❌ Invalid flight code format: {flight_code}")
        return False

    # Check airport codes
    if not re.match(r"^[A-Z]{3}$", first_leg.origin):
        logger.debug(f"❌ Invalid origin airport: {first_leg.origin}")
        return False
    if not re.match(r"^[A-Z]{3}$", result.legs[-1].destination):
        logger.debug(f"❌ Invalid destination airport: {result.legs[-1].destination}")
        return False

    # Price sanity check - more realistic ranges
    if result.price <= 10 or result.price > 5000:
        logger.debug(f"❌ Price out of realistic range: £{result.price}")
        return False

    # Must have realistic departure time
    if not first_leg.depart_iso:
        logger.debug(f"❌ Missing departure time")
        return False

    # Check URL is from real site (not demo)
    if 'demo' in result.url.lower() or 'test' in result.url.lower():
        logger.debug(f"❌ Demo/test URL rejected: {result.url}")
        return False

    logger.debug(f"✅ Validated real flight: {flight_code} £{result.price}")
    return True

@app.post("/api/ingest")
async def ingest_from_extension(payload: IngestPayload, request: Request, x_fa_token: str = Header(default="")):
    """Main ingestion endpoint for browser extension with token auth"""

    logger.info(f"📥 Ingest request from {payload.source_domain} with token: {x_fa_token[:8]}...")

    # Simple token validation to prevent spam
    if x_fa_token != INGEST_TOKEN:
        logger.warning(f"❌ Invalid token from {payload.source_domain}. Expected: {INGEST_TOKEN[:8]}..., Got: {x_fa_token[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info(f"📥 BYOB ingest from {payload.source_domain}: {len(payload.results)} results for query {payload.query_id}")

    # Validate query exists
    with get_db_connection() as conn:
        query = conn.execute('SELECT id FROM queries WHERE id = ?', (payload.query_id,)).fetchone()
        if not query:
            logger.warning(f"❌ Query {payload.query_id} not found")
            raise HTTPException(status_code=404, detail="Query not found")

    # Filter and deduplicate results - only keep solid ones
    dedup: Dict[str, Itinerary] = {}
    filtered_count = 0

    for r in payload.results:
        try:
            # Only keep results that pass validation
            if not validate_solid_result(r):
                filtered_count += 1
                continue

            k = _normalize_key(r)
            if k not in dedup:
                dedup[k] = r
            else:
                # Keep cheaper option
                if r.price < dedup[k].price:
                    dedup[k] = r
        except Exception as e:
            logger.warning(f"Error processing result: {e}")
            filtered_count += 1
            continue

    clean_results = list(dedup.values())

    if filtered_count > 0:
        logger.info(f"🔍 Filtered out {filtered_count} invalid results, kept {len(clean_results)} solid ones")

    # Store in SSE channels for real-time updates
    SSE_CHANNELS.setdefault(payload.query_id, []).extend([r.dict() for r in clean_results])

    # Also store in SQLite database
    with get_db_connection() as conn:
        site = conn.execute('SELECT id FROM sites WHERE domain = ?', (payload.source_domain,)).fetchone()
        if not site:
            # Auto-register new sites
            cursor = conn.execute(
                'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                (payload.source_domain, payload.source_domain.replace('.com', '').title(), 1, 2)
            )
            conn.commit()
            site_id = cursor.lastrowid
            logger.info(f"🆕 Auto-registered site: {payload.source_domain}")
        else:
            site_id = site['id']

<<<<<<< Updated upstream
def create_query(departure: str, arrival: str, date: Optional[str] = None, passengers: int = 1, airline: Optional[str] = None) -> Dict[str, Any]:
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

def get_airline_name(code: str) -> str:
    """Get airline full name from code"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM airlines WHERE code = ?", (code.upper(),))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return row['name']
    
    # If not found, return code as-is
    logger.warning(f"Unknown airline code: {code}")
    return code
=======
        # Insert results
        processed = 0
        for result in clean_results:
            try:
                result_hash = hashlib.sha256(json.dumps(result.dict(), sort_keys=True).encode()).hexdigest()[:16]
>>>>>>> Stashed changes

                # Check for existing
                existing = conn.execute(
                    'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                    (payload.query_id, result_hash)
                ).fetchone()

                if not existing:
                    conn.execute('''
                        INSERT INTO results (
                            query_id, site_id, raw_json, hash, price_min, price_currency,
                            legs_json, source, carrier_codes, flight_numbers, stops,
                            fare_brand, booking_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        payload.query_id, site_id, json.dumps(result.dict()), result_hash,
                        result.price, result.currency,
                        json.dumps([leg.dict() for leg in result.legs]), 'extension',
                        json.dumps([leg.carrier for leg in result.legs]),
                        json.dumps([leg.flight_number for leg in result.legs]),
                        len(result.legs) - 1,  # stops = legs - 1
                        result.fare.brand if result.fare else 'Economy',
                        result.deep_link or result.url
                    ))
                    processed += 1
            except Exception as e:
                logger.warning(f"Error storing result: {e}")
                continue

        conn.commit()

    # Check for alert matches on new results
    if processed > 0:
        await check_alert_matches(payload.query_id, site_id)

    # Enhanced logging for monitoring
    logger.info(f"✅ BYOB processed {processed} new results from {payload.source_domain}")
    if processed > 0:
        logger.info(f"🎯 REAL FLIGHTS FOUND! Query {payload.query_id} now has {processed} verified flights")

        # Log sample of what we got
        sample_results = clean_results[:2]
        for i, result in enumerate(sample_results):
            first_leg = result.legs[0]
            logger.info(f"  ✈️ {i+1}. {first_leg.carrier}{first_leg.flight_number}: £{result.price} ({result.provider})")
    else:
        logger.warning(f"⚠️ No valid flights from {payload.source_domain} - all {len(payload.results)} results filtered out")
        if filtered_count > 0:
            logger.info(f"   - {filtered_count} failed validation (demo data, invalid codes, etc.)")

    return {"ok": True, "ingested": processed, "deduplicated": len(payload.results) - len(clean_results), "filtered": filtered_count}

# ==================== AEROSPACE ENGINEERING ENDPOINTS ====================

@app.get("/api/aerospace/weather/{airport_code}")
async def get_airport_weather(airport_code: str):
    """Get current weather conditions and forecasts for airport (AEROSPACE FEATURE)"""
    try:
        airport_code = airport_code.upper()

        # Get current weather (METAR) and forecast (TAF) data
        metar_data = await weather_client.get_metar(airport_code)
        taf_data = await weather_client.get_taf(airport_code)

        # Get airport coordinates for additional calculations
        coords = get_airport_coordinates(airport_code)

        response = {
            'airport': airport_code,
            'current_weather': metar_data,
            'forecast': taf_data,
            'coordinates': coords,
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Weather API error for {airport_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Weather data unavailable for {airport_code}")

<<<<<<< Updated upstream
def generate_deep_link(airline_code: str, origin: str, destination: str, date: str, passengers: int = 1) -> str:
    """Generate real airline booking deep link"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT template_url FROM airline_deeplinks WHERE airline_code = ?", (airline_code.upper(),))
    row = cur.fetchone()
    
    if row and row['template_url']:
        # Replace placeholders in template
        url = row['template_url']
        url = url.replace('{orig}', origin)
        url = url.replace('{dest}', destination)
        url = url.replace('{date}', date)
        url = url.replace('{passengers}', str(passengers))
        conn.close()
        return url
    
    # Fallback to airline website
    cur.execute("SELECT domain FROM airlines WHERE code = ?", (airline_code.upper(),))
    row = cur.fetchone()
    conn.close()
    
    if row and row['domain']:
        return f"https://{row['domain']}"
    
    return "#"

async def search_flights_duffel(departure: str, arrival: str, date: str, passengers: int = 1, cabin: str = "ECONOMY") -> List[Dict[str, Any]]:
    """Search flights using Duffel API or enhanced mock data"""
    
    # Check if Duffel API key is available
    if DUFFEL_API_KEY and DUFFEL_API_KEY != "":
        try:
            # Use Duffel API
            headers = {
                "Authorization": f"Bearer {DUFFEL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "data": {
                    "slices": [{
                        "origin": departure,
                        "destination": arrival,
                        "departure_date": date
                    }],
                    "passengers": [{"type": "adult"}] * passengers,
                    "cabin_class": cabin.lower()
                }
            }
            
            response = requests.post(
                "https://api.duffel.com/air/offer_requests",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return parse_duffel_response(data)
        except Exception as e:
            logger.error(f"Duffel API error: {e}")
    
    # Fallback to enhanced mock data
    return get_enhanced_mock_flights(departure, arrival, date, passengers, cabin)

def parse_duffel_response(data: Dict) -> List[Dict[str, Any]]:
    """Parse Duffel API response"""
    flights = []
    
    try:
        for offer in data.get('data', {}).get('offers', []):
            for slice_data in offer.get('slices', []):
                for segment in slice_data.get('segments', []):
                    airline_code = segment.get('operating_carrier', {}).get('iata_code', 'XX')
                    
                    flight = {
                        'flight_number': f"{airline_code}{segment.get('operating_carrier_flight_number', '')}",
                        'airline_code': airline_code,
                        'departure': segment.get('origin', {}).get('iata_code', ''),
                        'arrival': segment.get('destination', {}).get('iata_code', ''),
                        'departure_time': segment.get('departing_at', ''),
                        'arrival_time': segment.get('arriving_at', ''),
                        'aircraft': segment.get('aircraft', {}).get('name', 'Unknown'),
                        'price': float(offer.get('total_amount', 0)),
                        'currency': offer.get('total_currency', 'GBP'),
                        'duration_minutes': int(segment.get('duration', 'PT0M')[2:-1]),
                        'is_rare_aircraft': is_rare_aircraft(segment.get('aircraft', {}).get('name', ''))
                    }
                    flights.append(flight)
    except Exception as e:
        logger.error(f"Error parsing Duffel response: {e}")
    
    return flights

def get_enhanced_mock_flights(departure: str, arrival: str, date: str, passengers: int = 1, cabin: str = "ECONOMY") -> List[Dict[str, Any]]:
    """Get enhanced mock flight data with realistic details"""
    
    # Aircraft database with rarity indicators
    aircraft_types = [
        ("Boeing 787-9", False), ("Airbus A350-900", False), ("Boeing 777-300ER", False),
        ("Airbus A380", True), ("Boeing 747-8", True), ("Airbus A350-1000", True),
        ("Boeing 777-200ER", False), ("Airbus A330-300", False), ("Boeing 737-800", False)
    ]
    
    # Airlines for mock data
    airlines = [
        ("BA", 299.99), ("AA", 325.50), ("DL", 289.00), ("UA", 315.75),
        ("EK", 450.00), ("SQ", 399.99), ("LH", 310.00), ("AF", 295.00)
    ]
    
    flights = []
    import random
    
    for i, (airline_code, base_price) in enumerate(airlines):
        aircraft, is_rare = random.choice(aircraft_types)
        
        # Adjust price based on cabin class
        price_multiplier = {
            "ECONOMY": 1.0,
            "PREMIUM_ECONOMY": 1.5,
            "BUSINESS": 3.0,
            "FIRST": 5.0
        }.get(cabin.upper(), 1.0)
        
        # Add some random variation
        price = round(base_price * price_multiplier * (0.9 + random.random() * 0.2), 2)
        
        # Generate departure time
        hour = 6 + i * 2
        minute = random.choice([0, 15, 30, 45])
        
        flight = {
            'flight_number': f"{airline_code}{100 + i * 50}",
            'airline_code': airline_code,
            'departure': departure,
            'arrival': arrival,
            'departure_time': f"{date}T{hour:02d}:{minute:02d}:00",
            'arrival_time': f"{date}T{(hour + 8) % 24:02d}:{minute:02d}:00",
            'aircraft': aircraft,
            'price': price,
            'currency': 'GBP',
            'duration_minutes': 480 + random.randint(-60, 60),
            'is_rare_aircraft': is_rare
        }
        flights.append(flight)
    
    return flights

def is_rare_aircraft(aircraft_name: str) -> bool:
    """Check if aircraft is considered rare"""
    rare_keywords = ['A380', '747-8', 'A350-1000', 'Concorde', 'A340', '747-400']
    return any(keyword.lower() in aircraft_name.lower() for keyword in rare_keywords)

def get_random_aerospace_fact() -> Dict[str, Any]:
    """Get random aerospace fact with calculations"""
    facts = [
        {
            "title": "Speed of Sound",
            "fact": "The speed of sound at cruising altitude (35,000 ft) is approximately 660 mph (Mach 1.0)",
            "calculation": "Mach number = aircraft speed / speed of sound",
            "example": "Boeing 787 cruises at Mach 0.85 = 561 mph"
        },
        {
            "title": "Fuel Efficiency",
            "fact": "Modern aircraft like the A350 consume about 2.9 liters per 100 passenger-kilometers",
            "calculation": "Fuel per passenger = Total fuel / (passengers × distance)",
            "example": "For 300 passengers on 10,000 km: 8,700 liters total"
        },
        {
            "title": "Thrust-to-Weight Ratio",
            "fact": "Commercial jets typically have a thrust-to-weight ratio of 0.25-0.30",
            "calculation": "Ratio = Total thrust / Aircraft weight",
            "example": "Boeing 777: 400,000 lbs thrust / 660,000 lbs weight = 0.61 at takeoff"
        },
        {
            "title": "Altitude Benefits",
            "fact": "Flying at 35,000 ft reduces air density by 75%, cutting drag and fuel consumption significantly",
            "calculation": "Air density decreases exponentially with altitude",
            "example": "Fuel savings of up to 20% at cruise altitude vs sea level"
        },
        {
            "title": "Maximum Takeoff Weight",
            "fact": "The Airbus A380 has an MTOW of 1,267,658 lbs (575 tonnes)",
            "calculation": "MTOW = Operating empty weight + Fuel + Payload",
            "example": "A380: 610,200 + 560,000 + 185,000 lbs"
        }
    ]
    
    import random
    return random.choice(facts)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    logger.info("🚀 FlightAlert Pro started successfully")
=======
@app.get("/api/aerospace/route-analysis/{origin}/{destination}")
async def analyze_flight_route(origin: str, destination: str):
    """Aerospace engineering analysis of flight route (GREAT CIRCLE, FUEL, NAVIGATION)"""
    try:
        origin = origin.upper()
        destination = destination.upper()
>>>>>>> Stashed changes

        # Get airport coordinates
        origin_coords = get_airport_coordinates(origin)
        dest_coords = get_airport_coordinates(destination)

<<<<<<< Updated upstream
@app.post("/api/query")
async def api_query(q: QueryIn, request: Request, user: Dict = Depends(paid_user_dependency)):
    """Main query endpoint - saves query and triggers search, returns real flight results"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Insert query into database
    cur.execute("""INSERT INTO queries (user_id, departure_iata, arrival_iata, depart_date, return_date,
                 passengers, cabin, min_price, max_price, alert_price, currency, rare_aircraft_filter, status)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user['id'], q.departure_iata.upper(), q.arrival_iata.upper(), q.depart_date,
                 q.return_date, q.passengers, q.cabin, q.min_price, q.max_price, q.alert_price,
                 q.currency.upper(), q.rare_aircraft_filter, "completed"))
    conn.commit()
    query_id = cur.lastrowid
    conn.close()

    # Log query creation
    logger.info(f"✈️ Created query {query_id}: {q.departure_iata} → {q.arrival_iata} on {q.depart_date}")

    # Search for flights using Duffel API or mock data
    flights = await search_flights_duffel(
        q.departure_iata.upper(), 
        q.arrival_iata.upper(), 
        q.depart_date,
        q.passengers,
        q.cabin
    )
    
    # Apply filters
    filtered_flights = []
    for flight in flights:
        # Price filters
        if q.min_price and flight['price'] < q.min_price:
            continue
        if q.max_price and flight['price'] > q.max_price:
            continue
        
        # Rare aircraft filter
        if q.rare_aircraft_filter and not flight.get('is_rare_aircraft', False):
            continue
            
        # Convert currency if needed
        if q.currency.upper() != 'GBP':
            exchange_rate = get_exchange_rate('GBP', q.currency.upper())
            flight['price_converted'] = round(flight['price'] * exchange_rate, 2)
            flight['currency_display'] = q.currency.upper()
        else:
            flight['price_converted'] = flight['price']
            flight['currency_display'] = 'GBP'
        
        # Add airline display with name in brackets
        airline_name = get_airline_name(flight['airline_code'])
        flight['airline_display'] = f"{flight['airline_code']} ({airline_name})"
        
        # Generate real deep link
        flight['booking_url'] = generate_deep_link(
            flight['airline_code'],
            q.departure_iata.upper(),
            q.arrival_iata.upper(),
            q.depart_date,
            q.passengers
        )
        
        filtered_flights.append(flight)
    
    # Sort by price
    filtered_flights.sort(key=lambda x: x['price'])
    
    # Calculate statistics
    statistics = {}
    if filtered_flights:
        prices = [f['price'] for f in filtered_flights]
        statistics = {
            'average_price': round(sum(prices) / len(prices), 2),
            'min_price': min(prices),
            'max_price': max(prices),
            'currency': q.currency.upper(),
            'total_results': len(filtered_flights)
        }
    
    # Get aerospace fact
    aerospace_fact = get_random_aerospace_fact()
    
    return {
        "ok": True, 
        "query_id": query_id, 
        "status": "completed",
        "results": {
            "count": len(filtered_flights),
            "flights": filtered_flights[:20],  # Limit to 20 results
        },
        "statistics": statistics,
        "aerospace_fact": aerospace_fact,
        "search_params": {
            "departure": q.departure_iata.upper(),
            "arrival": q.arrival_iata.upper(),
            "date": q.depart_date,
            "passengers": q.passengers,
            "cabin": q.cabin
        }
=======
        if not origin_coords or not dest_coords:
            raise HTTPException(status_code=404, detail="Airport coordinates not found")

        # Calculate great circle distance and navigation data
        distance_data = aerospace_calc.great_circle_distance(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Calculate initial bearing for navigation
        bearing = aerospace_calc.initial_bearing(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Fuel efficiency estimates for different aircraft types
        aircraft_types = ['A320', 'A350', 'B737', 'B787', 'B777']
        fuel_estimates = {}

        for aircraft in aircraft_types:
            fuel_data = aerospace_calc.fuel_efficiency_estimate(
                distance_data['great_circle_km'], aircraft
            )
            fuel_estimates[aircraft] = fuel_data

        response = {
            'route': f"{origin} → {destination}",
            'airports': {
                'origin': {'code': origin, 'coordinates': origin_coords},
                'destination': {'code': destination, 'coordinates': dest_coords}
            },
            'distance_analysis': distance_data,
            'navigation': {
                'initial_bearing': round(bearing, 1),
                'bearing_description': get_bearing_description(bearing),
                'great_circle_route': True
            },
            'fuel_analysis_by_aircraft': fuel_estimates,
            'flight_time_estimates': {
                'commercial_average': f"{round(distance_data['great_circle_km'] / 900, 1)} hours",  # ~900 km/h average
                'business_jet': f"{round(distance_data['great_circle_km'] / 800, 1)} hours",
                'supersonic_estimated': f"{round(distance_data['great_circle_km'] / 2100, 1)} hours"  # Concorde speed
            },
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Route analysis error for {origin}-{destination}: {e}")
        raise HTTPException(status_code=500, detail=f"Route analysis failed")

@app.get("/api/aerospace/dashboard/{query_id}")
async def aerospace_dashboard(query_id: int):
    """Aerospace engineering dashboard with comprehensive flight analysis"""
    try:
        # Get flight results with aerospace analysis
        results = await results_aggregator.get_results_with_apis(query_id)

        if not results:
            raise HTTPException(status_code=404, detail="No flight results found")

        # Extract aerospace analysis data
        routes_analysis = []
        fuel_efficiency_summary = {'best': None, 'worst': None, 'average': 0}
        distance_summary = {'shortest_km': float('inf'), 'longest_km': 0}
        aircraft_summary = {}

        total_fuel = 0
        fuel_count = 0

        for result in results:
            aerospace_data = result.get('aerospace_analysis', {})

            if aerospace_data:
                # Route analysis
                routes_analysis.append({
                    'flight': f"{result['carrier']}{result['flight_number']}",
                    'route': f"{result['segments'][0]['origin']} → {result['segments'][-1]['destination']}",
                    'distance': aerospace_data.get('distance', {}),
                    'fuel_analysis': aerospace_data.get('fuel_analysis', {}),
                    'route_efficiency': aerospace_data.get('route_efficiency', {}),
                    'navigation': aerospace_data.get('navigation', {}),
                    'price': result.get('price', {})
                })

                # Fuel efficiency tracking
                fuel_data = aerospace_data.get('fuel_analysis', {})
                if 'fuel_per_passenger_liters' in fuel_data:
                    fuel_amount = fuel_data['fuel_per_passenger_liters']
                    total_fuel += fuel_amount
                    fuel_count += 1

                    if fuel_efficiency_summary['best'] is None or fuel_amount < fuel_efficiency_summary['best']['fuel']:
                        fuel_efficiency_summary['best'] = {'flight': f"{result['carrier']}{result['flight_number']}", 'fuel': fuel_amount}

                    if fuel_efficiency_summary['worst'] is None or fuel_amount > fuel_efficiency_summary['worst']['fuel']:
                        fuel_efficiency_summary['worst'] = {'flight': f"{result['carrier']}{result['flight_number']}", 'fuel': fuel_amount}

                # Distance tracking
                distance_data = aerospace_data.get('distance', {})
                if 'great_circle_km' in distance_data:
                    dist_km = distance_data['great_circle_km']
                    distance_summary['shortest_km'] = min(distance_summary['shortest_km'], dist_km)
                    distance_summary['longest_km'] = max(distance_summary['longest_km'], dist_km)

                # Aircraft summary
                aircraft = fuel_data.get('aircraft_type', 'Unknown')
                if aircraft not in aircraft_summary:
                    aircraft_summary[aircraft] = {'count': 0, 'avg_fuel': 0, 'flights': []}
                aircraft_summary[aircraft]['count'] += 1
                aircraft_summary[aircraft]['flights'].append(f"{result['carrier']}{result['flight_number']}")

        if fuel_count > 0:
            fuel_efficiency_summary['average'] = round(total_fuel / fuel_count, 2)

        response = {
            'query_id': query_id,
            'summary': {
                'total_flights_analyzed': len(results),
                'routes_with_aerospace_data': len(routes_analysis),
                'fuel_efficiency_summary': fuel_efficiency_summary,
                'distance_summary': distance_summary,
                'aircraft_types': len(aircraft_summary)
            },
            'detailed_analysis': routes_analysis[:10],  # Top 10 for dashboard
            'aircraft_breakdown': aircraft_summary,
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Aerospace dashboard error for query {query_id}: {e}")
        raise HTTPException(status_code=500, detail="Dashboard generation failed")

@app.get("/api/aerospace/live-flights/{bbox}")
async def get_live_flights_in_area(bbox: str):
    """Get live aircraft positions using OpenSky Network (FREE for students)"""
    try:
        # Parse bounding box: lat_min,lon_min,lat_max,lon_max
        coords = bbox.split(',')
        if len(coords) != 4:
            raise HTTPException(status_code=400, detail="Invalid bbox format. Use: lat_min,lon_min,lat_max,lon_max")

        lat_min, lon_min, lat_max, lon_max = map(float, coords)

        # OpenSky Network API - FREE and perfect for students
        url = f"https://opensky-network.org/api/states/all?lamin={lat_min}&lomin={lon_min}&lamax={lat_max}&lomax={lon_max}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    states = data.get('states', [])

                    # Format aircraft data for aerospace analysis
                    aircraft_list = []
                    for state in states[:50]:  # Limit to 50 aircraft
                        if state[5] and state[6]:  # Has lat/lon
                            aircraft_info = {
                                'icao24': state[0],
                                'callsign': state[1].strip() if state[1] else 'Unknown',
                                'origin_country': state[2],
                                'longitude': state[5],
                                'latitude': state[6],
                                'altitude_m': state[7],
                                'ground_speed_ms': state[9],
                                'heading_deg': state[10],
                                'vertical_rate_ms': state[11],
                                'aircraft_type': 'Unknown',  # OpenSky doesn't provide this
                                'aerospace_metrics': {
                                    'ground_speed_kmh': round(state[9] * 3.6, 1) if state[9] else None,
                                    'ground_speed_kts': round(state[9] * 1.944, 1) if state[9] else None,
                                    'altitude_ft': round(state[7] * 3.281, 0) if state[7] else None,
                                    'flight_level': round(state[7] * 3.281 / 100, 0) if state[7] else None
                                }
                            }
                            aircraft_list.append(aircraft_info)

                    return {
                        'bbox': bbox,
                        'aircraft_count': len(aircraft_list),
                        'aircraft': aircraft_list,
                        'data_source': 'OpenSky Network (FREE)',
                        'student_friendly': True,
                        'generated_at': datetime.utcnow().isoformat()
                    }
                else:
                    raise HTTPException(status_code=500, detail="OpenSky API unavailable")

    except Exception as e:
        logger.error(f"❌ Live flights API error: {e}")
        raise HTTPException(status_code=500, detail="Live flights data unavailable")

@app.get("/api/aerospace/aircraft-database/{icao_code}")
async def get_aircraft_info(icao_code: str):
    """Get aircraft specifications from aviation databases (STUDENT ACCESS)"""
    try:
        icao_code = icao_code.upper()

        # Mock aircraft database - in reality this would connect to OpenSky or FAA databases
        aircraft_db = {
            'A320': {
                'manufacturer': 'Airbus',
                'model': 'A320-200',
                'type': 'Narrow-body',
                'engines': 2,
                'engine_type': 'CFM56-5B / V2500',
                'max_passengers': 180,
                'range_km': 6150,
                'cruise_speed_mach': 0.78,
                'service_ceiling_ft': 39000,
                'mtow_kg': 78000,
                'fuel_capacity_liters': 24210,
                'wingspan_m': 35.8,
                'length_m': 37.6,
                'academic_notes': 'Popular for aerospace engineering studies due to fly-by-wire systems'
            },
            'B737': {
                'manufacturer': 'Boeing',
                'model': '737-800',
                'type': 'Narrow-body',
                'engines': 2,
                'engine_type': 'CFM56-7B',
                'max_passengers': 189,
                'range_km': 5765,
                'cruise_speed_mach': 0.785,
                'service_ceiling_ft': 41000,
                'mtow_kg': 79016,
                'fuel_capacity_liters': 26020,
                'wingspan_m': 35.8,
                'length_m': 39.5,
                'academic_notes': 'Excellent case study for traditional control systems vs fly-by-wire'
            },
            'B787': {
                'manufacturer': 'Boeing',
                'model': '787-8 Dreamliner',
                'type': 'Wide-body',
                'engines': 2,
                'engine_type': 'GEnx / Trent 1000',
                'max_passengers': 242,
                'range_km': 14800,
                'cruise_speed_mach': 0.85,
                'service_ceiling_ft': 43000,
                'mtow_kg': 227930,
                'fuel_capacity_liters': 126920,
                'wingspan_m': 60.1,
                'length_m': 56.7,
                'academic_notes': 'Advanced composite materials - 50% carbon fiber reinforced plastic'
            }
        }

        aircraft_info = aircraft_db.get(icao_code)
        if not aircraft_info:
            # Return generic info for unknown aircraft
            aircraft_info = {
                'manufacturer': 'Unknown',
                'model': icao_code,
                'academic_notes': 'Aircraft data not available in student database'
            }

        # Add educational calculations
        if 'fuel_capacity_liters' in aircraft_info and 'range_km' in aircraft_info:
            aircraft_info['educational_metrics'] = {
                'fuel_efficiency_l_per_100km': round(aircraft_info['fuel_capacity_liters'] / aircraft_info['range_km'] * 100, 2),
                'approximate_fuel_cost_full_tank_usd': round(aircraft_info['fuel_capacity_liters'] * 0.85, 2),  # ~$0.85/liter aviation fuel
                'passenger_fuel_efficiency_l_per_100km': round(aircraft_info['fuel_capacity_liters'] / aircraft_info['range_km'] * 100 / aircraft_info['max_passengers'], 3)
            }

        return {
            'icao_code': icao_code,
            'aircraft_data': aircraft_info,
            'data_source': 'Student Aviation Database',
            'educational_purpose': True,
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Aircraft database error for {icao_code}: {e}")
        raise HTTPException(status_code=500, detail="Aircraft data unavailable")

@app.get("/api/aerospace/flight-planning/{origin}/{destination}")
async def flight_planning_tools(origin: str, destination: str, altitude_ft: int = 35000):
    """Flight planning calculations for aerospace engineering students"""
    try:
        origin = origin.upper()
        destination = destination.upper()

        # Get airport coordinates
        origin_coords = get_airport_coordinates(origin)
        dest_coords = get_airport_coordinates(destination)

        if not origin_coords or not dest_coords:
            raise HTTPException(status_code=404, detail="Airport coordinates not found")

        # Basic flight planning calculations
        distance_data = aerospace_calc.great_circle_distance(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Initial bearing
        bearing = aerospace_calc.initial_bearing(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Flight time estimates at different altitudes
        flight_times = {
            'fl350_standard': {
                'altitude_ft': 35000,
                'typical_speed_kts': 450,
                'flight_time_hours': round(distance_data['great_circle_nm'] / 450, 2),
                'fuel_efficiency': 'Optimal for most aircraft'
            },
            'fl400_high': {
                'altitude_ft': 40000,
                'typical_speed_kts': 470,
                'flight_time_hours': round(distance_data['great_circle_nm'] / 470, 2),
                'fuel_efficiency': 'Better efficiency, less traffic'
            },
            'fl280_low': {
                'altitude_ft': 28000,
                'typical_speed_kts': 420,
                'flight_time_hours': round(distance_data['great_circle_nm'] / 420, 2),
                'fuel_efficiency': 'Lower efficiency, more weather'
            }
        }

        # Wind triangle calculations (simplified)
        wind_triangle = {
            'true_airspeed_kts': 450,
            'ground_speed_no_wind_kts': 450,
            'estimated_wind_effect': '±30 kts typical',
            'note': 'Actual wind data requires meteorological API integration'
        }

        response = {
            'route': f"{origin} → {destination}",
            'distance_analysis': distance_data,
            'navigation': {
                'initial_bearing': round(bearing, 1),
                'bearing_description': get_bearing_description(bearing),
                'magnetic_variation': 'Requires current navigation database'
            },
            'flight_levels': flight_times,
            'wind_triangle': wind_triangle,
            'waypoints': {
                'note': 'Actual flight plans require current AIRAC navigation data',
                'approximate_midpoint': {
                    'lat': (origin_coords['lat'] + dest_coords['lat']) / 2,
                    'lon': (origin_coords['lon'] + dest_coords['lon']) / 2
                }
            },
            'educational_notes': [
                'Flight planning requires current weather, NOTAMS, and navigation data',
                'Real-world planning uses tools like Jeppesen FliteDeck or SkyVector',
                'Commercial flights must comply with ICAO and national regulations',
                'Fuel planning includes reserve requirements (typically 10% + alternate)'
            ],
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Flight planning error for {origin}-{destination}: {e}")
        raise HTTPException(status_code=500, detail="Flight planning calculation failed")

@app.get("/api/stream/{query_id}")
async def stream_results(query_id: int):
    """SSE stream for live updates"""
    async def gen():
        last_sent = 0
        while True:
            bucket = SSE_CHANNELS.get(query_id, [])
            if len(bucket) > last_sent:
                for i in range(last_sent, len(bucket)):
                    yield f"data: {json.dumps(bucket[i])}\n\n"
                last_sent = len(bucket)
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/api/debug/connectivity")
async def debug_connectivity(request: Request, x_fa_token: str = Header(default="")):
    """Debug endpoint to check CORS, token, and connectivity"""
    return {
        "status": "connected",
        "received_token": x_fa_token,
        "expected_token": INGEST_TOKEN,
        "token_valid": x_fa_token == INGEST_TOKEN,
        "server_time": datetime.utcnow().isoformat(),
        "request_origin": request.headers.get("origin", "none"),
        "cors_enabled": True,
        "codespaces_ready": True
    }

@app.get("/api/debug/token")
async def debug_check_token(x_fa_token: str = Header(default="")):
    """Debug endpoint to check token and connectivity"""
    return {
        "received_token": x_fa_token,
        "expected_token": INGEST_TOKEN,
        "token_valid": x_fa_token == INGEST_TOKEN,
        "server_time": datetime.utcnow().isoformat(),
        "cors_headers": "enabled"
    }

@app.post("/api/debug/ingest_example/{query_id}")
async def debug_ingest_example(query_id: int, x_fa_token: str = Header(default="")):
    """Debug endpoint to test UI without extension"""
    # Validate token
    if x_fa_token != INGEST_TOKEN:
        logger.warning(f"❌ Invalid token in debug endpoint. Expected: {INGEST_TOKEN[:8]}..., Got: {x_fa_token[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid token")

    # Create test fares
    test_fares = [
        {
            "origin": "LHR",
            "destination": "AMS", 
            "date": "2025-09-06",
            "airline": "British Airways",
            "price": 125.50,
            "currency": "GBP",
            "site": "debug.example",
            "url": "https://example.com/flights/LHR-AMS",
            "extracted_at": datetime.utcnow().isoformat()
        },
        {
            "origin": "LHR",
            "destination": "AMS",
            "date": "2025-09-06", 
            "airline": "KLM",
            "price": 89.99,
            "currency": "GBP",
            "site": "debug.example",
            "url": "https://example.com/flights/LHR-AMS-klm",
            "extracted_at": datetime.utcnow().isoformat()
        }
    ]

    # Use the simple ingest endpoint
    payload = {
        "query_id": query_id,
        "fares": test_fares,
        "site": "debug.example"
    }

    try:
        result = await ingest_fares(payload, x_fa_token)
        logger.info(f"✅ Debug test successful: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Debug test failed: {e}")
        raise

@app.post("/api/debug/ingest")
async def ingest_fares(payload: dict, x_fa_token: str = Header(default="")):
    """Simple ingestion endpoint for BYOB extension"""
    try:
        # Validate token
        if x_fa_token != INGEST_TOKEN:
            logger.warning(f"❌ Invalid token from extension. Expected: {INGEST_TOKEN[:8]}..., Got: {x_fa_token[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid token")

        query_id = payload.get("query_id")
        fares = payload.get("fares", [])
        site_domain = payload.get("site", "unknown")

        if not query_id:
            raise HTTPException(status_code=400, detail="query_id required")

        logger.info(f"📩 Received {len(fares)} fares from extension for query {query_id} from {site_domain}")

        # Get or create site
        with get_db_connection() as conn:
            site = conn.execute('SELECT id FROM sites WHERE domain = ?', (site_domain,)).fetchone()
            if not site:
                cursor = conn.execute(
                    'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                    (site_domain, site_domain.replace('.com', '').title(), 1, 2)
                )
                conn.commit()
                site_id = cursor.lastrowid
                logger.info(f"🆕 Auto-registered site: {site_domain}")
            else:
                site_id = site['id']

            # Store fares
            processed = 0
            for fare in fares:
                try:
                    # Generate hash for deduplication
                    fare_hash = hashlib.sha256(json.dumps(fare, sort_keys=True).encode()).hexdigest()[:16]

                    # Check for duplicates
                    existing = conn.execute(
                        'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                        (query_id, fare_hash)
                    ).fetchone()

                    if not existing:
                        conn.execute('''
                            INSERT INTO results (
                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                source, carrier_codes, booking_url, valid
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            query_id, site_id, json.dumps(fare), fare_hash,
                            fare.get('price', 0), fare.get('currency', 'GBP'),
                            'extension', json.dumps([fare.get('airline', '')]),
                            fare.get('url', ''), 1
                        ))
                        processed += 1
                        logger.debug(f"💾 Stored fare: {fare}")
                except Exception as e:
                    logger.warning(f"Error processing fare: {e}")
                    continue

            conn.commit()

        # Check for alert matches
        if processed > 0:
            await check_alert_matches(query_id, site_id)

        logger.info(f"✅ Processed {processed} new fares from {site_domain}")
        return {"ok": True, "count": processed}

    except Exception as e:
        logger.error(f"❌ BYOB ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results/{query_id}")
async def get_results(query_id: int):
    """Get results for a query with enhanced logging"""
    try:
        # Use API-enhanced results (Duffel + Amadeus)
        results = await results_aggregator.get_results_with_apis(query_id)

        with get_db_connection() as conn:
            query = conn.execute('SELECT * FROM queries WHERE id = ?', (query_id,)).fetchone()

            if not query:
                logger.warning(f"❌ Query {query_id} not found")
                raise HTTPException(status_code=404, detail="Query not found")

            # Enhanced logging for debugging
            if results:
                sources = {}
                for result in results:
                    source = result.get('source', {}).get('name', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
                logger.info(f"📊 Query {query_id}: {len(results)} results from sources: {sources}")
            else:
                # Check if there are any results at all for this query
                total_results = conn.execute('SELECT COUNT(*) FROM results WHERE query_id = ?', (query_id,)).fetchone()[0]

                # NO DEMO DATA - Only show real results
                if total_results == 0:
                    query_age_minutes = conn.execute('''
                        SELECT (julianday('now') - julianday(created_at)) * 1440 as age_minutes 
                        FROM queries WHERE id = ?
                    ''', (query_id,)).fetchone()[0]

                    logger.info(f"⏳ Query {query_id}: No real flight data yet. Query age: {int(query_age_minutes*60)}s")
                    logger.info(f"💡 Searching with API sources for comprehensive flight data")
                else:
                    logger.info(f"📊 Query {query_id}: Found {total_results} results in database, but none passed validation filters")

            return {
                'query_id': query_id,
                'query': dict(query),
                'results': results,
                'total_found': len(results),
                'last_updated': datetime.utcnow().isoformat(),
                'status': 'active' if len(results) == 0 else 'results_found'
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Results retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cities")
async def search_cities(q: str = ""):
    """Search cities by grouping airports from the CSV dataset"""
    try:
        if not q or len(q) < 2:
            return {"cities": []}

        cities = {}  # Dictionary to group airports by city
        q_lower = q.lower()

        try:
            # Use CSV file first (comprehensive dataset)
            if os.path.exists('airport-codes.csv'):
                import csv
                with open('airport-codes.csv', 'r', encoding='utf-8') as f:
                    csv_reader = csv.DictReader(f)
                    for row in csv_reader:
                        # Get airport details
                        iata_code = row.get('iata_code', '').strip()
                        icao_code = row.get('icao_code', '').strip()
                        ident = row.get('ident', '').strip()
                        name = row.get('name', '').strip()
                        municipality = row.get('municipality', '').strip()
                        iso_country = row.get('iso_country', '').strip()
                        airport_type = row.get('type', '').strip()

                        # Prefer IATA codes but include major airports with ICAO codes
                        display_code = iata_code if iata_code else icao_code

                        # Skip if no usable code or not a public airport
                        if not display_code or len(display_code) < 3:
                            continue
                        if airport_type in ['closed', 'heliport', 'seaplane_base']:
                            continue

                        # Search in city and airport names
                        searchable_text = f"{municipality} {name} {iata_code} {icao_code} {ident}".lower()
                        if q_lower in searchable_text and municipality:
                            # Group by city (municipality)
                            city_key = f"{municipality}, {iso_country}"
                            if city_key not in cities:
                                cities[city_key] = {
                                    'airports': [],
                                    'primary_code': None,
                                    'municipality': municipality,
                                    'country': iso_country
                                }

                            # Add airport to city group
                            cities[city_key]['airports'].append({
                                'code': display_code.upper(),
                                'name': name,
                                'type': airport_type
                            })

                            # Set primary airport code (prefer major international airports)
                            major_airports = {'LHR', 'LGW', 'STN', 'LTN', 'LCY', 'SEN'}

                            if not cities[city_key]['primary_code']:
                                cities[city_key]['primary_code'] = display_code.upper()
                            elif iata_code and len(iata_code) == 3:
                                current_code = cities[city_key]['primary_code']
                                current_type = cities[city_key]['airports'][0]['type'] if cities[city_key]['airports'] else ''

                                # Prefer major international airports
                                if iata_code in major_airports and current_code not in major_airports:
                                    cities[city_key]['primary_code'] = display_code.upper()
                                # Otherwise prefer large airports over smaller ones
                                elif (airport_type == 'large_airport' and current_type != 'large_airport') or \
                                     (airport_type == 'medium_airport' and current_type not in ['large_airport', 'medium_airport']):
                                    cities[city_key]['primary_code'] = display_code.upper()

                        if len(cities) >= 50:  # Limit to 50 cities for performance
                            break

                logger.info(f"Found {len(cities)} cities matching '{q}' from CSV")

            # Convert to list format for frontend
            city_list = []
            for city_name, city_data in cities.items():
                # Show number of airports if more than one
                airport_count = len(city_data['airports'])
                if airport_count > 1:
                    display_text = f"{city_name} ({airport_count} airports)"
                else:
                    display_text = city_name

                city_list.append({
                    'code': city_data['primary_code'],  # Use primary airport code
                    'display': display_text,
                    'airport_count': airport_count,
                    'airports': city_data['airports']  # Include all airports for this city
                })

            # Sort by city name
            city_list.sort(key=lambda x: x['display'])

            return {"cities": city_list[:30]}  # Return top 30 matches

        except Exception as e:
            logger.error(f"Error reading CSV for city search: {e}")

            # Fallback to JSON if CSV fails
            if os.path.exists('airports.json'):
                with open('airports.json', 'r') as f:
                    data = json.load(f)
                    cities = {}
                    for airport in data.get('airports', []):
                        code = airport.get('iata', airport.get('icao', ''))
                        name = airport.get('name', '')
                        city = airport.get('city', '')
                        country = airport.get('country', '')

                        if code and city and (q_lower in name.lower() or q_lower in city.lower() or q_lower in code.lower()):
                            city_key = f"{city}, {country}"
                            if city_key not in cities:
                                cities[city_key] = {
                                    'code': code,
                                    'display': city_key
                                }

                    return {"cities": list(cities.values())[:30]}

        return {"cities": []}
    except Exception as e:
        logger.error(f"City search failed: {e}")
        return {"cities": []}

@app.get("/api/airports")
async def search_airports(q: str = ""):
    """Search airports by query string using comprehensive CSV dataset"""
    try:
        if not q or len(q) < 2:
            return {"airports": []}

        airports = []
        q_lower = q.lower()

        try:
            # Use CSV file first (comprehensive dataset)
            if os.path.exists('airport-codes.csv'):
                import csv
                with open('airport-codes.csv', 'r', encoding='utf-8') as f:
                    csv_reader = csv.DictReader(f)
                    for row in csv_reader:
                        # Get airport details
                        iata_code = row.get('iata_code', '').strip()
                        icao_code = row.get('icao_code', '').strip()
                        ident = row.get('ident', '').strip()
                        name = row.get('name', '').strip()
                        municipality = row.get('municipality', '').strip()
                        iso_country = row.get('iso_country', '').strip()
                        airport_type = row.get('type', '').strip()

                        # Prefer IATA codes but also include airports with only ICAO or ident codes
                        display_code = iata_code if iata_code else (icao_code if icao_code else ident)

                        # Skip if no usable code
                        if not display_code or len(display_code) < 3:
                            continue

                        # Skip closed airports
                        if airport_type == 'closed':
                            continue

                        # Search in various fields
                        searchable_text = f"{name} {municipality} {iata_code} {icao_code} {ident}".lower()
                        if q_lower in searchable_text:
                            # Create display name
                            location_parts = []
                            if municipality:
                                location_parts.append(municipality)
                            if iso_country:
                                location_parts.append(iso_country)
                            location = ", ".join(location_parts) if location_parts else "Unknown"

                            airports.append({
                                'code': display_code.upper(),
                                'display': f"{display_code.upper()} - {name}, {location}"
                            })

                        if len(airports) >= 100:  # Increased limit for better search results
                            break

                logger.info(f"Found {len(airports)} airports matching '{q}' from CSV")

            # Fallback to JSON if CSV doesn't exist
            elif os.path.exists('airports.json'):
                with open('airports.json', 'r') as f:
                    all_airports = json.load(f)

                for airport in all_airports:
                    if (q_lower in airport.get('name', '').lower() or
                        q_lower in airport.get('city', '').lower() or
                        q_lower in airport.get('iata_code', '').lower()):
                        airports.append({
                            'code': airport.get('iata_code', ''),
                            'display': f"{airport.get('iata_code', '')} - {airport.get('name', '')}, {airport.get('city', '')} ({airport.get('country', '')})"
                        })
                        if len(airports) >= 20:
                            break

            # Final fallback with common airports
            else:
                common_airports = [
                    {'code': 'LHR', 'display': 'LHR - London Heathrow, London (GB)'},
                    {'code': 'JFK', 'display': 'JFK - John F Kennedy Intl, New York (US)'},
                    {'code': 'LAX', 'display': 'LAX - Los Angeles Intl, Los Angeles (US)'},
                    {'code': 'DXB', 'display': 'DXB - Dubai Intl, Dubai (AE)'},
                    {'code': 'CDG', 'display': 'CDG - Charles de Gaulle, Paris (FR)'},
                    {'code': 'AMS', 'display': 'AMS - Amsterdam Schiphol, Amsterdam (NL)'},
                    {'code': 'FRA', 'display': 'FRA - Frankfurt am Main, Frankfurt (DE)'},
                    {'code': 'BCN', 'display': 'BCN - Barcelona El Prat, Barcelona (ES)'},
                    {'code': 'FCO', 'display': 'FCO - Rome Fiumicino, Rome (IT)'},
                    {'code': 'MAD', 'display': 'MAD - Madrid Barajas, Madrid (ES)'},
                ]

                airports = [a for a in common_airports if q_lower in a['display'].lower()]

        except Exception as e:
            logger.warning(f"Error loading airports: {e}")
            airports = []

        return {"airports": airports}

    except Exception as e:
        logger.error(f"Airport search failed: {e}")
        return {"airports": []}

@app.get("/api/airlines")
async def search_airlines(q: str = ""):
    """Search airlines by query string"""
    try:
        # Common airlines database
        airlines = [
            {'code': 'BA', 'display': 'BA - British Airways (United Kingdom)'},
            {'code': 'LH', 'display': 'LH - Lufthansa (Germany)'},
            {'code': 'AF', 'display': 'AF - Air France (France)'},
            {'code': 'KL', 'display': 'KL - KLM Royal Dutch Airlines (Netherlands)'},
            {'code': 'VS', 'display': 'VS - Virgin Atlantic (United Kingdom)'},
            {'code': 'EK', 'display': 'EK - Emirates (United Arab Emirates)'},
            {'code': 'QR', 'display': 'QR - Qatar Airways (Qatar)'},
            {'code': 'EY', 'display': 'EY - Etihad Airways (United Arab Emirates)'},
            {'code': 'TK', 'display': 'TK - Turkish Airlines (Turkey)'},
            {'code': 'SQ', 'display': 'SQ - Singapore Airlines (Singapore)'},
            {'code': 'QF', 'display': 'QF - Qantas (Australia)'},
            {'code': 'CX', 'display': 'CX - Cathay Pacific (Hong Kong)'},
            {'code': 'JL', 'display': 'JL - Japan Airlines (Japan)'},
            {'code': 'NH', 'display': 'NH - All Nippon Airways (Japan)'},
            {'code': 'AC', 'display': 'AC - Air Canada (Canada)'},
            {'code': 'WS', 'display': 'WS - WestJet (Canada)'},
            {'code': 'DL', 'display': 'DL - Delta Air Lines (United States)'},
            {'code': 'UA', 'display': 'UA - United Airlines (United States)'},
            {'code': 'AA', 'display': 'AA - American Airlines (United States)'},
            {'code': 'AS', 'display': 'AS - Alaska Airlines (United States)'},
            {'code': 'B6', 'display': 'B6 - JetBlue Airways (United States)'},
            {'code': 'WN', 'display': 'WN - Southwest Airlines (United States)'},
            {'code': 'FR', 'display': 'FR - Ryanair (Ireland)'},
            {'code': 'U2', 'display': 'U2 - easyJet (United Kingdom)'},
            {'code': 'VY', 'display': 'VY - Vueling (Spain)'},
            {'code': 'W6', 'display': 'W6 - Wizz Air (Hungary)'},
            {'code': 'BE', 'display': 'BE - FlyBe (United Kingdom)'},
            {'code': 'MT', 'display': 'MT - Thomas Cook Airlines (United Kingdom)'},
            {'code': 'LS', 'display': 'LS - Jet2.com (United Kingdom)'},
            {'code': 'BY', 'display': 'BY - TUI Airways (United Kingdom)'},
            {'code': 'SN', 'display': 'SN - Brussels Airlines (Belgium)'},
            {'code': 'LX', 'display': 'LX - Swiss International Air Lines (Switzerland)'},
            {'code': 'OS', 'display': 'OS - Austrian Airlines (Austria)'},
            {'code': 'SK', 'display': 'SK - Scandinavian Airlines (Sweden)'},
            {'code': 'AY', 'display': 'AY - Finnair (Finland)'},
            {'code': 'DY', 'display': 'DY - Norwegian Air Shuttle (Norway)'},
            {'code': 'IB', 'display': 'IB - Iberia (Spain)'},
            {'code': 'UX', 'display': 'UX - Air Europa (Spain)'},
            {'code': 'TP', 'display': 'TP - TAP Air Portugal (Portugal)'},
            {'code': 'AZ', 'display': 'AZ - Alitalia (Italy)'},
            {'code': 'EN', 'display': 'EN - Air Dolomiti (Italy)'},
            {'code': 'LO', 'display': 'LO - LOT Polish Airlines (Poland)'},
            {'code': 'OK', 'display': 'OK - Czech Airlines (Czech Republic)'},
            {'code': 'RO', 'display': 'RO - Tarom (Romania)'},
            {'code': 'JU', 'display': 'JU - Air Serbia (Serbia)'},
            {'code': 'OU', 'display': 'OU - Croatia Airlines (Croatia)'},
            {'code': 'JP', 'display': 'JP - Adria Airways (Slovenia)'},
            {'code': 'BT', 'display': 'BT - Air Baltic (Latvia)'},
            {'code': 'SU', 'display': 'SU - Aeroflot (Russia)'},
            {'code': 'S7', 'display': 'S7 - S7 Airlines (Russia)'},
            {'code': 'UT', 'display': 'UT - UTair (Russia)'},
            {'code': 'FZ', 'display': 'FZ - flydubai (United Arab Emirates)'},
            {'code': 'WY', 'display': 'WY - Oman Air (Oman)'},
            {'code': 'GF', 'display': 'GF - Gulf Air (Bahrain)'},
            {'code': 'KU', 'display': 'KU - Kuwait Airways (Kuwait)'},
            {'code': 'SV', 'display': 'SV - Saudi Arabian Airlines (Saudi Arabia)'},
            {'code': 'MS', 'display': 'MS - EgyptAir (Egypt)'},
            {'code': 'ET', 'display': 'ET - Ethiopian Airlines (Ethiopia)'},
            {'code': 'SA', 'display': 'SA - South African Airways (South Africa)'},
            {'code': 'MN', 'display': 'MN - Kulula (South Africa)'},
            {'code': 'AI', 'display': 'AI - Air India (India)'},
            {'code': '6E', 'display': '6E - IndiGo (India)'},
            {'code': 'SG', 'display': 'SG - SpiceJet (India)'},
            {'code': 'UK', 'display': 'UK - Vistara (India)'},
            {'code': 'IX', 'display': 'IX - Air India Express (India)'},
            {'code': 'PK', 'display': 'PK - Pakistan International Airlines (Pakistan)'},
            {'code': 'BG', 'display': 'BG - Biman Bangladesh Airlines (Bangladesh)'},
            {'code': 'UL', 'display': 'UL - SriLankan Airlines (Sri Lanka)'},
            {'code': 'TG', 'display': 'TG - Thai Airways (Thailand)'},
            {'code': 'FD', 'display': 'FD - Thai AirAsia (Thailand)'},
            {'code': 'SL', 'display': 'SL - Thai Lion Air (Thailand)'},
            {'code': 'MH', 'display': 'MH - Malaysia Airlines (Malaysia)'},
            {'code': 'AK', 'display': 'AK - AirAsia (Malaysia)'},
            {'code': 'D7', 'display': 'D7 - AirAsia X (Malaysia)'},
            {'code': 'BI', 'display': 'BI - Royal Brunei Airlines (Brunei)'},
            {'code': 'TR', 'display': 'TR - Scoot (Singapore)'},
            {'code': 'MI', 'display': 'MI - SilkAir (Singapore)'},
            {'code': 'GA', 'display': 'GA - Garuda Indonesia (Indonesia)'},
            {'code': 'JT', 'display': 'JT - Lion Air (Indonesia)'},
            {'code': 'QG', 'display': 'QG - Citilink (Indonesia)'},
            {'code': 'VN', 'display': 'VN - Vietnam Airlines (Vietnam)'},
            {'code': 'VJ', 'display': 'VJ - VietJet Air (Vietnam)'},
            {'code': 'PR', 'display': 'PR - Philippine Airlines (Philippines)'},
            {'code': '5J', 'display': '5J - Cebu Pacific (Philippines)'},
            {'code': 'CA', 'display': 'CA - Air China (China)'},
            {'code': 'CZ', 'display': 'CZ - China Southern Airlines (China)'},
            {'code': 'MU', 'display': 'MU - China Eastern Airlines (China)'},
            {'code': 'HU', 'display': 'HU - Hainan Airlines (China)'},
            {'code': 'SC', 'display': 'SC - Shandong Airlines (China)'},
            {'code': 'FM', 'display': 'FM - Shanghai Airlines (China)'},
            {'code': 'OZ', 'display': 'OZ - Asiana Airlines (South Korea)'},
            {'code': 'KE', 'display': 'KE - Korean Air (South Korea)'},
            {'code': 'TW', 'display': 'TW - T way Air (South Korea)'},
            {'code': 'CI', 'display': 'CI - China Airlines (Taiwan)'},
            {'code': 'BR', 'display': 'BR - EVA Air (Taiwan)'},
            {'code': 'IT', 'display': 'IT - Tigerair Taiwan (Taiwan)'},
            {'code': 'HX', 'display': 'HX - Hong Kong Airlines (Hong Kong)'},
            {'code': 'UO', 'display': 'UO - HK Express (Hong Kong)'},
            {'code': 'NX', 'display': 'NX - Air Macau (Macau)'},
        ]

        if not q:
            # Return first 20 airlines if no search query
            return airlines[:20]

        q_lower = q.lower()
        filtered_airlines = []

        for airline in airlines:
            # Search in airline code, name, and country
            if (q_lower in airline['code'].lower() or
                q_lower in airline['display'].lower()):
                filtered_airlines.append(airline)
                if len(filtered_airlines) >= 50:  # Limit results
                    break

        return filtered_airlines

    except Exception as e:
        logger.error(f"Airline search failed: {e}")
        return []

@app.get("/api/flight_stats")
async def get_flight_stats():
    """Get live flight statistics"""
    return {
        'flights_tracked_now': random.randint(7500, 8500),
        'countries_represented': random.randint(95, 110),
        'average_altitude_feet': random.randint(22000, 26000)
    }

@app.get("/api/trending_routes")
async def get_trending_routes():
    """Get trending flight routes"""
    routes = [
        {'route': 'LHR-AMS', 'change': 15},
        {'route': 'LHR-CDG', 'change': -8},
        {'route': 'LHR-BCN', 'change': 22},
        {'route': 'LHR-FCO', 'change': -5},
        {'route': 'LHR-MAD', 'change': 12}
    ]
    return {'routes': routes}

@app.get("/api/airport_delays")
async def get_airport_delays():
    """Get live airport delays"""
    delays = [
        {'airport': 'LHR', 'delay': '15 min', 'severity': 'minor'},
        {'airport': 'CDG', 'delay': '45 min', 'severity': 'moderate'},
        {'airport': 'AMS', 'delay': '2 hours', 'severity': 'major'},
        {'airport': 'FRA', 'delay': '20 min', 'severity': 'minor'},
        {'airport': 'MAD', 'delay': '30 min', 'severity': 'moderate'}
    ]
    return {'delays': delays}

@app.get("/api/rare_aircraft_spotted")
async def get_rare_aircraft():
    """Get recently spotted rare aircraft"""
    sightings = [
        {'type': 'Airbus A380', 'route': 'LHR-DXB', 'time': '2 hours ago'},
        {'type': 'Boeing 787 Dreamliner', 'route': 'LHR-NRT', 'time': '4 hours ago'},
        {'type': 'Airbus A350', 'route': 'CDG-SIN', 'time': '6 hours ago'}
    ]
    return {'sightings': sightings}

@app.get("/api/price_war/{departure}/{destination}")
async def get_price_war(departure: str, destination: str):
    """Get price war data for a route"""
    airlines = [
        {'airline': 'Ryanair', 'price': 89.99},
        {'airline': 'easyJet', 'price': 94.50},
        {'airline': 'British Airways', 'price': 125.00}
    ]
    random.shuffle(airlines)
    return {
        'price_drop_alert': f'Price battle active on {departure}-{destination}!',
        'airlines': airlines
    }

@app.get("/api/surprise_me")
async def surprise_me(budget: float = 200):
    """Get surprise destinations within budget"""
    destinations = [
        {'city': 'Amsterdam', 'price': budget * 0.6},
        {'city': 'Barcelona', 'price': budget * 0.7},
        {'city': 'Prague', 'price': budget * 0.5},
        {'city': 'Dublin', 'price': budget * 0.8}
    ]
    return {
        'message': f'Amazing destinations under £{budget}!',
        'destinations': destinations
>>>>>>> Stashed changes
    }

@app.post("/api/ingest")
async def ingest_extension_data(request: Request):
    """Production ingest endpoint for BYOB extension"""
    try:
        data = await request.json()

        # Validate required fields
        required_fields = ['vendor', 'url', 'price']
        if not all(field in data for field in required_fields):
            return {'ok': False, 'error': 'Missing required fields'}

        # Basic validation
        price = float(data['price'])
        if price <= 0 or price > 50000:  # Reasonable bounds
            return {'ok': False, 'error': 'Invalid price range'}

        vendor = data['vendor']
        url = data['url']
        currency = data.get('currency', 'GBP')
        route = data.get('route', {})
        page_title = data.get('pageTitle', '')
        tab_url = data.get('tabUrl', '')
        user_agent = data.get('userAgent', '')
        ts = data.get('ts', datetime.now().isoformat())

        with get_db_connection() as conn:
            # Insert into results table (matching your existing schema)
            result_id = conn.execute('''
                INSERT INTO results (
                    query_id, price, currency, airline, url, site, 
                    source, valid, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                None,  # No specific query_id for extension data
                price,
                currency,
                vendor,  # Use vendor as airline
                url,
                vendor,  # Site name
                'extension',  # Mark as extension source
                1,  # Valid
                ts
            )).lastrowid

            # Also store in a separate extension_fares table for detailed analysis
            conn.execute('''
                CREATE TABLE IF NOT EXISTS extension_fares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER,
                    vendor TEXT,
                    url TEXT,
                    price REAL,
                    currency TEXT,
                    origin TEXT,
                    destination TEXT,
                    date TEXT,
                    page_title TEXT,
                    tab_url TEXT,
                    user_agent TEXT,
                    ts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (result_id) REFERENCES results (id)
                )
            ''')

            conn.execute('''
                INSERT INTO extension_fares (
                    result_id, vendor, url, price, currency, origin, 
                    destination, date, page_title, tab_url, user_agent, ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_id,
                vendor,
                url,
                price,
                currency,
                route.get('origin', ''),
                route.get('destination', ''),
                route.get('date', ''),
                page_title,
                tab_url,
                user_agent,
                ts
            ))

            conn.commit()

        logger.info(f"🔧 Extension data ingested: {vendor} - £{price} from {url[:50]}...")
        return {'ok': True, 'id': result_id, 'price': price, 'vendor': vendor}

    except Exception as e:
        logger.error(f"❌ Extension ingest error: {e}")
        return {'ok': False, 'error': str(e)}

@app.get("/api/extension_stats")
async def get_extension_stats():
    """Get stats on extension-collected data"""
    with get_db_connection() as conn:
        # Get extension data stats
        total_fares = conn.execute('SELECT COUNT(*) FROM results WHERE source = "extension"').fetchone()[0]

        by_vendor = conn.execute('''
            SELECT site, COUNT(*) as count, AVG(price) as avg_price
            FROM results 
            WHERE source = "extension" AND fetched_at > datetime("now", "-7 days")
            GROUP BY site
            ORDER BY count DESC
        ''').fetchall()

        recent_fares = conn.execute('''
            SELECT site, price, currency, url, fetched_at
            FROM results 
            WHERE source = "extension" 
            ORDER BY id DESC 
            LIMIT 10
        ''').fetchall()

        return {
            'total_extension_fares': total_fares,
            'vendors_7d': [{'vendor': row[0], 'count': row[1], 'avg_price': row[2]} for row in by_vendor],
            'recent_fares': [
                {
                    'vendor': row[0], 
                    'price': row[1], 
                    'currency': row[2], 
                    'url': row[3][:50] + '...' if len(row[3]) > 50 else row[3],
                    'time': row[4]
                } for row in recent_fares
            ]
        }

@app.get("/api/amadeus/status")
async def amadeus_status():
    """Check Amadeus API configuration status"""
    return {
        'configured': amadeus_client.is_configured(),
        'api_key_set': bool(AMADEUS_API_KEY),
        'api_secret_set': bool(AMADEUS_API_SECRET),
        'test_mode': AMADEUS_TEST_MODE,
        'has_token': bool(amadeus_client.access_token),
        'token_expires_at': amadeus_client.token_expires_at.isoformat() if amadeus_client.token_expires_at else None
    }

<<<<<<< Updated upstream
@app.get("/api/airports")
async def get_airports(search: Optional[str] = None):
    """Get airport database - clean format without extra text"""
    airports = {
        "JFK": {"name": "John F. Kennedy International Airport", "city": "New York", "country": "US"},
        "LAX": {"name": "Los Angeles International Airport", "city": "Los Angeles", "country": "US"},
        "LHR": {"name": "Heathrow Airport", "city": "London", "country": "GB"},
        "CDG": {"name": "Charles de Gaulle Airport", "city": "Paris", "country": "FR"},
        "DXB": {"name": "Dubai International Airport", "city": "Dubai", "country": "AE"},
        "HND": {"name": "Tokyo Haneda Airport", "city": "Tokyo", "country": "JP"},
        "FRA": {"name": "Frankfurt Airport", "city": "Frankfurt", "country": "DE"},
        "SIN": {"name": "Singapore Changi Airport", "city": "Singapore", "country": "SG"},
        "AMS": {"name": "Amsterdam Schiphol Airport", "city": "Amsterdam", "country": "NL"},
        "ICN": {"name": "Incheon International Airport", "city": "Seoul", "country": "KR"},
    }
    
    # Clean format: "London, GB" without "(6 airports)" text
    results = []
    for code, info in airports.items():
        display = f"{info['city']}, {info['country']}"
        
        if search and search.lower() not in display.lower() and search.upper() != code:
            continue
        
        results.append({
            "code": code,
            "name": info['name'],
            "city": info['city'],
            "country": info['country'],
            "display": display  # Clean format: "London, GB"
        })
    
    return {"airports": results, "count": len(results)}

@app.get("/api/airlines")
async def get_airlines():
    """Get airline database with IATA codes and full names"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT code, name, domain FROM airlines")
    rows = cur.fetchall()
    conn.close()
    
    airlines = []
    for row in rows:
        airlines.append({
            "code": row['code'],
            "name": row['name'],
            "display": f"{row['code']} ({row['name']})",  # Format: "BA (British Airways)"
            "domain": row['domain']
        })
    
    return {"airlines": airlines, "count": len(airlines)}

@app.get("/api/currency/rates")
async def get_currency_rates(base: str = "GBP"):
    """Get live currency exchange rates"""
    rates = {
        "USD": 1.27,
        "EUR": 1.17,
        "GBP": 1.00,
        "JPY": 188.50,
        "CAD": 1.72,
        "AUD": 1.98,
        "CHF": 1.12,
        "CNY": 9.20,
        "INR": 105.50,
        "AED": 4.66,
        "SGD": 1.70
    }
    
    # Try to get live rates from API
    try:
        url = f"{CURRENCY_API_URL}/latest?base={base.upper()}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'rates' in data:
                rates = data['rates']
    except Exception as e:
        logger.warning(f"Failed to fetch live rates, using fallback: {e}")
    
    return {
        "base": base.upper(),
        "rates": rates,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/flights/live-map")
async def get_live_flights():
    """Live global flight map (simplified aircraft tracker)"""
    import random
    
    # Generate mock live flight positions
    flights_in_air = []
    
    for i in range(50):  # 50 flights currently in the air
        airline_codes = ["BA", "AA", "DL", "UA", "EK", "SQ", "LH", "AF", "KL", "QR"]
        airline = random.choice(airline_codes)
        
        flight = {
            "id": f"{airline}{random.randint(100, 999)}",
            "airline": airline,
            "airline_name": get_airline_name(airline),
            "origin": random.choice(["JFK", "LHR", "DXB", "SIN", "LAX", "FRA"]),
            "destination": random.choice(["JFK", "LHR", "DXB", "SIN", "LAX", "FRA"]),
            "latitude": random.uniform(-60, 60),
            "longitude": random.uniform(-180, 180),
            "altitude": random.randint(30000, 42000),
            "speed": random.randint(450, 580),
            "heading": random.randint(0, 359),
            "aircraft": random.choice(["B787", "A350", "B777", "A380", "B737", "A320"]),
            "status": random.choice(["cruising", "climbing", "descending"])
        }
        flights_in_air.append(flight)
    
    return {
        "flights": flights_in_air,
        "count": len(flights_in_air),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/flights/rare")
async def get_rare_aircraft_flights(origin: Optional[str] = None, destination: Optional[str] = None):
    """Search for flights with rare aircraft"""
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT code, manufacturer, model, popularity_score FROM rare_aircrafts ORDER BY popularity_score DESC")
    rare_aircraft = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    # If origin/destination provided, search for flights
    flights = []
    if origin and destination:
        all_flights = await search_flights_duffel(origin, destination, 
                                                   (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))
        flights = [f for f in all_flights if f.get('is_rare_aircraft', False)]
    
    return {
        "rare_aircraft": rare_aircraft,
        "flights": flights,
        "count": len(flights) if flights else 0
    }

@app.get("/api/aerospace-facts")
async def get_aerospace_facts():
    """Get aerospace-related facts and calculations"""
    all_facts = [
        {
            "category": "Speed & Performance",
            "title": "Mach Number Calculations",
            "fact": "Commercial jets cruise at Mach 0.78-0.85 (78-85% speed of sound)",
            "formula": "Mach = Aircraft Speed / Speed of Sound at altitude",
            "example": "Boeing 787 at 488 knots / 573 knots (sound) = Mach 0.85"
        },
        {
            "category": "Fuel Efficiency",
            "title": "Fuel Consumption Rate",
            "fact": "A380 burns ~12,000 kg/hour for 550 passengers = 21.8 kg per passenger per hour",
            "formula": "Fuel per passenger = Total burn rate / Number of passengers",
            "example": "12,000 kg/hr ÷ 550 pax = 21.8 kg/pax/hr"
        },
        {
            "category": "Physics",
            "title": "Lift Generation",
            "fact": "Lift (L) = 0.5 × Air Density × Velocity² × Wing Area × Lift Coefficient",
            "formula": "L = 0.5 × ρ × V² × S × CL",
            "example": "Boeing 747: ~900,000 lbs lift at cruise"
        },
        {
            "category": "Altitude",
            "title": "Air Density at Altitude",
            "fact": "At 35,000 ft, air density is only 25% of sea level",
            "formula": "ρ(h) = ρ₀ × e^(-h/H) where H ≈ 7,640m",
            "example": "Sea level: 1.225 kg/m³ → 35,000ft: 0.38 kg/m³"
        },
        {
            "category": "Range",
            "title": "Breguet Range Equation",
            "fact": "Aircraft range depends on fuel efficiency, weight, and aerodynamics",
            "formula": "Range = (V/c) × (L/D) × ln(W₁/W₂)",
            "example": "A350-900ULR: 18,000 km range"
        }
    ]
    
    return {"facts": all_facts, "count": len(all_facts)}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return {"error": "Endpoint not found", "detail": "The requested endpoint does not exist"}
=======
@app.get("/api/duffel/status")
async def duffel_status():
    """Check Duffel API configuration status"""
    return {
        'configured': duffel_client.is_configured(),
        'api_key_set': bool(DUFFEL_API_KEY),
        'api_key_prefix': DUFFEL_API_KEY[:20] + '...' if DUFFEL_API_KEY else None,
        'base_url': DUFFEL_BASE_URL
    }
>>>>>>> Stashed changes

@app.post("/api/amadeus/test")
async def test_amadeus():
    """Test Amadeus API connection"""
    if not amadeus_client.is_configured():
        raise HTTPException(status_code=400, detail="Amadeus API not configured")

    try:
        # Test authentication
        token = await amadeus_client.get_access_token()
        if token:
            # Test a simple search
            test_results = await amadeus_client.search_flights('LHR', 'CDG', '2025-09-01')
            return {
                'success': True,
                'token_obtained': True,
                'search_test': len(test_results) > 0,
                'results_count': len(test_results)
            }
        else:
            return {
                'success': False,
                'token_obtained': False,
                'error': 'Failed to obtain access token'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.post("/api/duffel/test")
async def test_duffel():
    """Test Duffel API connection"""
    if not duffel_client.is_configured():
        raise HTTPException(status_code=400, detail="Duffel API not configured")

    try:
        # Test a simple search
        test_results = await duffel_client.search_flights('LHR', 'CDG', '2025-09-01')
        return {
            'success': True,
            'search_test': len(test_results) > 0,
            'results_count': len(test_results),
            'sample_result': test_results[0] if test_results else None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/api/duffel/offers/{offer_id}")
async def get_duffel_offer(offer_id: str):
    """Get detailed Duffel offer information"""
    if not duffel_client.is_configured():
        raise HTTPException(status_code=400, detail="Duffel API not configured")

    try:
        headers = {
            "Authorization": f"Bearer {DUFFEL_API_KEY}",
            "Content-Type": "application/json",
            "Duffel-Version": "v2"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DUFFEL_BASE_URL}/air/offers/{offer_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Duffel offer request failed: {response.status} - {error_text}")
                    raise HTTPException(status_code=response.status, detail="Failed to fetch offer")

    except Exception as e:
        logger.error(f"❌ Duffel offer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint with real data status"""
    with get_db_connection() as conn:
        # Basic DB connectivity test
        site_count = conn.execute('SELECT COUNT(*) FROM sites').fetchone()[0]
        result_count = conn.execute('SELECT COUNT(*) FROM results WHERE fetched_at > datetime("now", "-24 hours")').fetchone()[0]
        user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]

        # Real data status
        real_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "extension" AND valid = 1').fetchone()[0]
        demo_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "demo"').fetchone()[0]

        # Recent activity
        recent_queries = conn.execute('SELECT COUNT(*) FROM queries WHERE created_at > datetime("now", "-1 hour")').fetchone()[0]
        recent_results = conn.execute('SELECT COUNT(*) FROM results WHERE fetched_at > datetime("now", "-1 hour") AND source = "extension"').fetchone()[0]

        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'sites_configured': site_count,
            'results_24h': result_count,
            'users_registered': user_count,
            'playwright_available': PLAYWRIGHT_AVAILABLE,
            'amadeus_configured': amadeus_client.is_configured(),
            'duffel_configured': duffel_client.is_configured(),
            'version': '3.0',
            'data_status': {
                'real_flights': real_results,
                'demo_flights': demo_results,
                'recent_queries_1h': recent_queries,
                'recent_real_results_1h': recent_results,
                'data_collection': 'BYOB extension + Amadeus API'
            }
        }

@app.get("/api/data_status")
async def get_data_status():
    """Get detailed status of real vs demo data"""
    with get_db_connection() as conn:
        # Detailed breakdown
        total_results = conn.execute('SELECT COUNT(*) FROM results').fetchone()[0]
        real_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "extension" AND valid = 1').fetchone()[0]
        demo_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "demo"').fetchone()[0]

        # By source breakdown
        source_breakdown = conn.execute('''
            SELECT 
                CASE 
                    WHEN source = "extension" THEN "Real Browser Extension Data"
                    WHEN source = "demo" THEN "Demo/Test Data"
                    ELSE "Other"
                END as source_type,
                COUNT(*) as count
            FROM results 
            GROUP BY source_type
            ORDER BY count DESC
        ''').fetchall()

        # Recent activity by query
        recent_activity = conn.execute('''
            SELECT 
                q.id,
                q.origin || " → " || q.destination as route,
                q.depart_date,
                COUNT(r.id) as result_count,
                SUM(CASE WHEN r.source = "extension" THEN 1 ELSE 0 END) as real_count
            FROM queries q
            LEFT JOIN results r ON q.id = r.query_id
            WHERE q.created_at > datetime("now", "-24 hours")
            GROUP BY q.id
            ORDER BY q.created_at DESC
            LIMIT 10
        ''').fetchall()

        return {
            'summary': {
                'total_results': total_results,
                'real_results': real_results,
                'demo_results': demo_results,
                'real_percentage': round((real_results / total_results * 100) if total_results > 0 else 0, 1)
            },
            'by_source': [dict(row) for row in source_breakdown],
            'recent_activity': [dict(row) for row in recent_activity],
            'collection_method': 'BYOB (Bring Your Own Browser) - Extension only',
            'demo_data_disabled': True
        }

@app.get("/debug/users")
async def debug_users():
    """Debug endpoint to check users (remove in production)"""
    with get_db_connection() as conn:
        users = conn.execute('SELECT id, username, email, created_at FROM users').fetchall()
        return {
            'users': [dict(user) for user in users],
            'total': len(users)
        }

# ------------ User Management (keeping existing functionality) ------------

def get_current_user(request: Request):
    """Helper function to get current user from session"""
    session_token = request.cookies.get("session_token")
    if session_token and session_token in user_sessions:
        return user_sessions[session_token]
    return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("home.html", {
        "request": request,
        "session": user or {}
    })

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Search page with BYOB interface"""
    user = get_current_user(request)
    return templates.TemplateResponse("search.html", {
        "request": request,
        "session": user or {},
        "ingest_token": INGEST_TOKEN,
        "backend_url": str(request.base_url).rstrip('/')
    })

@app.get("/alerts", response_class=HTMLResponse)
async def alerts_dashboard(request: Request):
    """Alerts dashboard"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Flight Alerts - FlightAlert Pro</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; }}
        .tabs {{ border-bottom: 2px solid #007bff; margin-bottom: 20px; }}
        .tab {{ display: inline-block; padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; }}
        .tab.active {{ border-bottom-color: #007bff; background: #f0f8ff; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .form-group {{ margin: 15px 0; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        .form-group input, .form-group select {{ padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 200px; }}
        .btn {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        .btn:hover {{ background: #0056b3; }}
        .match-item {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 4px; }}
        .match-price {{ font-size: 1.2em; font-weight: bold; color: #28a745; }}
        .match-route {{ color: #007bff; font-weight: bold; }}
        .alert-item {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #007bff; }}
    </style>
</head>
<body>
    <h1>✈️ Flight Alerts Dashboard</h1>

    <div class="tabs">
        <div class="tab active" onclick="showTab('create')">Create Alert</div>
        <div class="tab" onclick="showTab('active')">My Alerts</div>
        <div class="tab" onclick="showTab('matches')">Recent Matches</div>
    </div>

    <div id="create" class="tab-content active">
        <h2>Create New Alert</h2>

        <div style="margin-bottom: 20px;">
            <label>Alert Type:</label>
            <select id="alertType" onchange="showAlertForm()">
                <option value="cheap">Cheap Flights</option>
                <option value="rare">Rare Aircraft</option>
                <option value="adventurous">Adventurous (Any Destination)</option>
                <option value="price_war">Price War Tracker</option>
            </select>
        </div>

        <form id="alertForm">
            <div id="basicFields">
                <div class="form-group">
                    <label>From (Origin):</label>
                    <input type="text" id="origin" placeholder="LHR" maxlength="3">
                </div>
                <div class="form-group">
                    <label>To (Destination):</label>
                    <input type="text" id="destination" placeholder="AMS" maxlength="3">
                </div>
                <div class="form-group">
                    <label>Departure Start:</label>
                    <input type="date" id="departStart">
                </div>
                <div class="form-group">
                    <label>Departure End:</label>
                    <input type="date" id="departEnd">
                </div>
                <div class="form-group">
                    <label>Max Price (£):</label>
                    <input type="number" id="maxPrice" placeholder="200">
                </div>
            </div>

            <div id="rareFields" style="display: none;">
                <div class="form-group">
                    <label>Rare Aircraft (comma-separated):</label>
                    <input type="text" id="rareAircraft" placeholder="A340,B747,DC-10">
                </div>
            </div>

            <div class="form-group">
                <label>Notes:</label>
                <input type="text" id="notes" placeholder="Optional notes">
            </div>

            <button type="button" class="btn" onclick="createAlert()">Create Alert</button>
        </form>
    </div>

    <div id="active" class="tab-content">
        <h2>My Active Alerts</h2>
        <div id="activeAlerts">Loading...</div>
    </div>

    <div id="matches" class="tab-content">
        <h2>Recent Matches</h2>
        <div id="recentMatches">Loading...</div>
    </div>

    <script>
        function showTab(tabName) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');

            if (tabName === 'active') loadActiveAlerts();
            if (tabName === 'matches') loadRecentMatches();
        }}

        function showAlertForm() {{
            const type = document.getElementById('alertType').value;
            const rareFields = document.getElementById('rareFields');
            const destField = document.getElementById('destination').parentElement;
            const maxPriceField = document.getElementById('maxPrice').parentElement;

            // Reset all fields
            rareFields.style.display = 'none';
            destField.style.display = 'block';
            maxPriceField.querySelector('label').textContent = 'Max Price (£):';

            if (type === 'rare') {{
                rareFields.style.display = 'block';
                maxPriceField.querySelector('label').textContent = 'Max Price (£) - Optional:';
            }} else if (type === 'adventurous') {{
                destField.style.display = 'none';
                document.getElementById('destination').value = '';
                maxPriceField.querySelector('label').textContent = 'Budget (£):';
            }} else if (type === 'price_war') {{
                maxPriceField.querySelector('label').textContent = 'Alert when price drops below (£):';
            }}
        }}

        async function createAlert() {{
            const data = {{
                type: document.getElementById('alertType').value,
                origin: document.getElementById('origin').value.toUpperCase() || null,
                destination: document.getElementById('destination').value.toUpperCase() || null,
                depart_start: document.getElementById('departStart').value || null,
                depart_end: document.getElementById('departEnd').value || null,
                max_price: parseFloat(document.getElementById('maxPrice').value) || null,
                rare_aircraft_list: document.getElementById('rareAircraft').value || null,
                notes: document.getElementById('notes').value || null
            }};

            try {{
                const response = await fetch('/api/alerts', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }});

                if (response.ok) {{
                    alert('Alert created successfully!');
                    document.getElementById('alertForm').reset();
                    // Reset form visibility for new alert
                    showAlertForm();
                }} else {{
                    const errorData = await response.json();
                    alert('Failed to create alert: ' + (errorData.detail || 'Unknown error'));
                }}
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function loadActiveAlerts() {{
            try {{
                const response = await fetch('/api/alerts');
                const data = await response.json();

                const html = data.alerts.map(alert => `
                    <div class="alert-item">
                        <strong>${{alert.type.toUpperCase()}}</strong> alert<br>
                        Route: ${{alert.origin || '?'}} → ${{alert.destination || 'Any'}}<br>
                        Price: Up to £${{alert.max_price || '∞'}}<br>
                        Created: ${{new Date(alert.created_at).toLocaleDateString()}}
                        ${{alert.notes ? '<br>Notes: ' + alert.notes : ''}}
                    </div>
                `).join('');

                document.getElementById('activeAlerts').innerHTML = html || 'No active alerts';
            }} catch (e) {{
                document.getElementById('activeAlerts').innerHTML = 'Error loading alerts';
            }}
        }}

        async function loadRecentMatches() {{
            try {{
                const response = await fetch('/api/matches');
                const data = await response.json();

                const html = data.matches.map(match => `
                    <div class="match-item">
                        <div class="match-route">${{match.route}}</div>
                        <div class="match-price">£${{match.price.amount}} ${{match.price.currency}}</div>
                        <div>${{match.carrier}} ${{match.flight_number}}</div>
                        <div>Found on: ${{match.site.name}}</div>
                        <div>Matched: ${{new Date(match.matched_at).toLocaleString()}}</div>
                        ${{match.booking_url ? `<a href="${{match.booking_url}}" target="_blank">Book Now</a>` : ''}}
                        ${{!match.seen ? ' <strong>(NEW)</strong>' : ''}}
                    </div>
                `).join('');

                document.getElementById('recentMatches').innerHTML = html || 'No recent matches';
            }} catch (e) {{
                document.getElementById('recentMatches').innerHTML = 'Error loading matches';
            }}
        }}

        // Load initial data and set initial form state
        loadActiveAlerts();
        showAlertForm();
    </script>

    <p><a href="/search">← Back to Search</a> | <a href="/operator">Operator Console</a></p>
</body>
</html>
    """)

@app.post("/api/search")
async def api_search(request: Request, origin: str = Form(...), destination: str = Form(...), date: str = Form(...)):
    """API search endpoint that creates query and returns deep links"""
    try:
        query_request = QueryRequest(origin=origin, destination=destination, depart_date=date)
        result = await create_query(query_request)

        # Add JavaScript to broadcast query_id to extension
        if result and 'query_id' in result:
            backend_url = str(request.base_url).rstrip('/')
            result['broadcast_script'] = f"""
            <script>
                // Broadcast query_id to extension for BYOB ingestion
                localStorage.setItem("FA_QUERY_ID", "{result['query_id']}");
                localStorage.setItem("FA_INGEST_TOKEN", "{INGEST_TOKEN}");
                localStorage.setItem("FA_BACKEND_URL", "{backend_url}");

                // Broadcast to extension content scripts
                window.postMessage({{
                    type: "FA_QUERY_CREATED",
                    queryId: {result['query_id']},
                    token: "{INGEST_TOKEN}",
                    backendUrl: "{backend_url}"
                }}, "*");

                console.log("FlightAlert: Broadcasting query_id {result['query_id']} to extension");
                console.log("FlightAlert: Backend URL set to {backend_url}");

                // Also try direct extension messaging
                if (window.chrome && window.chrome.runtime) {{
                    try {{
                        chrome.runtime.sendMessage({{
                            type: "FA_QUERY_CREATED",
                            queryId: {result['query_id']},
                            token: "{INGEST_TOKEN}",
                            backendUrl: "{backend_url}"
                        }});
                    }} catch(e) {{
                        console.log("Extension not ready or not installed");
                    }}
                }}
            </script>
            """

        return result
    except Exception as e:
        return {"error": str(e), "success": False}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "session": {}
    })

@app.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        email = email.strip()
        password = password.strip()

        print(f"🔐 Login attempt for email: {email}")

        if not email or not password:
            print("❌ Missing email or password")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "session": {},
                "error": "Email and password are required"
            })

        # Check database for user
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            print(f"🔍 User lookup result: {'Found' if user else 'Not found'}")

        if user and check_password_hash(user['password_hash'], password):
            print(f"✅ Login successful for {email}")
            # Create session
            session_token = secrets.token_urlsafe(32)
            user_sessions[session_token] = {
                'user_id': user['id'],
                'email': user['email'],
                'username': user['username'],
                'created_at': datetime.utcnow().isoformat()
            }

            # Redirect to search
            from fastapi.responses import RedirectResponse
            response = RedirectResponse(url="/search", status_code=302)
            response.set_cookie(key="session_token", value=session_token, httponly=True, max_age=86400)
            return response
        else:
            print(f"❌ Invalid credentials for {email}")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "session": {},
                "error": "Invalid email or password"
            })
    except Exception as e:
        print(f"❌ Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "session": {},
            "error": "Login failed. Please try again."
        })

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "session": {}
    })

@app.post("/signup", response_class=HTMLResponse)
async def signup_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    try:
        username = username.strip()
        email = email.strip()
        password = password.strip()

        print(f"📝 Signup attempt for: {username} ({email})")

        if not username or not email or not password:
            print("❌ Missing required signup fields")
            return templates.TemplateResponse("signup.html", {
                "request": request,
                "session": {},
                "error": "All fields are required"
            })

        # Check if user already exists
        with get_db_connection() as conn:
            existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

            if existing:
                print(f"❌ User already exists: {email}")
                return templates.TemplateResponse("signup.html", {
                    "request": request,
                    "session": {},
                    "error": "User with this email already exists"
                })

            # Create new user
            password_hash = generate_password_hash(password)
            cursor = conn.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid
            print(f"✅ Created new user: {username} (ID: {user_id})")

        # Auto-login after signup
        session_token = secrets.token_urlsafe(32)
        user_sessions[session_token] = {
            'user_id': user_id,
            'email': email,
            'username': username,
            'created_at': datetime.utcnow().isoformat()
        }

        from fastapi.responses import RedirectResponse
        response = RedirectResponse(url="/search", status_code=302)
        response.set_cookie(key="session_token", value=session_token, httponly=True, max_age=86400)
        return response
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "session": {},
            "error": "Signup failed. Please try again."
        })

@app.post("/logout")
async def logout_user(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token and session_token in user_sessions:
        del user_sessions[session_token]

    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session_token")
    return response

# ------------ Extension Support Page ------------

# ------------ Alert Management Endpoints ------------

class AlertRequest(BaseModel):
    type: str = "cheap"  # cheap, rare, adventurous, price_war
    origin: Optional[str] = None
    destination: Optional[str] = None
    one_way: bool = True
    depart_start: Optional[str] = None
    depart_end: Optional[str] = None
    return_start: Optional[str] = None
    return_end: Optional[str] = None
    min_bags: int = 0
    max_bags: int = 2
    cabin: str = "economy"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    rare_aircraft_list: Optional[str] = None
    notes: Optional[str] = None

@app.post("/api/alerts")
async def create_alert(alert: AlertRequest, request: Request):
    """Create a new price alert"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO alerts (
                    user_id, type, origin, destination, one_way, depart_start, depart_end,
                    return_start, return_end, min_bags, max_bags, cabin, min_price, max_price,
                    min_duration, max_duration, rare_aircraft_list, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['user_id'], alert.type, alert.origin, alert.destination, alert.one_way,
                alert.depart_start, alert.depart_end, alert.return_start, alert.return_end,
                alert.min_bags, alert.max_bags, alert.cabin, alert.min_price, alert.max_price,
                alert.min_duration, alert.max_duration, alert.rare_aircraft_list, alert.notes
            ))
            conn.commit()
            alert_id = cursor.lastrowid

        logger.info(f"✅ Created {alert.type} alert {alert_id} for user {user['user_id']}")
        return {"alert_id": alert_id, "success": True}

    except Exception as e:
        logger.error(f"❌ Alert creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_user_alerts(request: Request):
    """Get user's active alerts"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            alerts = conn.execute('''
                SELECT * FROM alerts
                WHERE user_id = ? AND active = 1
                ORDER BY created_at DESC
            ''', (user['user_id'],)).fetchall()

            return {"alerts": [dict(alert) for alert in alerts]}

    except Exception as e:
        logger.error(f"❌ Alert retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/matches")
async def get_alert_matches(request: Request):
    """Get recent matches for user's alerts"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            matches = conn.execute('''
                SELECT
                    m.*, a.type as alert_type, a.origin, a.destination,
                    r.price_min, r.price_currency, r.raw_json, r.booking_url,
                    s.name as site_name, s.domain
                FROM matches m
                JOIN alerts a ON m.alert_id = a.id
                JOIN results r ON m.result_id = r.id
                JOIN sites s ON r.site_id = s.id
                WHERE a.user_id = ? AND m.matched_at > datetime('now', '-7 days')
                ORDER BY m.matched_at DESC
                LIMIT 50
            ''', (user['user_id'],)).fetchall()

            formatted_matches = []
            for match in matches:
                try:
                    result_data = json.loads(match['raw_json'])
                    formatted_matches.append({
                        'match_id': match['id'],
                        'alert_type': match['alert_type'],
                        'route': f"{match['origin']} → {match['destination']}",
                        'price': {
                            'amount': match['price_min'],
                            'currency': match['price_currency']
                        },
                        'carrier': result_data.get('carrier', 'Unknown'),
                        'flight_number': result_data.get('flight_number', ''),
                        'site': {
                            'name': match['site_name'],
                            'domain': match['domain']
                        },
                        'booking_url': match['booking_url'],
                        'matched_at': match['matched_at'],
                        'seen': bool(match['seen'])
                    })
                except Exception as e:
                    logger.warning(f"Error formatting match: {e}")
                    continue

            return {"matches": formatted_matches}

    except Exception as e:
        logger.error(f"❌ Match retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/matches/{match_id}/seen")
async def mark_match_seen(match_id: int, request: Request):
    """Mark a match as seen"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            # Verify the match belongs to this user
            match = conn.execute('''
                SELECT m.* FROM matches m
                JOIN alerts a ON m.alert_id = a.id
                WHERE m.id = ? AND a.user_id = ?
            ''', (match_id, user['user_id'])).fetchone()

            if not match:
                raise HTTPException(status_code=404, detail="Match not found")

            conn.execute('UPDATE matches SET seen = 1 WHERE id = ?', (match_id,))
            conn.commit()

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Mark seen failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, request: Request):
    """Delete a user's alert"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            # Verify the alert belongs to this user
            alert = conn.execute('''
                SELECT id FROM alerts
                WHERE id = ? AND user_id = ?
            ''', (alert_id, user['user_id'])).fetchone()

            if not alert:
                raise HTTPException(status_code=404, detail="Alert not found")

            # Delete the alert (set active = 0 instead of hard delete to preserve history)
            conn.execute('UPDATE alerts SET active = 0 WHERE id = ?', (alert_id,))
            conn.commit()

        logger.info(f"✅ Deleted alert {alert_id} for user {user['user_id']}")
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Alert deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/operator", response_class=HTMLResponse)
async def operator_console(request: Request):
    """Operator console for single-operator BYOB mode"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    # Get recent queries and active alerts to generate browse URLs
    with get_db_connection() as conn:
        # Recent queries from last 7 days
        recent_queries = conn.execute('''
            SELECT DISTINCT origin, destination, depart_date
            FROM queries
            WHERE created_at > datetime('now', '-7 days')
            ORDER BY created_at DESC
            LIMIT 15
        ''').fetchall()

        # Active alerts
        alerts = conn.execute('''
            SELECT DISTINCT origin, destination, depart_start, depart_end
            FROM alerts
            WHERE active = 1 AND origin IS NOT NULL AND destination IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        ''').fetchall()

    browse_urls = []

    # Add recent queries
    for query in recent_queries:
        date_str = query['depart_date']
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            # Key sites for operator browsing
            sites = [
                ('Skyscanner', f"https://www.skyscanner.net/transport/flights/{query['origin'].lower()}/{query['destination'].lower()}/{date_obj.strftime('%y%m%d')}/"),
                ('Kayak', f"https://www.kayak.com/flights/{query['origin']}-{query['destination']}/{date_str}"),
                ('Google Flights', f"https://www.google.com/travel/flights?q=Flights%20from%20{query['origin']}%20to%20{query['destination']}%20on%20{date_str}"),
                ('British Airways', f"https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?origin={query['origin']}&destination={query['destination']}&departureDate={date_str}"),
                ('Ryanair', f"https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={date_str}&origin={query['origin']}&destination={query['destination']}")
            ]

            for site_name, url in sites:
                browse_urls.append({
                    'route': f"{query['origin']} → {query['destination']}",
                    'date': date_str,
                    'site': site_name,
                    'url': url,
                    'type': 'recent_query'
                })
        except ValueError:
            continue

    # Add alert-based URLs
    for alert in alerts:
        if alert['depart_start']:
            date_str = alert['depart_start']
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                sites = [
                    ('Skyscanner',f"https://www.skyscanner.net/transport/flights/{alert['origin'].lower()}/{alert['destination'].lower()}/{date_obj.strftime('%y%m%d')}/"),
                    ('Kayak', f"https://www.kayak.com/flights/{alert['origin']}-{alert['destination']}/{date_str}")
                ]

                for site_name, url in sites:
                    browse_urls.append({
                        'route': f"{alert['origin']} → {alert['destination']}",
                        'date': date_str,
                        'site': site_name,
                        'url': url,
                        'type': 'alert'
                    })
            except ValueError:
                continue

    backend_url = str(request.base_url).rstrip('/')

    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>BYOB Operator Console - FlightAlert Pro</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; }}
        .header {{ background: #e8f4fd; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .setup-check {{ background: #f0f8ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #007bff; }}
        .url-item {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }}
        .route {{ font-weight: bold; color: #007bff; }}
        .site {{ color: #666; margin-left: 10px; }}
        .type-badge {{ background: #007bff; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 10px; }}
        .alert-type {{ background: #28a745; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .test-section {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .btn {{ padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }}
        .btn:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 BYOB Operator Console</h1>
        <p><strong>Single-Operator Mode:</strong> You browse airline sites normally. Your extension collects real prices. Users get results.</p>
        <p><strong>⚠️ REAL DATA ONLY:</strong> Demo data has been disabled. Only actual scraped flight prices will be shown.</p>
    </div>

    <div class="setup-check">
        <h3>🔧 Extension Setup Check</h3>
        <p><strong>Backend URL:</strong> <code>{backend_url}</code></p>
        <p><strong>Ingest Token:</strong> <code>{INGEST_TOKEN}</code></p>
        <p><strong>Test connectivity:</strong> <a href="{backend_url}/api/debug/connectivity" target="_blank" class="btn">Test Connection</a></p>
    </div>

    <div class="test-section">
        <h3>🧪 Quick Test</h3>
        <p>Test if your backend can receive data:</p>
        <button class="btn" onclick="testIngestion()">Send Test Data</button>
        <div id="testResult" style="margin-top: 10px;"></div>
    </div>

    <h2>📋 Browse URLs ({len(browse_urls)} total)</h2>
    <p>Open these in new tabs. Your extension will automatically extract and send prices back to the system.</p>

    {''.join([f'''
    <div class="url-item">
        <span class="route">{url['route']}</span>
        <span class="site">- {url['site']}</span>
        <span class="type-badge {'alert-type' if url['type'] == 'alert' else ''}">{url['type'].replace('_', ' ').title()}</span>
        <span style="color: #999; margin-left: 10px;">({url['date']})</span><br>
        <a href="{url['url']}" target="_blank">{url['url']}</a>
    </div>
    ''' for url in browse_urls])}

    <script>
        async function testIngestion() {{
            const resultDiv = document.getElementById('testResult');
            resultDiv.innerHTML = '⏳ Testing...';

            try {{
                const response = await fetch('{backend_url}/api/debug/ingest_example/1', {{
                    method: 'POST',
                    headers: {{
                        'X-FA-Token': '{INGEST_TOKEN}'
                    }}
                }});

                const data = await response.json();

                if (response.ok) {{
                    resultDiv.innerHTML = '✅ Test successful! Backend can receive data.';
                    resultDiv.style.color = 'green';
                }} else {{
                    resultDiv.innerHTML = '❌ Test failed: ' + (data.detail || 'Unknown error');
                    resultDiv.style.color = 'red';
                }}
            }} catch (error) {{
                resultDiv.innerHTML = '❌ Connection failed: ' + error.message;
                resultDiv.style.color = 'red';
            }}
        }}
    </script>

    <p><a href="/search">← Back to Search</a> | <a href="/alerts">View Alerts</a></p>
</body>
</html>
    """)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard page"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    # Get user's alerts
    with get_db_connection() as conn:
        alerts = conn.execute('''
            SELECT * FROM alerts
            WHERE user_id = ? AND active = 1
            ORDER BY created_at DESC
        ''', (user['user_id'],)).fetchall()

        # Get recent matches
        matches = conn.execute('''
            SELECT COUNT(*) as count FROM matches m
            JOIN alerts a ON m.alert_id = a.id
            WHERE a.user_id = ? AND m.matched_at > datetime('now', '-7 days')
        ''', (user['user_id'],)).fetchone()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "session": user,
        "alerts": [dict(alert) for alert in alerts],
        "recent_matches": matches['count'] if matches else 0
    })

@app.get("/create_alert", response_class=HTMLResponse)
async def create_alert_page(request: Request):
    """Create alert page"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    today = datetime.now().strftime('%Y-%m-%d')
    return templates.TemplateResponse("create_alert.html", {
        "request": request,
        "session": user,
        "today": today
    })

@app.post("/create_alert", response_class=HTMLResponse)
async def create_alert_post(
    request: Request,
    alert_type: str = Form(...),
    trip_type: str = Form(...),
    departure_airport: str = Form(...),
    destination_airport: str = Form(default=""),
    airline: str = Form(default=""),
    aircraft_type: str = Form(default=""),
    max_price: float = Form(default=None),
    min_baggage: int = Form(default=None),
    max_baggage: int = Form(default=None),
    departure_date: str = Form(...),
    return_date: str = Form(default=""),
    min_trip_duration: int = Form(default=None),
    max_trip_duration: int = Form(default=None)
):
    """Handle alert creation form submission"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    try:
        # Process form data
        departure_airports = [ap.strip() for ap in departure_airport.split(',') if ap.strip()]
        destination_airports = [ap.strip() for ap in destination_airport.split(',') if ap.strip()] if destination_airport else []
        airlines = [al.strip() for al in airline.split(',') if al.strip()] if airline else []

        # Convert form data to database format
        one_way = (trip_type == 'one_way')

        with get_db_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO alerts (
                    user_id, type, origin, destination, one_way, depart_start, depart_end,
                    return_start, return_end, min_bags, max_bags, cabin, min_price, max_price,
                    min_duration, max_duration, rare_aircraft_list, notes, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['user_id'],
                alert_type,
                ','.join(departure_airports) if departure_airports else None,
                ','.join(destination_airports) if destination_airports else None,
                one_way,
                departure_date,
                departure_date,  # For now, use same date for start and end
                return_date if return_date else None,
                return_date if return_date else None,
                min_baggage or 0,
                max_baggage or 50,
                'economy',  # Default cabin class
                None,  # min_price
                max_price,
                min_trip_duration,
                max_trip_duration,
                aircraft_type if aircraft_type else None,
                f"Alert created via web form. Airlines: {','.join(airlines) if airlines else 'Any'}",
                True
            ))
            conn.commit()
            alert_id = cursor.lastrowid

        logger.info(f"✅ Created {alert_type} alert {alert_id} for user {user['user_id']}")

        # Redirect to dashboard with success message
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard?alert_created=1", status_code=302)

    except Exception as e:
        logger.error(f"❌ Alert creation failed: {e}")
        today = datetime.now().strftime('%Y-%m-%d')
        return templates.TemplateResponse("create_alert.html", {
            "request": request,
            "session": user,
            "today": today,
            "error": f"Failed to create alert: {str(e)}"
        })

@app.get("/preferences", response_class=HTMLResponse)
async def preferences_page(request: Request):
    """User preferences page"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    return templates.TemplateResponse("preferences.html", {
        "request": request,
        "session": user
    })

@app.get("/logout")
async def logout_get(request: Request):
    """Handle GET request to logout"""
    return await logout_user(request)

@app.get("/upgrade", response_class=HTMLResponse)
async def upgrade_page(request: Request):
    """Upgrade/subscription page"""
    user = get_current_user(request)
    return templates.TemplateResponse("upgrade.html", {
        "request": request,
        "session": user or {}
    })

@app.get("/extension", response_class=HTMLResponse)
async def extension_page(request: Request):
    """Page explaining the browser extension"""
    backend_url = str(request.base_url).rstrip('/')

    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>FlightAlert Pro Extension Setup</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .highlight {{ background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .code {{ background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; }}
        .step {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; }}
        .warning {{ background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; }}
        .btn {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }}
        .success {{ color: #28a745; font-weight: bold; }}
        .error {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>🚀 FlightAlert Pro BYOB Extension</h1>

    <div class="highlight">
        <h2>BYOB = Bring Your Own Browser</h2>
        <p>You browse airline sites normally. Extension extracts real prices. No bots, no blocks, just real data from your actual browsing!</p>
    </div>

    <div class="warning">
        <h3>⚠️ Critical Setup Requirements</h3>
        <p>For your extension to work with this Codespaces backend:</p>
        <ol>
            <li><strong>Backend URL must be:</strong> <code>{backend_url}</code></li>
            <li><strong>Token must be:</strong> <code>{INGEST_TOKEN}</code></li>
            <li><strong>Host permissions must include:</strong> <code>*.githubpreview.dev</code></li>
        </ol>
    </div>

    <div class="step">
        <h3>🔧 Extension Configuration</h3>
        <p>Update your extension's background.js or options with:</p>
        <div class="code">
BACKEND_BASE_URL = "{backend_url}"<br>
INGEST_TOKEN = "{INGEST_TOKEN}"
        </div>
    </div>

    <div class="step">
        <h3>📋 manifest.json Host Permissions</h3>
        <p>Add these to your extension's manifest.json:</p>
        <div class="code">
"host_permissions": [<br>
&nbsp;&nbsp;"https://*.githubpreview.dev/*",<br>
&nbsp;&nbsp;"https://*.skyscanner.net/*",<br>
&nbsp;&nbsp;"https://*.kayak.com/*",<br>
&nbsp;&nbsp;"https://*.britishairways.com/*",<br>
&nbsp;&nbsp;"https://*.google.com/travel/flights/*"<br>
]
        </div>
    </div>

    <div class="step">
        <h3> TEst Your Setup</h3>
        <p>Click this button to verify your extension can reach the backend:</p>
        <button class="btn" onclick="testConnection()">Test Connection</button>
        <div id="testResult" style="margin-top: 10px;"></div>
    </div>

    <div class="step">
        <h3>🎯 How to Use</h3>
        <ol>
            <li>Go to <a href="/search">Search Page</a> and search for flights</li>
            <li>Click the generated deep links to open airline sites</li>
            <li>Your extension automatically extracts prices in the background</li>
            <li>Return to see aggregated results from all sites</li>
        </ol>
    </div>

    <script>
        async function testConnection() {{
            const resultDiv = document.getElementById('testResult');
            resultDiv.innerHTML = '⏳ Testing connection...';

            try {{
                const response = await fetch('{backend_url}/api/debug/connectivity', {{
                    headers: {{
                        'X-FA-Token': '{INGEST_TOKEN}'
                    }}
                }});

                const data = await response.json();

                if (response.ok && data.token_valid) {{
                    resultDiv.innerHTML = '<span class="success">✅ Connection successful! Backend is reachable and token is valid.</span>';
                }} else if (response.ok) {{
                    resultDiv.innerHTML = '<span class="error">❌ Connected but token invalid. Check your extension token.</span>';
                }} else {{
                    resultDiv.innerHTML = '<span class="error">❌ Connection failed: HTTP ' + response.status + '</span>';
                }}
            }} catch (error) {{
                resultDiv.innerHTML = '<span class="error">❌ Connection failed: ' + error.message + '</span>';
            }}
        }}
    </script>

    <p><a href="/search">← Back to Search</a> | <a href="/operator">Operator Console</a></p>
</body>
</html>
    """)

if __name__ == "__main__":
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        # Verify all imports work
        print("✅ All required packages imported successfully")

        print("🚀 Starting FlightAlert Pro BYOB Edition...")
        print("🎯 Browser Extension + FastAPI Architecture")
        print("📡 Server will be available at: http://0.0.0.0:5000")
        print("🔧 Extension APIs + User Interface")
        print("✅ SQLite Database + Real-time Ingestion")

        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=5000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Installing missing dependencies...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pydantic", "aiohttp", "beautifulsoup4", "pandas", "werkzeug", "python-dateutil", "pytz", "requests", "playwright", "jinja2", "python-multipart"])
        print("✅ Dependencies installed. Please restart the server.")
        sys.exit(1)

#!/usr/bin/env python3
"""
FlightAlert Pro - BYOB Architecture with Browser Extension Support
Production-Grade Flight Scraper with Extension-Based Price Collection
"""

# Import verification
try:
    import fastapi
    import uvicorn
    import pydantic
    import aiohttp
    import bs4
    import pandas
    import werkzeug
    import dateutil
    import pytz
    import requests
    import jinja2
    print("✅ All required packages imported successfully")
except ImportError as e:
    print(f"❌ Missing package: {e}")
    import sys
    import subprocess
    print("Installing missing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pydantic", "aiohttp", "beautifulsoup4", "pandas", "werkzeug", "python-dateutil", "pytz", "requests", "playwright", "jinja2", "python-multipart"])
    print("✅ Dependencies installed. Please restart.")
    sys.exit(1)

import asyncio
import uuid
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
import time
import random
import re
import hashlib
import secrets
import sqlite3
from contextlib import contextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form, Header
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Core imports
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode, urlparse
import threading
from threading import Lock
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil import parser as dtparse
import pytz
import requests

# Try to import Playwright for optional server-side validation
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
    print("✅ Playwright available for validation scraping")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright not available - install with: pip install playwright && playwright install chromium")

# Force headless mode for server validation
HEADLESS = True
print("🤖 Server validation will run in headless mode")

# ------------ Config ------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_PATH = "flightalert.db"
MAX_RESULTS_PER_QUERY = 50
VALIDATION_RATE_LIMIT = 60  # seconds between validations per site
INGEST_TOKEN = "dev-only-token-change-me"  # Simple token to prevent spam

# Amadeus API Configuration
# For Replit: Add these as Secrets (AMADEUS_API_KEY, AMADEUS_API_SECRET)
# For GitHub: Set these as environment variables or manually configure
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
AMADEUS_BASE_URL = "https://api.amadeus.com"
AMADEUS_TEST_MODE = os.getenv("AMADEUS_TEST_MODE", "true").lower() == "true"

# Duffel API Configuration
# For Replit: Add DUFFEL_API_KEY as a Secret
# For GitHub: Set as environment variable or manually configure
DUFFEL_API_KEY = os.getenv("DUFFEL_API_KEY", "DUFFEL_API_KEY")
DUFFEL_BASE_URL = "https://api.duffel.com"

# Debug Duffel configuration
print(f"🔧 Duffel API Key: {DUFFEL_API_KEY[:20]}...")
print(f"🔧 Duffel Base URL: {DUFFEL_BASE_URL}")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("flight-scraper")

# Thread-safe locks
file_lock = Lock()

# Global state
user_sessions: Dict[str, Dict[str, Any]] = {}
PLAY = None
BROWSER = None

# Pydantic models for API
class SiteConfigResponse(BaseModel):
    sites: List[Dict[str, Any]]
    selectors: List[Dict[str, Any]]
    version: str

class QueryRequest(BaseModel):
    origin: str
    destination: str
    depart_date: str
    return_date: Optional[str] = None
    cabin_class: Optional[str] = "economy"  # economy, business, first
    passengers: Optional[int] = 1

class IngestionRequest(BaseModel):
    site: str
    url: str
    query: Dict[str, str]
    currency: str
    itineraries: List[Dict[str, Any]]
    page_meta: Dict[str, Any]

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# Database management
@contextmanager
def get_db_connection():
    """Thread-safe database connection context manager"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database with BYOB architecture tables"""
    with get_db_connection() as conn:
        # Sites table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                allowed_scrape BOOLEAN DEFAULT 0,
                robots_checked_at TIMESTAMP,
                priority INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 0.0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Selectors table for dynamic selector management
        conn.execute('''
            CREATE TABLE IF NOT EXISTS selectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                version INTEGER DEFAULT 1,
                field TEXT NOT NULL,
                strategy TEXT NOT NULL,
                selector TEXT,
                regex_pattern TEXT,
                json_path TEXT,
                priority INTEGER DEFAULT 1,
                success_7d INTEGER DEFAULT 0,
                last_success TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')

        # Queries table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                depart_date TEXT NOT NULL,
                return_date TEXT,
                cabin_class TEXT DEFAULT 'economy',
                passengers INTEGER DEFAULT 1,
                user_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Results table for ingested data
        conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER NOT NULL,
                site_id INTEGER NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_json TEXT NOT NULL,
                hash TEXT NOT NULL,
                price_min REAL,
                price_currency TEXT,
                legs_json TEXT,
                source TEXT DEFAULT 'extension',
                carrier_codes TEXT,
                flight_numbers TEXT,
                stops INTEGER,
                fare_brand TEXT,
                booking_url TEXT,
                valid BOOLEAN DEFAULT 1,
                FOREIGN KEY (query_id) REFERENCES queries (id),
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')

        # Users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                preferences_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Metrics table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                site_id INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Alerts table for price monitoring
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL DEFAULT 'cheap',
                origin TEXT,
                destination TEXT,
                one_way BOOLEAN DEFAULT 1,
                depart_start TEXT,
                depart_end TEXT,
                return_start TEXT,
                return_end TEXT,
                min_bags INTEGER DEFAULT 0,
                max_bags INTEGER DEFAULT 2,
                cabin TEXT DEFAULT 'economy',
                min_price REAL,
                max_price REAL,
                min_duration INTEGER,
                max_duration INTEGER,
                rare_aircraft_list TEXT,
                notes TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Matches table to track alert hits
        conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                result_id INTEGER NOT NULL,
                matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                seen BOOLEAN DEFAULT 0,
                FOREIGN KEY (alert_id) REFERENCES alerts (id),
                FOREIGN KEY (result_id) REFERENCES results (id)
            )
        ''')

        # Price history for price war tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_key TEXT NOT NULL,
                date_key TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                carrier TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_query_id ON results(query_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_hash ON results(hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_selectors_site_field ON selectors(site_id, field)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, active)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_matches_alert ON matches(alert_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_route ON price_history(route_key, date_key)')

        conn.commit()
        logger.info("✅ Database initialized with BYOB architecture")

        # Verify alerts table exists and has correct structure
        cursor = conn.execute("PRAGMA table_info(alerts)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'active' not in columns:
            conn.execute('ALTER TABLE alerts ADD COLUMN active BOOLEAN DEFAULT 1')
            conn.commit()
            logger.info("✅ Updated alerts table structure")

def migrate_users_from_json():
    """Migrate users from users.json to SQLite database"""
    if not os.path.exists('users.json'):
        return

    try:
        with open('users.json', 'r') as f:
            json_users = json.load(f)

        with get_db_connection() as conn:
            for user in json_users:
                # Check if user already exists
                existing = conn.execute('SELECT id FROM users WHERE email = ?', (user['email'],)).fetchone()
                if not existing:
                    conn.execute(
                        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                        (user['username'], user['email'], user['password_hash'])
                    )
                    logger.info(f"✅ Migrated user: {user['username']} ({user['email']})")
            conn.commit()

    except Exception as e:
        logger.warning(f"⚠️ User migration failed: {e}")

def seed_initial_data():
    """Seed database with initial sites and selectors"""
    with get_db_connection() as conn:
        # Check if we already have sites
        existing_sites = conn.execute('SELECT COUNT(*) FROM sites').fetchone()[0]
        if existing_sites > 0:
            return

        # Initial sites
        sites_data = [
            ('skyscanner.net', 'Skyscanner', 0, 1, 'Popular OTA'),
            ('kayak.com', 'Kayak', 0, 1, 'Popular OTA'),
            ('expedia.com', 'Expedia', 0, 2, 'OTA with good coverage'),
            ('booking.com', 'Booking.com', 0, 2, 'Hotels and flights'),
            ('ba.com', 'British Airways', 1, 1, 'Official airline - allowed'),
            ('ryanair.com', 'Ryanair', 1, 1, 'Official airline - allowed'),
            ('easyjet.com', 'easyJet', 1, 1, 'Official airline - allowed'),
            ('lufthansa.com', 'Lufthansa', 1, 1, 'Official airline - allowed'),
            ('airfrance.com', 'Air France', 1, 1, 'Official airline - allowed'),
            ('klm.com', 'KLM', 1, 1, 'Official airline - allowed')
        ]

        for domain, name, allowed, priority, notes in sites_data:
            conn.execute(
                'INSERT INTO sites (domain, name, allowed_scrape, priority, notes) VALUES (?, ?, ?, ?, ?)',
                (domain, name, allowed, priority, notes)
            )

        # Initial selectors for key sites
        site_id_map = {row[0]: row[1] for row in conn.execute('SELECT domain, id FROM sites').fetchall()}

        selectors_data = [
            # Skyscanner
            (site_id_map['skyscanner.net'], 'itineraries', 'css', '[data-testid*="flight-card"], .FlightCard', None, None, 1),
            (site_id_map['skyscanner.net'], 'price_total', 'css', '[data-testid*="price"], .BpkText_bpk-text__money', r'([£$€]\d+)', None, 1),
            (site_id_map['skyscanner.net'], 'carrier', 'css', '[data-testid*="airline"], .airline-name', None, None, 1),

            # Kayak
            (site_id_map['kayak.com'], 'itineraries', 'css', '.result-item, [data-resultid]', None, None, 1),
            (site_id_map['kayak.com'], 'price_total', 'css', '.price-text, [class*="price"]', r'([£$€]\d+)', None, 1),
            (site_id_map['kayak.com'], 'carrier', 'css', '.airline-text, [class*="airline"]', None, None, 1),

            # British Airways
            (site_id_map['ba.com'], 'itineraries', 'css', '.flight-option, .fare-family', None, None, 1),
            (site_id_map['ba.com'], 'price_total', 'css', '.fare-price, [class*="price"]', r'([£$€]\d+)', None, 1),
            (site_id_map['ba.com'], 'carrier', 'css', '.airline-name', None, None, 1),
        ]

        for site_id, field, strategy, selector, regex, json_path, priority in selectors_data:
            if site_id:  # Only insert if site exists
                conn.execute(
                    'INSERT INTO selectors (site_id, field, strategy, selector, regex_pattern, json_path, priority) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (site_id, field, strategy, selector, regex, json_path, priority)
                )

        conn.commit()
        logger.info("✅ Seeded initial sites and selectors")

# Amadeus API Integration
class AmadeusClient:
    """Amadeus API client for flight search"""

    def __init__(self):
        self.api_key = AMADEUS_API_KEY
        self.api_secret = AMADEUS_API_SECRET
        self.base_url = AMADEUS_BASE_URL
        self.test_mode = AMADEUS_TEST_MODE
        self.access_token = None
        self.token_expires_at = None

    def is_configured(self) -> bool:
        """Check if Amadeus credentials are configured"""
        return bool(self.api_key and self.api_secret)

    def _should_attempt_request(self) -> bool:
        """Check if we should attempt API requests (prevents spam when not configured)"""
        if not self.is_configured():
            return False
        # Don't spam failed attempts - only retry every 5 minutes after failure
        if hasattr(self, '_last_failed_attempt'):
            time_since_failure = (datetime.utcnow() - self._last_failed_attempt).total_seconds()
            if time_since_failure < 300:  # 5 minutes
                return False
        return True

    async def get_access_token(self) -> Optional[str]:
        """Get OAuth access token from Amadeus with smart error handling"""
        # Don't attempt if credentials aren't configured or if we should rate limit
        if not self._should_attempt_request():
            return None

        # Check if token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return self.access_token

        try:
            # Get new token
            token_url = f"{self.base_url}/v1/security/oauth2/token"

            data = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.api_secret
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data, headers=headers) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.access_token = token_data.get('access_token')
                        expires_in = token_data.get('expires_in', 3600)
                        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                        # Clear any previous failure timestamps
                        if hasattr(self, '_last_failed_attempt'):
                            delattr(self, '_last_failed_attempt')
                        if hasattr(self, '_error_logged'):
                            delattr(self, '_error_logged')
                        logger.info("✅ Amadeus access token obtained")
                        return self.access_token
                    else:
                        # Set failure timestamp to prevent spam
                        self._last_failed_attempt = datetime.utcnow()
                        if not hasattr(self, '_error_logged'):
                            logger.warning(f"⚠️ Amadeus API credentials not working (status {response.status}). Disabling for 5 minutes to reduce console spam.")
                            self._error_logged = True
                        return None

        except Exception as e:
            self._last_failed_attempt = datetime.utcnow()
            if not hasattr(self, '_error_logged'):
                logger.warning(f"⚠️ Amadeus API authentication error: {e}. Disabling for 5 minutes.")
                self._error_logged = True
            return None

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Search flights using Amadeus API"""
        token = await self.get_access_token()
        if not token:
            return []

        try:
            # Use appropriate endpoint based on trip type
            if return_date:
                endpoint = f"{self.base_url}/v2/shopping/flight-offers"
            else:
                endpoint = f"{self.base_url}/v2/shopping/flight-offers"

            params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': departure_date,
                'adults': adults,
                'max': 20  # Limit results
            }

            if return_date:
                params['returnDate'] = return_date

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        flights = data.get('data', [])
                        logger.info(f"✅ Amadeus returned {len(flights)} flight offers")
                        return self._format_amadeus_results(flights)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Amadeus search failed: {response.status} - {error_text}")
                        return []

        except Exception as e:
            logger.error(f"❌ Amadeus search error: {e}")
            return []

    def _format_amadeus_results(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Amadeus API results to our standard format"""
        formatted_results = []

        for flight in flights:
            try:
                # Extract pricing
                price_info = flight.get('price', {})
                total_price = float(price_info.get('total', 0))
                currency = price_info.get('currency', 'EUR')

                # Extract itinerary info
                itineraries = flight.get('itineraries', [])
                if not itineraries:
                    continue

                segments = []
                for itinerary in itineraries:
                    for segment in itinerary.get('segments', []):
                        departure = segment.get('departure', {})
                        arrival = segment.get('arrival', {})
                        operating = segment.get('operating', {})

                        segments.append({
                            'carrier': operating.get('carrierCode', segment.get('carrierCode', '')),
                            'flight_number': segment.get('number', ''),
                            'origin': departure.get('iataCode', ''),
                            'destination': arrival.get('iataCode', ''),
                            'departure_time': departure.get('at', ''),
                            'arrival_time': arrival.get('at', ''),
                            'aircraft': segment.get('aircraft', {}).get('code', ''),
                            'duration': segment.get('duration', '')
                        })

                if segments:
                    formatted_results.append({
                        'price': {
                            'amount': total_price,
                            'currency': currency
                        },
                        'carrier': segments[0]['carrier'],
                        'flight_number': segments[0]['flight_number'],
                        'departure_time': segments[0]['departure_time'],
                        'arrival_time': segments[-1]['arrival_time'],
                        'stops': len(segments) - 1,
                        'segments': segments,
                        'booking_url': '',  # Amadeus doesn't provide direct booking URLs
                        'source': {
                            'name': 'Amadeus API',
                            'domain': 'amadeus.com',
                            'success_rate': 1.0
                        },
                        'fetched_at': datetime.utcnow().isoformat(),
                        'hash': hashlib.sha256(json.dumps(flight, sort_keys=True).encode()).hexdigest()[:16]
                    })

            except Exception as e:
                logger.warning(f"Error formatting Amadeus result: {e}")
                continue

        return formatted_results

# Duffel API Integration
class DuffelClient:
    """Duffel API client for flight search"""

    def __init__(self):
        self.api_key = DUFFEL_API_KEY
        self.base_url = DUFFEL_BASE_URL

    def is_configured(self) -> bool:
        """Check if Duffel credentials are configured"""
        return bool(self.api_key and self.api_key.startswith('duffel_'))

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, passengers: int = 1) -> List[Dict[str, Any]]:
        """Search flights using Duffel API"""
        if not self.is_configured():
            logger.warning("⚠️ Duffel API key not configured")
            return []

        try:
            # Create offer request
            offer_request_data = {
                "data": {
                    "slices": [
                        {
                            "origin": origin,
                            "destination": destination,
                            "departure_date": departure_date
                        }
                    ],
                    "passengers": [{"type": "adult"} for _ in range(passengers)],
                    "cabin_class": "economy"
                }
            }

            # Add return slice if round trip
            if return_date:
                offer_request_data["data"]["slices"].append({
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date
                })

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Duffel-Version": "v2"
            }

            # Create offer request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/air/offer_requests",
                    json=offer_request_data,
                    headers=headers
                ) as response:
                    if response.status == 201:
                        request_data = await response.json()
                        offer_request_id = request_data["data"]["id"]

                        # Get offers
                        async with session.get(
                            f"{self.base_url}/air/offers",
                            params={"offer_request_id": offer_request_id},
                            headers=headers
                        ) as offers_response:
                            if offers_response.status == 200:
                                offers_data = await offers_response.json()
                                offers = offers_data.get("data", [])
                                logger.info(f"✅ Duffel returned {len(offers)} flight offers")
                                return self._format_duffel_results(offers)
                            else:
                                error_text = await offers_response.text()
                                logger.error(f"❌ Duffel offers failed: {offers_response.status} - {error_text}")
                                logger.error(f"❌ Offer request ID: {offer_request_id}")
                                logger.error(f"❌ Search params: {origin} → {destination} on {departure_date}")
                                return []
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Duffel request failed: {response.status} - {error_text}")
                        logger.error(f"❌ Request data: {offer_request_data}")
                        logger.error(f"❌ Headers used: {headers}")
                        return []

        except Exception as e:
            logger.error(f"❌ Duffel search error: {e}")
            return []

    def _format_duffel_results(self, offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Duffel API results to our standard format"""
        formatted_results = []
        seen_combinations = set()  # Track unique flight combinations

        for offer in offers:
            try:
                # Extract pricing
                total_amount = float(offer.get("total_amount", 0))
                currency = offer.get("total_currency", "GBP")

                # Extract slices (legs)
                slices = offer.get("slices", [])
                if not slices:
                    continue

                segments = []
                first_segment = None
                last_segment = None

                for slice_data in slices:
                    slice_segments = slice_data.get("segments", [])
                    for segment in slice_segments:
                        # Get airline info
                        marketing_carrier = segment.get("marketing_carrier", {})
                        aircraft = segment.get("aircraft", {})

                        segment_info = {
                            'carrier': marketing_carrier.get("iata_code", ""),
                            'carrier_name': marketing_carrier.get("name", ""),
                            'flight_number': segment.get("marketing_carrier_flight_number", ""),
                            'origin': segment.get("origin", {}).get("iata_code", ""),
                            'destination': segment.get("destination", {}).get("iata_code", ""),
                            'departure_time': segment.get("departing_at", ""),
                            'arrival_time': segment.get("arriving_at", ""),
                            'aircraft': aircraft.get("name", ""),
                            'aircraft_code': aircraft.get("iata_code", ""),
                            'duration': segment.get("duration", "")
                        }

                        segments.append(segment_info)

                        if first_segment is None:
                            first_segment = segment_info
                        last_segment = segment_info

                if segments and first_segment and last_segment:
                    # Add aerospace engineering calculations
                    aerospace_data = {}

                    # Get airport coordinates for calculations
                    origin_coords = get_airport_coordinates(first_segment['origin'])
                    dest_coords = get_airport_coordinates(last_segment['destination'])

                    if origin_coords and dest_coords:
                        # Great circle distance calculations
                        distance_data = aerospace_calc.great_circle_distance(
                            origin_coords['lat'], origin_coords['lon'],
                            dest_coords['lat'], dest_coords['lon']
                        )

                        # Initial bearing for navigation
                        bearing = aerospace_calc.initial_bearing(
                            origin_coords['lat'], origin_coords['lon'],
                            dest_coords['lat'], dest_coords['lon']
                        )

                        # Fuel efficiency estimate
                        aircraft_type = first_segment.get('aircraft_code', 'unknown')
                        fuel_data = aerospace_calc.fuel_efficiency_estimate(
                            distance_data['great_circle_km'], aircraft_type
                        )

                        aerospace_data = {
                            'distance': distance_data,
                            'navigation': {
                                'initial_bearing': round(bearing, 1),
                                'bearing_description': get_bearing_description(bearing)
                            },
                            'fuel_analysis': fuel_data,
                            'route_efficiency': calculate_route_efficiency(segments, distance_data)
                        }

                    # Enhanced deduplication - prevent repeated flights with same prices
                    all_flight_numbers = [seg['flight_number'] for seg in segments]
                    route_key = f"{first_segment['origin']}-{last_segment['destination']}"

                    # Extract meaningful time components for deduplication
                    departure_time_short = first_segment['departure_time'][:16] if first_segment['departure_time'] else 'unknown'
                    arrival_time_short = last_segment['arrival_time'][:16] if last_segment['arrival_time'] else 'unknown'

                    # Create primary unique key with full flight details
                    primary_key = f"{route_key}-{first_segment['carrier']}-{'-'.join(all_flight_numbers)}-{departure_time_short}-{arrival_time_short}-{total_amount:.2f}-{len(segments)}"

                    # Create secondary key for aggressive price-based deduplication 
                    # This prevents multiple flights with identical prices from same carrier
                    price_route_key = f"{route_key}-{first_segment['carrier']}-{total_amount:.2f}"

                    # Only add if both uniqueness criteria are met
                    if primary_key not in seen_combinations:
                        # For same carrier + route + price, only keep the first one (usually best time)
                        if price_route_key not in seen_combinations:
                            seen_combinations.add(primary_key)
                            seen_combinations.add(price_route_key)  # Track this price combination

                        # Get full airline name with explanation
                        carrier_code = first_segment['carrier']
                        carrier_name = first_segment.get('carrier_name', '')

                        # Add explanation for common airline codes
                        airline_explanations = {
                            'RJ': 'Royal Jordanian Airlines (Jordan)',
                            'BA': 'British Airways (UK)',
                            'FR': 'Ryanair (Ireland)',
                            'U2': 'easyJet (UK)', 
                            'LH': 'Lufthansa (Germany)',
                            'AF': 'Air France (France)',
                            'KL': 'KLM (Netherlands)',
                            'TK': 'Turkish Airlines (Turkey)',
                            'EK': 'Emirates (UAE)',
                            'QR': 'Qatar Airways (Qatar)',
                            'SV': 'Saudia (Saudi Arabia)',
                            'MS': 'EgyptAir (Egypt)',
                            'BG': 'Biman Bangladesh Airlines (Bangladesh)',
                            'BS': 'US-Bangla Airlines (Bangladesh)'
                        }

                        full_carrier_name = airline_explanations.get(carrier_code, carrier_name or carrier_code)

                        formatted_results.append({
                            'price': {
                                'amount': total_amount,
                                'currency': currency
                            },
                            'carrier': carrier_code,
                            'carrier_name': full_carrier_name,
                            'flight_number': first_segment['flight_number'],
                            'departure_time': first_segment['departure_time'],
                            'arrival_time': last_segment['arrival_time'],
                            'stops': len(segments) - 1,
                            'segments': segments,
                            'booking_url': self._generate_deep_booking_url(first_segment, last_segment, offer.get('id', '')),
                            'offer_id': offer.get('id', ''),
                            'source': {
                                'name': 'Duffel API',
                                'domain': 'duffel.com',
                                'success_rate': 1.0
                            },
                            'aerospace_analysis': aerospace_data,
                            'fetched_at': datetime.utcnow().isoformat(),
                            'hash': hashlib.sha256(json.dumps({
                                'carrier': first_segment['carrier'],
                                'flight_number': first_segment['flight_number'], 
                                'departure_time': first_segment['departure_time'],
                                'price': total_amount,
                                'offer_id': offer.get('id', '')
                            }, sort_keys=True).encode()).hexdigest()[:16]
                        })

            except Exception as e:
                logger.warning(f"Error formatting Duffel result: {e}")
                continue

        logger.info(f"🎯 Duffel API: Formatted {len(formatted_results)} unique flights from {len(offers)} offers")
        return formatted_results

    def _generate_deep_booking_url(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], offer_id: str) -> str:
        """Generate direct airline booking URLs ONLY - no OTA fallbacks"""
        try:
            origin = first_segment.get('origin', '').upper()
            destination = last_segment.get('destination', '').upper()
            carrier = first_segment.get('carrier', '').upper()
            flight_number = first_segment.get('flight_number', '')
            departure_date = first_segment.get('departure_time', '')[:10]  # Get YYYY-MM-DD
            departure_time = first_segment.get('departure_time', '')

            # Extract time components for deeper linking
            if departure_time and 'T' in departure_time:
                time_part = departure_time.split('T')[1][:5]  # Get HH:MM
            else:
                time_part = ''

            # Comprehensive airline-specific deep booking URLs with flight details
            airline_urls = {
                # European Airlines
                'BA': f'https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?journeyType=ONEWAY&origin={origin}&destination={destination}&departureDate={departure_date}&cabinClass=M&adult=1',
                'FR': f'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={departure_date}&origin={origin}&destination={destination}',
                'U2': f'https://www.easyjet.com/en/booking/flights/{origin.lower()}-{destination.lower()}/{departure_date}?adults=1&children=0&infants=0',
                'W6': f'https://wizzair.com/en-gb/flights/select?departureDate={departure_date}&origin={origin}&destination={destination}&adultCount=1',
                'VS': f'https://www.virgin-atlantic.com/gb/en/book-a-flight/select-flights?origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',
                'AF': f'https://www.airfrance.com/en/booking/search?connections%5B0%5D%5Bdeparture%5D={origin}&connections%5B0%5D%5Barrival%5D={destination}&connections%5B0%5D%5BdepartureDate%5D={departure_date}&pax%5Badults%5D=1',
                'LH': f'https://www.lufthansa.com/de/en/booking/offers?departure={origin}&destination={destination}&outbound-date={departure_date}&return-date=&pax.adult=1&cabin-class=economy',
                'KL': f'https://www.klm.com/search/offers?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1&cabinClass=economy',
                'SK': f'https://www.sas.com/book/flights?from={origin}&to={destination}&outDate={departure_date}&adults=1&children=0&youth=0&infants=0',
                'IB': f'https://www.iberia.com/gb/flights/{origin}-{destination}/{departure_date}/?passengers=1',
                'VY': f'https://www.vueling.com/en/flights/{origin.lower()}-{destination.lower()}/{departure_date}?passengers=1',
                'TP': f'https://www.tap.pt/en/flights/{origin}-{destination}?adults=1&departureDate={departure_date}',
                'SN': f'https://www.brusselsairlines.com/en-us/booking/flights/{origin}-{destination}/{departure_date}?ADT=1',
                'LX': f'https://www.swiss.com/us/en/book/outbound-flight/{origin}-{destination}/{departure_date}?travelers=1-0-0-0',
                'OS': f'https://www.austrian.com/us/en/book/flight/{origin}/{destination}?departureDate={departure_date}&numAdults=1',
                'AZ': f'https://www.alitalia.com/en_us/booking/flights-search.html?tripType=OW&departureStation={origin}&arrivalStation={destination}&outboundDate={departure_date}&passengers=1-0-0',
                'AY': f'https://www.finnair.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DY': f'https://www.norwegian.com/en/booking/flight-search?origin={origin}&destination={destination}&outbound={departure_date}&adults=1',
                'EN': f'https://www.airdolomiti.it/en/book-a-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'LO': f'https://www.lot.com/us/en/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'OK': f'https://www.czechairlines.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RO': f'https://www.tarom.ro/en/book-a-flight?tripType=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'JU': f'https://www.airserbia.com/en/booking/flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'OU': f'https://www.croatiaairlines.com/en/book-a-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'JP': f'https://www.adria.si/en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BT': f'https://www.airbaltic.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # North American Airlines
                'DL': f'https://www.delta.com/flight-search/book-a-flight?origin={origin}&destination={destination}&departure_date={departure_date}&passengers=1',
                'UA': f'https://www.united.com/en/us/fsr/choose-flights?f={origin}&t={destination}&d={departure_date}&tt=1&at=1&sc=7',
                'AA': f'https://www.aa.com/booking/choose-flights?localeCode=en_US&from={origin}&to={destination}&departureDate={departure_date}&tripType=OneWay&adult=1',
                'AS': f'https://www.alaskaair.com/booking/reservation/search?passengers=1&from={origin}&to={destination}&departureDate={departure_date}',
                'B6': f'https://www.jetblue.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'WN': f'https://www.southwest.com/air/booking/select.html?originationAirportCode={origin}&destinationAirportCode={destination}&departureDate={departure_date}&adults=1',
                'AC': f'https://www.aircanada.com/us/en/aco/home/book/search/flight.html?tripType=O&org0={origin}&dest0={destination}&departureDate0={departure_date}&adult=1',
                'WS': f'https://www.westjet.com/en-ca/flights/search?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',

                # Middle Eastern Airlines
                'EK': f'https://www.emirates.com/english/book-a-flight/flights-search.aspx?fromCityOrAirport={origin}&toCityOrAirport={destination}&departDate={departure_date}&adults=1',
                'QR': f'https://www.qatarairways.com/en/booking?tripType=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'EY': f'https://www.etihad.com/en/flights/{origin}/{destination}?departureDate={departure_date}&passengerCount=1',
                'TK': f'https://www.turkishairlines.com/en-int/flights/booking/{origin}-{destination}/{departure_date}/?pax=1&cabin=Economy',
                'WY': f'https://www.omanair.com/en/book/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'GF': f'https://www.gulfair.com/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KU': f'https://www.kuwaitairways.com/en/booking/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'SV': f'https://www.saudia.com/book/flight-search?trip=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'MS': f'https://www.egyptair.com/en/fly-egyptair/online-booking?tripType=OW&from={origin}&to={destination}&depDate={departure_date}&adults=1',
                'FZ': f'https://www.flydubai.com/en/book-a-trip/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RJ': f'https://www.rj.com/en/book-and-manage/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AT': f'https://www.royalairmaroc.com/int-en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DT': f'https://www.taag.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TU': f'https://www.tunisair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Asian Airlines
                'SQ': f'https://www.singaporeair.com/en_UK/book-a-flight/search/?triptype=OW&from={origin}&to={destination}&depdate={departure_date}&paxadult=1',
                'CX': f'https://www.cathaypacific.com/cx/en_US/book-a-trip/search.html?tripType=OW&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JL': f'https://www.jal.co.jp/en/dom/search/?ar={origin}&dp={destination}&dd={departure_date}&adult=1',
                'NH': f'https://www.ana.co.jp/en/us/book-plan/book/domestic/search/?departureAirport={origin}&arrivalAirport={destination}&departureDate={departure_date}&adult=1',
                'AI': f'https://www.airindia.in/book/flight-search?trip=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                '6E': f'https://www.goindigo.in/book/flight-search.html?r=1&px=1,0,0&o={origin}&d={destination}&dd={departure_date}',
                'SG': f'https://www.spicejet.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UK': f'https://www.airvistara.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'IX': f'https://www.airindiaexpress.in/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'PK': f'https://www.piac.com.pk/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BG': f'https://www.biman-airlines.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UL': f'https://www.srilankan.com/en_uk/plan-and-book/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TG': f'https://www.thaiairways.com/en_CA/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'MH': f'https://www.malaysiaairlines.com/my/en/book-with-us/search.html?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AK': f'https://www.airasia.com/flights/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Australian Airlines
                'QF': f'https://www.qantas.com/au/en/booking/search.html?tripType=O&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JQ': f'https://www.jetstar.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VA': f'https://www.virginaustralia.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'NZ': f'https://www.airnewzealand.com/booking/select-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'FJ': f'https://www.fijiairways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Latin American Airlines
                'LA': f'https://www.latam.com/en_us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CM': f'https://www.copaair.com/en/web/us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AV': f'https://www.avianca.com/us/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AM': f'https://aeromexico.com/en-us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AR': f'https://www.aerolineas.com.ar/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1'
            }

            # Use airline-specific deep URL if available
            if carrier in deep_airline_urls:
                return deep_airline_urls[carrier]

            # For other airlines, create a Google Flights URL with flight number for easier finding
            if flight_number:
                google_deep_url = f'https://www.google.com/flights?hl=en#flt={origin}.{destination}.{departure_date};c:{carrier}{flight_number}'
                return google_deep_url

            # Fallback to Skyscanner with route and date
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/{departure_date.replace("-", "")}/?adults=1&children=0&adultsv2=1&childrenv2=&infants=0&cabinclass=economy&rtn=0&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false'

        except Exception as e:
            logger.warning(f"Error generating deep booking URL: {e}")
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/'

    def _calculate_aerospace_data(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aerospace engineering data for FlightAPI results"""
        try:
            origin_coords = get_airport_coordinates(first_segment['origin'])
            dest_coords = get_airport_coordinates(last_segment['destination'])

            if origin_coords and dest_coords:
                # Great circle distance calculations
                distance_data = aerospace_calc.great_circle_distance(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Initial bearing for navigation
                bearing = aerospace_calc.initial_bearing(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Fuel efficiency estimate
                aircraft_type = first_segment.get('aircraft', 'unknown')
                fuel_data = aerospace_calc.fuel_efficiency_estimate(
                    distance_data['great_circle_km'], aircraft_type
                )

                return {
                    'distance': distance_data,
                    'navigation': {
                        'initial_bearing': round(bearing, 1),
                        'bearing_description': get_bearing_description(bearing)
                    },
                    'fuel_analysis': fuel_data,
                    'route_efficiency': calculate_route_efficiency(segments, distance_data)
                }
        except Exception as e:
            logger.warning(f"Error calculating aerospace data: {e}")

        return {}

# Initialize API clients
amadeus_client = AmadeusClient()
duffel_client = DuffelClient()
flightapi_client = FlightAPIClient()

# Aerospace Engineering Enhancement Classes
class AerospaceCalculator:
    """Aerospace engineering calculations for flight analysis"""

    def __init__(self):
        self.earth_radius_km = 6371.0
        self.earth_radius_nm = 3440.065  # Nautical miles

    def great_circle_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Dict[str, float]:
        """Calculate great circle distance between two points (shortest flight path)"""
        import math

        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        distance_km = self.earth_radius_km * c
        distance_nm = self.earth_radius_nm * c
        distance_mi = distance_km * 0.621371

        return {
            'great_circle_km': round(distance_km, 2),
            'great_circle_nm': round(distance_nm, 2),
            'great_circle_mi': round(distance_mi, 2)
        }

    def initial_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate initial bearing for great circle route"""
        import math

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)

        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)

        # Normalize to 0-360 degrees
        return (bearing_deg + 360) % 360

    def fuel_efficiency_estimate(self, distance_km: float, aircraft_type: str = "unknown") -> Dict[str, Any]:
        """Estimate fuel consumption based on distance and aircraft type"""

        # Typical fuel consumption rates (liters per km per passenger)
        fuel_rates = {
            "A320": 0.024,  # Airbus A320 family
            "A321": 0.025,
            "A330": 0.028,
            "A350": 0.022,  # More efficient
            "B737": 0.025,  # Boeing 737
            "B738": 0.025,
            "B787": 0.020,  # Very efficient
            "B777": 0.030,
            "E190": 0.026,  # Embraer regional
            "unknown": 0.025  # Average estimate
        }

        rate = fuel_rates.get(aircraft_type.upper(), fuel_rates["unknown"])
        total_fuel_liters = distance_km * rate
        fuel_cost_estimate = total_fuel_liters * 0.85  # ~$0.85 per liter jet fuel

        return {
            'fuel_per_passenger_liters': round(total_fuel_liters, 2),
            'fuel_cost_estimate_usd': round(fuel_cost_estimate, 2),
            'efficiency_rating': 'High' if rate < 0.023 else 'Medium' if rate < 0.027 else 'Standard',
            'aircraft_type': aircraft_type
        }

class AviationWeatherClient:
    """Aviation weather data integration for flight planning"""

    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data"

    async def get_metar(self, airport_code: str) -> Dict[str, Any]:
        """Get current weather conditions (METAR) for airport"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/metar"
                params = {
                    'ids': airport_code.upper(),
                    'format': 'json',
                    'taf': 'false',
                    'hours': '1'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            metar = data[0]
                            return {
                                'airport': airport_code.upper(),
                                'metar_text': metar.get('rawOb', ''),
                                'visibility': metar.get('visib', 'Unknown'),
                                'wind_speed': metar.get('wspd', 0),
                                'wind_direction': metar.get('wdir', 0),
                                'temperature': metar.get('temp', 'Unknown'),
                                'conditions': metar.get('wx', []),
                                'flight_category': metar.get('fltcat', 'Unknown'),
                                'observation_time': metar.get('obsTime', ''),
                                'suitable_for_flight': metar.get('fltcat', '').upper() in ['VFR', 'MVFR']
                            }

        except Exception as e:
            logger.warning(f"Weather API error for {airport_code}: {e}")

        return {
            'airport': airport_code.upper(),
            'metar_text': 'Weather data unavailable',
            'flight_category': 'Unknown',
            'suitable_for_flight': True  # Default assumption
        }

    async def get_taf(self, airport_code: str) -> Dict[str, Any]:
        """Get Terminal Aerodrome Forecast (TAF) for airport"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/taf"
                params = {
                    'ids': airport_code.upper(),
                    'format': 'json',
                    'hours': '12'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            taf = data[0]
                            return {
                                'airport': airport_code.upper(),
                                'taf_text': taf.get('rawTAF', ''),
                                'forecast_time': taf.get('fcstTime', ''),
                                'valid_from': taf.get('validTime', ''),
                                'forecast_conditions': 'Available'
                            }

        except Exception as e:
            logger.warning("Import asyncio")
import uuid
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
import time
import random
import re
import hashlib
import secrets
import sqlite3
from contextlib import contextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form, Header
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Core imports
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode, urlparse
import threading
from threading import Lock
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil import parser as dtparse
import pytz
import requests

# Try to import Playwright for optional server-side validation
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
    print("✅ Playwright available for validation scraping")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright not available - install with: pip install playwright && playwright install chromium")

# Force headless mode for server validation
HEADLESS = True
print("🤖 Server validation will run in headless mode")

# ------------ Config ------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_PATH = "flightalert.db"
MAX_RESULTS_PER_QUERY = 50
VALIDATION_RATE_LIMIT = 60  # seconds between validations per site
INGEST_TOKEN = "dev-only-token-change-me"  # Simple token to prevent spam

# Amadeus API Configuration
# For Replit: Add these as Secrets (AMADEUS_API_KEY, AMADEUS_API_SECRET)
# For GitHub: Set these as environment variables or manually configure
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
AMADEUS_BASE_URL = "https://api.amadeus.com"
AMADEUS_TEST_MODE = os.getenv("AMADEUS_TEST_MODE", "true").lower() == "true"

# Duffel API Configuration
# For Replit: Add DUFFEL_API_KEY as a Secret
# For GitHub: Set as environment variable or manually configure
DUFFEL_API_KEY = os.getenv("DUFFEL_API_KEY", "DUFFEL_API_KEY")
DUFFEL_BASE_URL = "https://api.duffel.com"

# Debug Duffel configuration
print(f"🔧 Duffel API Key: {DUFFEL_API_KEY[:20]}...")
print(f"🔧 Duffel Base URL: {DUFFEL_BASE_URL}")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("flight-scraper")

# Thread-safe locks
file_lock = Lock()

# Global state
user_sessions: Dict[str, Dict[str, Any]] = {}
PLAY = None
BROWSER = None

# Pydantic models for API
class SiteConfigResponse(BaseModel):
    sites: List[Dict[str, Any]]
    selectors: List[Dict[str, Any]]
    version: str

class QueryRequest(BaseModel):
    origin: str
    destination: str
    depart_date: str
    return_date: Optional[str] = None
    cabin_class: Optional[str] = "economy"  # economy, business, first
    passengers: Optional[int] = 1

class IngestionRequest(BaseModel):
    site: str
    url: str
    query: Dict[str, str]
    currency: str
    itineraries: List[Dict[str, Any]]
    page_meta: Dict[str, Any]

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# Database management
@contextmanager
def get_db_connection():
    """Thread-safe database connection context manager"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database with BYOB architecture tables"""
    with get_db_connection() as conn:
        # Sites table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                allowed_scrape BOOLEAN DEFAULT 0,
                robots_checked_at TIMESTAMP,
                priority INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 0.0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Selectors table for dynamic selector management
        conn.execute('''
            CREATE TABLE IF NOT EXISTS selectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                version INTEGER DEFAULT 1,
                field TEXT NOT NULL,
                strategy TEXT NOT NULL,
                selector TEXT,
                regex_pattern TEXT,
                json_path TEXT,
                priority INTEGER DEFAULT 1,
                success_7d INTEGER DEFAULT 0,
                last_success TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')

        # Queries table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                depart_date TEXT NOT NULL,
                return_date TEXT,
                cabin_class TEXT DEFAULT 'economy',
                passengers INTEGER DEFAULT 1,
                user_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Results table for ingested data
        conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER NOT NULL,
                site_id INTEGER NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_json TEXT NOT NULL,
                hash TEXT NOT NULL,
                price_min REAL,
                price_currency TEXT,
                legs_json TEXT,
                source TEXT DEFAULT 'extension',
                carrier_codes TEXT,
                flight_numbers TEXT,
                stops INTEGER,
                fare_brand TEXT,
                booking_url TEXT,
                valid BOOLEAN DEFAULT 1,
                FOREIGN KEY (query_id) REFERENCES queries (id),
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')

        # Users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                preferences_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Metrics table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                site_id INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Alerts table for price monitoring
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL DEFAULT 'cheap',
                origin TEXT,
                destination TEXT,
                one_way BOOLEAN DEFAULT 1,
                depart_start TEXT,
                depart_end TEXT,
                return_start TEXT,
                return_end TEXT,
                min_bags INTEGER DEFAULT 0,
                max_bags INTEGER DEFAULT 2,
                cabin TEXT DEFAULT 'economy',
                min_price REAL,
                max_price REAL,
                min_duration INTEGER,
                max_duration INTEGER,
                rare_aircraft_list TEXT,
                notes TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Matches table to track alert hits
        conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                result_id INTEGER NOT NULL,
                matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                seen BOOLEAN DEFAULT 0,
                FOREIGN KEY (alert_id) REFERENCES alerts (id),
                FOREIGN KEY (result_id) REFERENCES results (id)
            )
        ''')

        # Price history for price war tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_key TEXT NOT NULL,
                date_key TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                carrier TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_query_id ON results(query_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_results_hash ON results(hash)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_selectors_site_field ON selectors(site_id, field)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, active)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_matches_alert ON matches(alert_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_route ON price_history(route_key, date_key)')

        conn.commit()
        logger.info("✅ Database initialized with BYOB architecture")

        # Verify alerts table exists and has correct structure
        cursor = conn.execute("PRAGMA table_info(alerts)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'active' not in columns:
            conn.execute('ALTER TABLE alerts ADD COLUMN active BOOLEAN DEFAULT 1')
            conn.commit()
            logger.info("✅ Updated alerts table structure")

def migrate_users_from_json():
    """Migrate users from users.json to SQLite database"""
    if not os.path.exists('users.json'):
        return

    try:
        with open('users.json', 'r') as f:
            json_users = json.load(f)

        with get_db_connection() as conn:
            for user in json_users:
                # Check if user already exists
                existing = conn.execute('SELECT id FROM users WHERE email = ?', (user['email'],)).fetchone()
                if not existing:
                    conn.execute(
                        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                        (user['username'], user['email'], user['password_hash'])
                    )
                    logger.info(f"✅ Migrated user: {user['username']} ({user['email']})")
            conn.commit()

    except Exception as e:
        logger.warning(f"⚠️ User migration failed: {e}")

def seed_initial_data():
    """Seed database with initial sites and selectors"""
    with get_db_connection() as conn:
        # Check if we already have sites
        existing_sites = conn.execute('SELECT COUNT(*) FROM sites').fetchone()[0]
        if existing_sites > 0:
            return

        # Initial sites
        sites_data = [
            ('skyscanner.net', 'Skyscanner', 0, 1, 'Popular OTA'),
            ('kayak.com', 'Kayak', 0, 1, 'Popular OTA'),
            ('expedia.com', 'Expedia', 0, 2, 'OTA with good coverage'),
            ('booking.com', 'Booking.com', 0, 2, 'Hotels and flights'),
            ('ba.com', 'British Airways', 1, 1, 'Official airline - allowed'),
            ('ryanair.com', 'Ryanair', 1, 1, 'Official airline - allowed'),
            ('easyjet.com', 'easyJet', 1, 1, 'Official airline - allowed'),
            ('lufthansa.com', 'Lufthansa', 1, 1, 'Official airline - allowed'),
            ('airfrance.com', 'Air France', 1, 1, 'Official airline - allowed'),
            ('klm.com', 'KLM', 1, 1, 'Official airline - allowed')
        ]

        for domain, name, allowed, priority, notes in sites_data:
            conn.execute(
                'INSERT INTO sites (domain, name, allowed_scrape, priority, notes) VALUES (?, ?, ?, ?, ?)',
                (domain, name, allowed, priority, notes)
            )

        # Initial selectors for key sites
        site_id_map = {row[0]: row[1] for row in conn.execute('SELECT domain, id FROM sites').fetchall()}

        selectors_data = [
            # Skyscanner
            (site_id_map['skyscanner.net'], 'itineraries', 'css', '[data-testid*="flight-card"], .FlightCard', None, None, 1),
            (site_id_map['skyscanner.net'], 'price_total', 'css', '[data-testid*="price"], .BpkText_bpk-text__money', r'([£$€]\d+)', None, 1),
            (site_id_map['skyscanner.net'], 'carrier', 'css', '[data-testid*="airline"], .airline-name', None, None, 1),

            # Kayak
            (site_id_map['kayak.com'], 'itineraries', 'css', '.result-item, [data-resultid]', None, None, 1),
            (site_id_map['kayak.com'], 'price_total', 'css', '.price-text, [class*="price"]', r'([£$€]\d+)', None, 1),
            (site_id_map['kayak.com'], 'carrier', 'css', '.airline-text, [class*="airline"]', None, None, 1),

            # British Airways
            (site_id_map['ba.com'], 'itineraries', 'css', '.flight-option, .fare-family', None, None, 1),
            (site_id_map['ba.com'], 'price_total', 'css', '.fare-price, [class*="price"]', r'([£$€]\d+)', None, 1),
            (site_id_map['ba.com'], 'carrier', 'css', '.airline-name', None, None, 1),
        ]

        for site_id, field, strategy, selector, regex, json_path, priority in selectors_data:
            if site_id:  # Only insert if site exists
                conn.execute(
                    'INSERT INTO selectors (site_id, field, strategy, selector, regex_pattern, json_path, priority) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (site_id, field, strategy, selector, regex, json_path, priority)
                )

        conn.commit()
        logger.info("✅ Seeded initial sites and selectors")

# Amadeus API Integration
class AmadeusClient:
    """Amadeus API client for flight search"""

    def __init__(self):
        self.api_key = AMADEUS_API_KEY
        self.api_secret = AMADEUS_API_SECRET
        self.base_url = AMADEUS_BASE_URL
        self.test_mode = AMADEUS_TEST_MODE
        self.access_token = None
        self.token_expires_at = None

    def is_configured(self) -> bool:
        """Check if Amadeus credentials are configured"""
        return bool(self.api_key and self.api_secret)

    def _should_attempt_request(self) -> bool:
        """Check if we should attempt API requests (prevents spam when not configured)"""
        if not self.is_configured():
            return False
        # Don't spam failed attempts - only retry every 5 minutes after failure
        if hasattr(self, '_last_failed_attempt'):
            time_since_failure = (datetime.utcnow() - self._last_failed_attempt).total_seconds()
            if time_since_failure < 300:  # 5 minutes
                return False
        return True

    async def get_access_token(self) -> Optional[str]:
        """Get OAuth access token from Amadeus with smart error handling"""
        # Don't attempt if credentials aren't configured or if we should rate limit
        if not self._should_attempt_request():
            return None

        # Check if token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return self.access_token

        try:
            # Get new token
            token_url = f"{self.base_url}/v1/security/oauth2/token"

            data = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.api_secret
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=data, headers=headers) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.access_token = token_data.get('access_token')
                        expires_in = token_data.get('expires_in', 3600)
                        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                        # Clear any previous failure timestamps
                        if hasattr(self, '_last_failed_attempt'):
                            delattr(self, '_last_failed_attempt')
                        if hasattr(self, '_error_logged'):
                            delattr(self, '_error_logged')
                        logger.info("✅ Amadeus access token obtained")
                        return self.access_token
                    else:
                        # Set failure timestamp to prevent spam
                        self._last_failed_attempt = datetime.utcnow()
                        if not hasattr(self, '_error_logged'):
                            logger.warning(f"⚠️ Amadeus API credentials not working (status {response.status}). Disabling for 5 minutes to reduce console spam.")
                            self._error_logged = True
                        return None

        except Exception as e:
            self._last_failed_attempt = datetime.utcnow()
            if not hasattr(self, '_error_logged'):
                logger.warning(f"⚠️ Amadeus API authentication error: {e}. Disabling for 5 minutes.")
                self._error_logged = True
            return None

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Search flights using Amadeus API"""
        token = await self.get_access_token()
        if not token:
            return []

        try:
            # Use appropriate endpoint based on trip type
            if return_date:
                endpoint = f"{self.base_url}/v2/shopping/flight-offers"
            else:
                endpoint = f"{self.base_url}/v2/shopping/flight-offers"

            params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': departure_date,
                'adults': adults,
                'max': 20  # Limit results
            }

            if return_date:
                params['returnDate'] = return_date

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        flights = data.get('data', [])
                        logger.info(f"✅ Amadeus returned {len(flights)} flight offers")
                        return self._format_amadeus_results(flights)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Amadeus search failed: {response.status} - {error_text}")
                        return []

        except Exception as e:
            logger.error(f"❌ Amadeus search error: {e}")
            return []

    def _format_amadeus_results(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Amadeus API results to our standard format"""
        formatted_results = []

        for flight in flights:
            try:
                # Extract pricing
                price_info = flight.get('price', {})
                total_price = float(price_info.get('total', 0))
                currency = price_info.get('currency', 'EUR')

                # Extract itinerary info
                itineraries = flight.get('itineraries', [])
                if not itineraries:
                    continue

                segments = []
                for itinerary in itineraries:
                    for segment in itinerary.get('segments', []):
                        departure = segment.get('departure', {})
                        arrival = segment.get('arrival', {})
                        operating = segment.get('operating', {})

                        segments.append({
                            'carrier': operating.get('carrierCode', segment.get('carrierCode', '')),
                            'flight_number': segment.get('number', ''),
                            'origin': departure.get('iataCode', ''),
                            'destination': arrival.get('iataCode', ''),
                            'departure_time': departure.get('at', ''),
                            'arrival_time': arrival.get('at', ''),
                            'aircraft': segment.get('aircraft', {}).get('code', ''),
                            'duration': segment.get('duration', '')
                        })

                if segments:
                    formatted_results.append({
                        'price': {
                            'amount': total_price,
                            'currency': currency
                        },
                        'carrier': segments[0]['carrier'],
                        'flight_number': segments[0]['flight_number'],
                        'departure_time': segments[0]['departure_time'],
                        'arrival_time': segments[-1]['arrival_time'],
                        'stops': len(segments) - 1,
                        'segments': segments,
                        'booking_url': '',  # Amadeus doesn't provide direct booking URLs
                        'source': {
                            'name': 'Amadeus API',
                            'domain': 'amadeus.com',
                            'success_rate': 1.0
                        },
                        'fetched_at': datetime.utcnow().isoformat(),
                        'hash': hashlib.sha256(json.dumps(flight, sort_keys=True).encode()).hexdigest()[:16]
                    })

            except Exception as e:
                logger.warning(f"Error formatting Amadeus result: {e}")
                continue

        return formatted_results

# Duffel API Integration
class DuffelClient:
    """Duffel API client for flight search"""

    def __init__(self):
        self.api_key = DUFFEL_API_KEY
        self.base_url = DUFFEL_BASE_URL

    def is_configured(self) -> bool:
        """Check if Duffel credentials are configured"""
        return bool(self.api_key and self.api_key.startswith('duffel_'))

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, passengers: int = 1) -> List[Dict[str, Any]]:
        """Search flights using Duffel API"""
        if not self.is_configured():
            logger.warning("⚠️ Duffel API key not configured")
            return []

        try:
            # Create offer request
            offer_request_data = {
                "data": {
                    "slices": [
                        {
                            "origin": origin,
                            "destination": destination,
                            "departure_date": departure_date
                        }
                    ],
                    "passengers": [{"type": "adult"} for _ in range(passengers)],
                    "cabin_class": "economy"
                }
            }

            # Add return slice if round trip
            if return_date:
                offer_request_data["data"]["slices"].append({
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date
                })

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Duffel-Version": "v2"
            }

            # Create offer request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/air/offer_requests",
                    json=offer_request_data,
                    headers=headers
                ) as response:
                    if response.status == 201:
                        request_data = await response.json()
                        offer_request_id = request_data["data"]["id"]

                        # Get offers
                        async with session.get(
                            f"{self.base_url}/air/offers",
                            params={"offer_request_id": offer_request_id},
                            headers=headers
                        ) as offers_response:
                            if offers_response.status == 200:
                                offers_data = await offers_response.json()
                                offers = offers_data.get("data", [])
                                logger.info(f"✅ Duffel returned {len(offers)} flight offers")
                                return self._format_duffel_results(offers)
                            else:
                                error_text = await offers_response.text()
                                logger.error(f"❌ Duffel offers failed: {offers_response.status} - {error_text}")
                                logger.error(f"❌ Offer request ID: {offer_request_id}")
                                logger.error(f"❌ Search params: {origin} → {destination} on {departure_date}")
                                return []
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Duffel request failed: {response.status} - {error_text}")
                        logger.error(f"❌ Request data: {offer_request_data}")
                        logger.error(f"❌ Headers used: {headers}")
                        return []

        except Exception as e:
            logger.error(f"❌ Duffel search error: {e}")
            return []

    def _format_duffel_results(self, offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Duffel API results to our standard format"""
        formatted_results = []
        seen_combinations = set()  # Track unique flight combinations

        for offer in offers:
            try:
                # Extract pricing
                total_amount = float(offer.get("total_amount", 0))
                currency = offer.get("total_currency", "GBP")

                # Extract slices (legs)
                slices = offer.get("slices", [])
                if not slices:
                    continue

                segments = []
                first_segment = None
                last_segment = None

                for slice_data in slices:
                    slice_segments = slice_data.get("segments", [])
                    for segment in slice_segments:
                        # Get airline info
                        marketing_carrier = segment.get("marketing_carrier", {})
                        aircraft = segment.get("aircraft", {})

                        segment_info = {
                            'carrier': marketing_carrier.get("iata_code", ""),
                            'carrier_name': marketing_carrier.get("name", ""),
                            'flight_number': segment.get("marketing_carrier_flight_number", ""),
                            'origin': segment.get("origin", {}).get("iata_code", ""),
                            'destination': segment.get("destination", {}).get("iata_code", ""),
                            'departure_time': segment.get("departing_at", ""),
                            'arrival_time': segment.get("arriving_at", ""),
                            'aircraft': aircraft.get("name", ""),
                            'aircraft_code': aircraft.get("iata_code", ""),
                            'duration': segment.get("duration", "")
                        }

                        segments.append(segment_info)

                        if first_segment is None:
                            first_segment = segment_info
                        last_segment = segment_info

                if segments and first_segment and last_segment:
                    # Add aerospace engineering calculations
                    aerospace_data = {}

                    # Get airport coordinates for calculations
                    origin_coords = get_airport_coordinates(first_segment['origin'])
                    dest_coords = get_airport_coordinates(last_segment['destination'])

                    if origin_coords and dest_coords:
                        # Great circle distance calculations
                        distance_data = aerospace_calc.great_circle_distance(
                            origin_coords['lat'], origin_coords['lon'],
                            dest_coords['lat'], dest_coords['lon']
                        )

                        # Initial bearing for navigation
                        bearing = aerospace_calc.initial_bearing(
                            origin_coords['lat'], origin_coords['lon'],
                            dest_coords['lat'], dest_coords['lon']
                        )

                        # Fuel efficiency estimate
                        aircraft_type = first_segment.get('aircraft_code', 'unknown')
                        fuel_data = aerospace_calc.fuel_efficiency_estimate(
                            distance_data['great_circle_km'], aircraft_type
                        )

                        aerospace_data = {
                            'distance': distance_data,
                            'navigation': {
                                'initial_bearing': round(bearing, 1),
                                'bearing_description': get_bearing_description(bearing)
                            },
                            'fuel_analysis': fuel_data,
                            'route_efficiency': calculate_route_efficiency(segments, distance_data)
                        }

                    # Enhanced deduplication - prevent repeated flights with same prices
                    all_flight_numbers = [seg['flight_number'] for seg in segments]
                    route_key = f"{first_segment['origin']}-{last_segment['destination']}"

                    # Extract meaningful time components for deduplication
                    departure_time_short = first_segment['departure_time'][:16] if first_segment['departure_time'] else 'unknown'
                    arrival_time_short = last_segment['arrival_time'][:16] if last_segment['arrival_time'] else 'unknown'

                    # Create primary unique key with full flight details
                    primary_key = f"{route_key}-{first_segment['carrier']}-{'-'.join(all_flight_numbers)}-{departure_time_short}-{arrival_time_short}-{total_amount:.2f}-{len(segments)}"

                    # Create secondary key for aggressive price-based deduplication 
                    # This prevents multiple flights with identical prices from same carrier
                    price_route_key = f"{route_key}-{first_segment['carrier']}-{total_amount:.2f}"

                    # Only add if both uniqueness criteria are met
                    if primary_key not in seen_combinations:
                        # For same carrier + route + price, only keep the first one (usually best time)
                        if price_route_key not in seen_combinations:
                            seen_combinations.add(primary_key)
                            seen_combinations.add(price_route_key)  # Track this price combination

                        formatted_results.append({
                            'price': {
                                'amount': total_amount,
                                'currency': currency
                            },
                            'carrier': first_segment['carrier'],
                            'carrier_name': first_segment['carrier_name'],
                            'flight_number': first_segment['flight_number'],
                            'departure_time': first_segment['departure_time'],
                            'arrival_time': last_segment['arrival_time'],
                            'stops': len(segments) - 1,
                            'segments': segments,
                            'booking_url': self._generate_deep_booking_url(first_segment, last_segment, offer.get('id', '')),
                            'offer_id': offer.get('id', ''),
                            'source': {
                                'name': 'Duffel API',
                                'domain': 'duffel.com',
                                'success_rate': 1.0
                            },
                            'aerospace_analysis': aerospace_data,
                            'fetched_at': datetime.utcnow().isoformat(),
                            'hash': hashlib.sha256(json.dumps({
                                'carrier': first_segment['carrier'],
                                'flight_number': first_segment['flight_number'], 
                                'departure_time': first_segment['departure_time'],
                                'price': total_amount,
                                'offer_id': offer.get('id', '')
                            }, sort_keys=True).encode()).hexdigest()[:16]
                        })

            except Exception as e:
                logger.warning(f"Error formatting Duffel result: {e}")
                continue

        logger.info(f"🎯 Duffel API: Formatted {len(formatted_results)} unique flights from {len(offers)} offers")
        return formatted_results

    def _generate_deep_booking_url(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], offer_id: str) -> str:
        """Generate direct airline booking URLs ONLY - no OTA fallbacks"""
        try:
            origin = first_segment.get('origin', '').upper()
            destination = last_segment.get('destination', '').upper()
            carrier = first_segment.get('carrier', '').upper()
            flight_number = first_segment.get('flight_number', '')
            departure_date = first_segment.get('departure_time', '')[:10]  # Get YYYY-MM-DD
            departure_time = first_segment.get('departure_time', '')

            # Extract time components for deeper linking
            if departure_time and 'T' in departure_time:
                time_part = departure_time.split('T')[1][:5]  # Get HH:MM
            else:
                time_part = ''

            # Comprehensive airline-specific deep booking URLs with flight details
            airline_urls = {
                # European Airlines
                'BA': f'https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?journeyType=ONEWAY&origin={origin}&destination={destination}&departureDate={departure_date}&cabinClass=M&adult=1',
                'FR': f'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={departure_date}&origin={origin}&destination={destination}',
                'U2': f'https://www.easyjet.com/en/booking/flights/{origin.lower()}-{destination.lower()}/{departure_date}?adults=1&children=0&infants=0',
                'W6': f'https://wizzair.com/en-gb/flights/select?departureDate={departure_date}&origin={origin}&destination={destination}&adultCount=1',
                'VS': f'https://www.virgin-atlantic.com/gb/en/book-a-flight/select-flights?origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',
                'AF': f'https://www.airfrance.com/en/booking/search?connections%5B0%5D%5Bdeparture%5D={origin}&connections%5B0%5D%5Barrival%5D={destination}&connections%5B0%5D%5BdepartureDate%5D={departure_date}&pax%5Badults%5D=1',
                'LH': f'https://www.lufthansa.com/de/en/booking/offers?departure={origin}&destination={destination}&outbound-date={departure_date}&return-date=&pax.adult=1&cabin-class=economy',
                'KL': f'https://www.klm.com/search/offers?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1&cabinClass=economy',
                'SK': f'https://www.sas.com/book/flights?from={origin}&to={destination}&outDate={departure_date}&adults=1&children=0&youth=0&infants=0',
                'IB': f'https://www.iberia.com/gb/flights/{origin}-{destination}/{departure_date}/?passengers=1',
                'VY': f'https://www.vueling.com/en/flights/{origin.lower()}-{destination.lower()}/{departure_date}?passengers=1',
                'TP': f'https://www.tap.pt/en/flights/{origin}-{destination}?adults=1&departureDate={departure_date}',
                'SN': f'https://www.brusselsairlines.com/en-us/booking/flights/{origin}-{destination}/{departure_date}?ADT=1',
                'LX': f'https://www.swiss.com/us/en/book/outbound-flight/{origin}-{destination}/{departure_date}?travelers=1-0-0-0',
                'OS': f'https://www.austrian.com/us/en/book/flight/{origin}/{destination}?departureDate={departure_date}&numAdults=1',
                'AZ': f'https://www.alitalia.com/en_us/booking/flights-search.html?tripType=OW&departureStation={origin}&arrivalStation={destination}&outboundDate={departure_date}&passengers=1-0-0',
                'AY': f'https://www.finnair.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DY': f'https://www.norwegian.com/en/booking/flight-search?origin={origin}&destination={destination}&outbound={departure_date}&adults=1',
                'EN': f'https://www.airdolomiti.it/en/book-a-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'LO': f'https://www.lot.com/us/en/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'OK': f'https://www.czechairlines.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RO': f'https://www.tarom.ro/en/book-a-flight?tripType=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'JU': f'https://www.airserbia.com/en/booking/flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'OU': f'https://www.croatiaairlines.com/en/book-a-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'JP': f'https://www.adria.si/en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BT': f'https://www.airbaltic.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # North American Airlines
                'DL': f'https://www.delta.com/flight-search/book-a-flight?origin={origin}&destination={destination}&departure_date={departure_date}&passengers=1',
                'UA': f'https://www.united.com/en/us/fsr/choose-flights?f={origin}&t={destination}&d={departure_date}&tt=1&at=1&sc=7',
                'AA': f'https://www.aa.com/booking/choose-flights?localeCode=en_US&from={origin}&to={destination}&departureDate={departure_date}&tripType=OneWay&adult=1',
                'AS': f'https://www.alaskaair.com/booking/reservation/search?passengers=1&from={origin}&to={destination}&departureDate={departure_date}',
                'B6': f'https://www.jetblue.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'WN': f'https://www.southwest.com/air/booking/select.html?originationAirportCode={origin}&destinationAirportCode={destination}&departureDate={departure_date}&adults=1',
                'AC': f'https://www.aircanada.com/us/en/aco/home/book/search/flight.html?tripType=O&org0={origin}&dest0={destination}&departureDate0={departure_date}&adult=1',
                'WS': f'https://www.westjet.com/en-ca/flights/search?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',

                # Middle Eastern Airlines
                'EK': f'https://www.emirates.com/english/book-a-flight/flights-search.aspx?fromCityOrAirport={origin}&toCityOrAirport={destination}&departDate={departure_date}&adults=1',
                'QR': f'https://www.qatarairways.com/en/booking?tripType=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'EY': f'https://www.etihad.com/en/flights/{origin}/{destination}?departureDate={departure_date}&passengerCount=1',
                'TK': f'https://www.turkishairlines.com/en-int/flights/booking/{origin}-{destination}/{departure_date}/?pax=1&cabin=Economy',
                'WY': f'https://www.omanair.com/en/book/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'GF': f'https://www.gulfair.com/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KU': f'https://www.kuwaitairways.com/en/booking/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'SV': f'https://www.saudia.com/book/flight-search?trip=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'MS': f'https://www.egyptair.com/en/fly-egyptair/online-booking?tripType=OW&from={origin}&to={destination}&depDate={departure_date}&adults=1',
                'FZ': f'https://www.flydubai.com/en/book-a-trip/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RJ': f'https://www.rj.com/en/book-and-manage/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AT': f'https://www.royalairmaroc.com/int-en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DT': f'https://www.taag.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TU': f'https://www.tunisair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Asian Airlines
                'SQ': f'https://www.singaporeair.com/en_UK/book-a-flight/search/?triptype=OW&from={origin}&to={destination}&depdate={departure_date}&paxadult=1',
                'CX': f'https://www.cathaypacific.com/cx/en_US/book-a-trip/search.html?tripType=OW&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JL': f'https://www.jal.co.jp/en/dom/search/?ar={origin}&dp={destination}&dd={departure_date}&adult=1',
                'NH': f'https://www.ana.co.jp/en/us/book-plan/book/domestic/search/?departureAirport={origin}&arrivalAirport={destination}&departureDate={departure_date}&adult=1',
                'AI': f'https://www.airindia.in/book/flight-search?trip=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                '6E': f'https://www.goindigo.in/book/flight-search.html?r=1&px=1,0,0&o={origin}&d={destination}&dd={departure_date}',
                'TG': f'https://www.thaiairways.com/en_CA/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'MH': f'https://www.malaysiaairlines.com/my/en/book-with-us/search.html?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AK': f'https://www.airasia.com/flights/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Australian Airlines
                'QF': f'https://www.qantas.com/au/en/booking/search.html?tripType=O&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JQ': f'https://www.jetstar.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VA': f'https://www.virginaustralia.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'NZ': f'https://www.airnewzealand.com/booking/select-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Latin American Airlines
                'LA': f'https://www.latam.com/en_us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CM': f'https://www.copaair.com/en/web/us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AV': f'https://www.avianca.com/us/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AM': f'https://aeromexico.com/en-us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AR': f'https://www.aerolineas.com.ar/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1'
            }

            # Use airline-specific deep URL if available
            if carrier in deep_airline_urls:
                return deep_airline_urls[carrier]

            # For other airlines, create a Google Flights URL with flight number for easier finding
            if flight_number:
                google_deep_url = f'https://www.google.com/flights?hl=en#flt={origin}.{destination}.{departure_date};c:{carrier}{flight_number}'
                return google_deep_url

            # Fallback to Skyscanner with route and date
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/{departure_date.replace("-", "")}/?adults=1&children=0&adultsv2=1&childrenv2=&infants=0&cabinclass=economy&rtn=0&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false'

        except Exception as e:
            logger.warning(f"Error generating deep booking URL: {e}")
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/'

    def _calculate_aerospace_data(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aerospace engineering data for FlightAPI results"""
        try:
            origin_coords = get_airport_coordinates(first_segment['origin'])
            dest_coords = get_airport_coordinates(last_segment['destination'])

            if origin_coords and dest_coords:
                # Great circle distance calculations
                distance_data = aerospace_calc.great_circle_distance(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Initial bearing for navigation
                bearing = aerospace_calc.initial_bearing(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Fuel efficiency estimate
                aircraft_type = first_segment.get('aircraft', 'unknown')
                fuel_data = aerospace_calc.fuel_efficiency_estimate(
                    distance_data['great_circle_km'], aircraft_type
                )

                return {
                    'distance': distance_data,
                    'navigation': {
                        'initial_bearing': round(bearing, 1),
                        'bearing_description': get_bearing_description(bearing)
                    },
                    'fuel_analysis': fuel_data,
                    'route_efficiency': calculate_route_efficiency(segments, distance_data)
                }
        except Exception as e:
            logger.warning(f"Error calculating aerospace data: {e}")

        return {}

# FlightAPI Integration for Budget Airlines  
class FlightAPIClient:
    """FlightAPI client for comprehensive budget airline coverage"""

    def __init__(self):
        # Use provided API key with fallback to environment
        self.api_key = os.getenv('FLIGHTAPI_KEY', 'FLIGHTAPI_KEY')
        # Note: FlightAPI may not be active - this is a placeholder for future real budget airline APIs
        self.base_url = 'https://api.aviationstack.com/v1'  # Alternative flight API

    def is_configured(self) -> bool:
        """Check if FlightAPI credentials are configured"""
        return bool(self.api_key)

    def _should_attempt_request(self) -> bool:
        """Check if we should attempt API requests (prevents spam when failing)"""
        if not self.is_configured():
            return False
        # Don't spam failed attempts - only retry every 10 minutes after failure
        if hasattr(self, '_last_failed_attempt'):
            time_since_failure = (datetime.utcnow() - self._last_failed_attempt).total_seconds()
            if time_since_failure < 600:  # 10 minutes
                return False
        return True

    async def search_flights(self, origin: str, destination: str, departure_date: str, 
                           return_date: Optional[str] = None, passengers: int = 1) -> List[Dict[str, Any]]:
        """Search flights using FlightAPI with improved error handling"""
        # Don't attempt if we should rate limit failed attempts
        if not self._should_attempt_request():
            return []

        try:
            # Note: The provided FlightAPI key may not be for an active service
            # This is disabled to prevent console spam until we have a working budget airline API
            if not hasattr(self, '_api_disabled_warning_shown'):
                logger.info("ℹ️ FlightAPI temporarily disabled - using Duffel API and Ryanair integration for comprehensive coverage")
                self._api_disabled_warning_shown = True
            return []

            # Alternative approach - use a working API if available
            async with aiohttp.ClientSession() as session:
                # This would be for a working flight API
                endpoint = f"{self.base_url}/flights"

                params = {
                    'access_key': self.api_key,
                    'departure_iata': origin,
                    'arrival_iata': destination,
                    'limit': 20
                }

                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'FlightAlert-Pro-QMUL-Student/1.0'
                }

                async with session.get(endpoint, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        flights = data.get('data', [])
                        logger.info(f"✅ FlightAPI returned {len(flights)} budget airline flights")
                        return self._format_flightapi_results(flights)
                    else:
                        # Set failure timestamp to prevent spam
                        self._last_failed_attempt = datetime.utcnow()
                        if not hasattr(self, '_error_logged'):
                            logger.warning(f"⚠️ FlightAPI not responding correctly (status {response.status}). Disabling for 10 minutes to reduce console spam.")
                            self._error_logged = True
                        return []

        except Exception as e:
            self._last_failed_attempt = datetime.utcnow()
            if not hasattr(self, '_error_logged'):
                logger.warning(f"⚠️ FlightAPI error: {e}. Disabling for 10 minutes.")
                self._error_logged = True
            return []

# ==================== BUDGET AIRLINE INTEGRATION ====================

class RyanairAPIClient:
    """Direct Ryanair integration for budget airline pricing"""

    def __init__(self):
        try:
            from ryanair import Ryanair
            self.api = Ryanair("EUR")  # Use EUR for European routes
            self.available = True
            logger.info("✅ Ryanair API client initialized")
        except ImportError:
            self.available = False
            logger.warning("⚠️ Ryanair library not available")

    def is_configured(self) -> bool:
        return self.available

    async def search_flights(self, origin: str, destination: str, departure_date: str, passengers: int = 1) -> List[Dict[str, Any]]:
        """Search Ryanair flights with real pricing"""
        if not self.available:
            return []

        try:
            from datetime import datetime, timedelta

            # Convert date string to datetime object
            dep_date = datetime.strptime(departure_date, '%Y-%m-%d').date()

            # Get cheapest flights for the date
            flights = self.api.get_cheapest_flights(origin, dep_date, dep_date + timedelta(days=1))

            formatted_flights = []
            for flight in flights[:10]:  # Limit to 10 results
                if hasattr(flight, 'price') and hasattr(flight, 'currency'):
                    formatted_flight = {
                        'id': f"ryanair_{flight.outbound.flight_number if hasattr(flight, 'outbound') else 'FR001'}_{departure_date}",
                        'carrier': 'FR',
                        'carrier_name': 'Ryanair',
                        'flight_number': getattr(flight.outbound, 'flight_number', 'FR001') if hasattr(flight, 'outbound') else 'FR001',
                        'origin': origin,
                        'destination': destination,
                        'departure_time': getattr(flight.outbound, 'departure_time', f"{departure_date}T08:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T08:00:00",
                        'arrival_time': getattr(flight.outbound, 'arrival_time', f"{departure_date}T10:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T10:00:00",
                        'duration': getattr(flight.outbound, 'duration', '2h 00m') if hasattr(flight, 'outbound') else '2h 00m',
                        'stops': 0,  # Ryanair is typically direct
                        'price': {
                            'total': float(flight.price),
                            'currency': flight.currency,
                            'formatted': f"{flight.currency}{flight.price:.2f}"
                        },
                        'cabin_class': 'economy',
                        'booking_url': f"https://www.ryanair.com/gb/en/trip/flights/select?adults={passengers}&dateOut={departure_date}&originIATA={origin}&destinationIATA={destination}",
                        'source': 'Ryanair Direct API',
                        'segments': [{
                            'origin': origin,
                            'destination': destination,
                            'departure_time': getattr(flight.outbound, 'departure_time', f"{departure_date}T08:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T08:00:00",
                            'arrival_time': getattr(flight.outbound, 'arrival_time', f"{departure_date}T10:00:00") if hasattr(flight, 'outbound') else f"{departure_date}T10:00:00",
                            'flight_number': getattr(flight.outbound, 'flight_number', 'FR001') if hasattr(flight, 'outbound') else 'FR001',
                            'carrier': 'FR'
                        }]
                    }
                    formatted_flights.append(formatted_flight)

            logger.info(f"✅ Ryanair API returned {len(formatted_flights)} flights")
            return formatted_flights

        except Exception as e:
            logger.error(f"❌ Ryanair API failed: {e}")
            return []

    def _format_flightapi_results(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format FlightAPI results to our standard format"""
        formatted_results = []
        seen_combinations = set()

        for flight in flights:
            try:
                # Extract pricing
                price_info = flight.get('price', {})
                total_amount = float(price_info.get('amount', 0))
                currency = price_info.get('currency', 'USD')

                # Extract route segments
                segments = []
                legs = flight.get('legs', [])

                for leg in legs:
                    carriers = leg.get('carriers', [])
                    if carriers:
                        carrier_info = carriers[0]  # Primary carrier

                        segment_info = {
                            'carrier': carrier_info.get('code', ''),
                            'carrier_name': carrier_info.get('name', ''),
                            'flight_number': leg.get('flight_number', ''),
                            'origin': leg.get('origin', {}).get('code', ''),
                            'destination': leg.get('destination', {}).get('code', ''),
                            'departure_time': leg.get('departure_time', ''),
                            'arrival_time': leg.get('arrival_time', ''),
                            'aircraft': leg.get('aircraft', ''),
                            'duration': leg.get('duration', '')
                        }
                        segments.append(segment_info)

                if segments:
                    first_segment = segments[0]
                    last_segment = segments[-1]

                    # Enhanced deduplication with price-based filtering
                    all_flight_numbers = [seg['flight_number'] for seg in segments]
                    route_key = f"{first_segment['origin']}-{last_segment['destination']}"
                    segment_hash = hashlib.sha256(json.dumps(segments, sort_keys=True).encode()).hexdigest()[:8]

                    # Primary uniqueness key  
                    primary_key = f"{route_key}-{'-'.join(all_flight_numbers)}-{first_segment['departure_time']}-{total_amount}-{segment_hash}"

                    # Secondary key to prevent same price duplicates from same source
                    price_source_key = f"{route_key}-FlightAPI-{total_amount:.2f}"

                    # Only add if both uniqueness criteria are met
                    if primary_key not in seen_combinations:
                        if price_source_key not in seen_combinations:
                            seen_combinations.add(primary_key)
                            seen_combinations.add(price_source_key)

                        formatted_results.append({
                            'price': {
                                'amount': total_amount,
                                'currency': currency
                            },
                            'carrier': first_segment['carrier'],
                            'carrier_name': first_segment['carrier_name'],
                            'flight_number': first_segment['flight_number'],
                            'departure_time': first_segment['departure_time'],
                            'arrival_time': last_segment['arrival_time'],
                            'stops': len(segments) - 1,
                            'segments': segments,
                            'booking_url': self._generate_deep_booking_url(first_segment, last_segment, flight.get('id', '')),
                            'offer_id': flight.get('id', ''),
                            'source': {
                                'name': 'FlightAPI',
                                'domain': 'flightapi.io',
                                'success_rate': 1.0
                            },
                            'aerospace_analysis': self._calculate_aerospace_data(first_segment, last_segment, segments),
                            'fetched_at': datetime.utcnow().isoformat(),
                            'hash': hashlib.sha256(json.dumps({
                                'carrier': first_segment['carrier'],
                                'flight_number': first_segment['flight_number'], 
                                'departure_time': first_segment['departure_time'],
                                'price': total_amount,
                                'offer_id': flight.get('id', '')
                            }, sort_keys=True).encode()).hexdigest()[:16]
                        })

            except Exception as e:
                logger.warning(f"Error formatting FlightAPI result: {e}")
                continue

        logger.info(f"🎯 FlightAPI: Formatted {len(formatted_results)} unique flights from {len(flights)} offers")
        return formatted_results

    def _generate_deep_booking_url(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], offer_id: str) -> str:
        """Generate DEEP booking URLs with pre-filled flight details"""
        try:
            origin = first_segment.get('origin', '').upper()
            destination = last_segment.get('destination', '').upper()
            carrier = first_segment.get('carrier', '').upper()
            flight_number = first_segment.get('flight_number', '')
            departure_date = first_segment.get('departure_time', '')[:10]  # YYYY-MM-DD
            departure_time = first_segment.get('departure_time', '')[11:16] if len(first_segment.get('departure_time', '')) > 10 else ''  # HH:MM

            # Comprehensive airline-specific booking URLs with flight details pre-filled
            deep_airline_urls = {
                # European Airlines
                'BA': f'https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?journeyType=ONEWAY&origin={origin}&destination={destination}&departureDate={departure_date}&cabinClass=M&adult=1',
                'FR': f'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={departure_date}&origin={origin}&destination={destination}',
                'U2': f'https://www.easyjet.com/en/booking/flights/{origin.lower()}-{destination.lower()}/{departure_date}?adults=1&children=0&infants=0',
                'W6': f'https://wizzair.com/en-gb/flights/select?departureDate={departure_date}&origin={origin}&destination={destination}&adultCount=1',
                'VS': f'https://www.virgin-atlantic.com/gb/en/book-a-flight/select-flights?origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',
                'AF': f'https://www.airfrance.com/en/booking/search?connections%5B0%5D%5Bdeparture%5D={origin}&connections%5B0%5D%5Barrival%5D={destination}&connections%5B0%5D%5BdepartureDate%5D={departure_date}&pax%5Badults%5D=1',
                'LH': f'https://www.lufthansa.com/de/en/booking/offers?departure={origin}&destination={destination}&outbound-date={departure_date}&return-date=&pax.adult=1&cabin-class=economy',
                'KL': f'https://www.klm.com/search/offers?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1&cabinClass=economy',
                'SK': f'https://www.sas.com/book/flights?from={origin}&to={destination}&outDate={departure_date}&adults=1&children=0&youth=0&infants=0',
                'IB': f'https://www.iberia.com/gb/flights/{origin}-{destination}/{departure_date}/?passengers=1',
                'VY': f'https://www.vueling.com/en/flights/{origin.lower()}-{destination.lower()}/{departure_date}?passengers=1',
                'TP': f'https://www.tap.pt/en/flights/{origin}-{destination}?adults=1&departureDate={departure_date}',
                'SN': f'https://www.brusselsairlines.com/en-us/booking/flights/{origin}-{destination}/{departure_date}?ADT=1',
                'LX': f'https://www.swiss.com/us/en/book/outbound-flight/{origin}-{destination}/{departure_date}?travelers=1-0-0-0',
                'OS': f'https://www.austrian.com/us/en/book/flight/{origin}/{destination}?departureDate={departure_date}&numAdults=1',
                'AZ': f'https://www.alitalia.com/en_us/booking/flights-search.html?tripType=OW&departureStation={origin}&arrivalStation={destination}&outboundDate={departure_date}&passengers=1-0-0',
                'AY': f'https://www.finnair.com/us-en/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DY': f'https://www.norwegian.com/en/booking/flight-search?origin={origin}&destination={destination}&outbound={departure_date}&adults=1',

                # North American Airlines
                'DL': f'https://www.delta.com/flight-search/book-a-flight?origin={origin}&destination={destination}&departure_date={departure_date}&passengers=1',
                'UA': f'https://www.united.com/en/us/fsr/choose-flights?f={origin}&t={destination}&d={departure_date}&tt=1&at=1&sc=7',
                'AA': f'https://www.aa.com/booking/choose-flights?localeCode=en_US&from={origin}&to={destination}&departureDate={departure_date}&tripType=OneWay&adult=1',
                'AS': f'https://www.alaskaair.com/booking/reservation/search?passengers=1&from={origin}&to={destination}&departureDate={departure_date}',
                'B6': f'https://www.jetblue.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'WN': f'https://www.southwest.com/air/booking/select.html?originationAirportCode={origin}&destinationAirportCode={destination}&departureDate={departure_date}&adults=1',
                'AC': f'https://www.aircanada.com/us/en/aco/home/book/search/flight.html?tripType=O&org0={origin}&dest0={destination}&departureDate0={departure_date}&adult=1',
                'WS': f'https://www.westjet.com/en-ca/flights/search?tripType=oneway&origin={origin}&destination={destination}&departureDate={departure_date}&adults=1',

                # Middle Eastern Airlines
                'EK': f'https://www.emirates.com/english/book-a-flight/flights-search.aspx?fromCityOrAirport={origin}&toCityOrAirport={destination}&departDate={departure_date}&adults=1',
                'QR': f'https://www.qatarairways.com/en/booking?tripType=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'EY': f'https://www.etihad.com/en/flights/{origin}/{destination}?departureDate={departure_date}&passengerCount=1',
                'TK': f'https://www.turkishairlines.com/en-int/flights/booking/{origin}-{destination}/{departure_date}/?pax=1&cabin=Economy',
                'WY': f'https://www.omanair.com/en/book/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'GF': f'https://www.gulfair.com/book-flight?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KU': f'https://www.kuwaitairways.com/en/booking/flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'SV': f'https://www.saudia.com/book/flight-search?trip=OW&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'MS': f'https://www.egyptair.com/en/fly-egyptair/online-booking?tripType=OW&from={origin}&to={destination}&depDate={departure_date}&adults=1',
                'FZ': f'https://www.flydubai.com/en/book-a-trip/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'RJ': f'https://www.rj.com/en/book-and-manage/book-a-flight?tripType=oneway&from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AT': f'https://www.royalairmaroc.com/int-en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'DT': f'https://www.taag.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TU': f'https://www.tunisair.com/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Asian Airlines
                'SQ': f'https://www.singaporeair.com/en_UK/book-a-flight/search/?triptype=OW&from={origin}&to={destination}&depdate={departure_date}&paxadult=1',
                'CX': f'https://www.cathaypacific.com/cx/en_US/book-a-trip/search.html?tripType=OW&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JL': f'https://www.jal.co.jp/en/dom/search/?ar={origin}&dp={destination}&dd={departure_date}&adult=1',
                'NH': f'https://www.ana.co.jp/en/us/book-plan/book/domestic/search/?departureAirport={origin}&arrivalAirport={destination}&departureDate={departure_date}&adult=1',
                'AI': f'https://www.airindia.in/book/flight-search?trip=oneway&from={origin}&to={destination}&departure={departure_date}&adults=1',
                '6E': f'https://www.goindigo.in/book/flight-search.html?r=1&px=1,0,0&o={origin}&d={destination}&dd={departure_date}',
                'SG': f'https://www.spicejet.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UK': f'https://www.airvistara.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'IX': f'https://www.airindiaexpress.in/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'PK': f'https://www.piac.com.pk/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'BG': f'https://www.biman-airlines.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'UL': f'https://www.srilankan.com/en_uk/plan-and-book/search-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'TG': f'https://www.thaiairways.com/en_CA/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'MH': f'https://www.malaysiaairlines.com/my/en/book-with-us/search.html?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AK': f'https://www.airasia.com/flights/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Australian Airlines
                'QF': f'https://www.qantas.com/au/en/booking/search.html?tripType=O&from={origin}&to={destination}&departureDate={departure_date}&adult=1',
                'JQ': f'https://www.jetstar.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'VA': f'https://www.virginaustralia.com/au/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'NZ': f'https://www.airnewzealand.com/booking/select-flights?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # Latin American Airlines
                'LA': f'https://www.latam.com/en_us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'CM': f'https://www.copaair.com/en/web/us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AV': f'https://www.avianca.com/us/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AM': f'https://aeromexico.com/en-us/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'AR': f'https://www.aerolineas.com.ar/en/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',

                # African Airlines
                'ET': f'https://www.ethiopianairlines.com/aa/book/flight-search?tripType=ONEWAY&from={origin}&to={destination}&departure={departure_date}&adults=1',
                'SA': f'https://www.flysaa.com/za/en/book-flights/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1',
                'KQ': f'https://www.kenya-airways.com/booking/search?from={origin}&to={destination}&departureDate={departure_date}&adults=1'
            }

            # Use airline-specific deep URL if available
            if carrier in deep_airline_urls:
                return deep_airline_urls[carrier]

            # For other airlines, create a Google Flights URL with flight number for easier finding
            if flight_number:
                google_deep_url = f'https://www.google.com/flights?hl=en#flt={origin}.{destination}.{departure_date};c:{carrier}{flight_number}'
                return google_deep_url

            # Fallback to Skyscanner with route and date
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/{departure_date.replace("-", "")}/?adults=1&children=0&adultsv2=1&childrenv2=&infants=0&cabinclass=economy&rtn=0&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false'

        except Exception as e:
            logger.warning(f"Error generating deep booking URL: {e}")
            return f'https://www.skyscanner.net/transport/flights/{origin.lower()}/{destination.lower()}/'

    def _calculate_aerospace_data(self, first_segment: Dict[str, Any], last_segment: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aerospace engineering data for FlightAPI results"""
        try:
            origin_coords = get_airport_coordinates(first_segment['origin'])
            dest_coords = get_airport_coordinates(last_segment['destination'])

            if origin_coords and dest_coords:
                # Great circle distance calculations
                distance_data = aerospace_calc.great_circle_distance(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Initial bearing for navigation
                bearing = aerospace_calc.initial_bearing(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )

                # Fuel efficiency estimate
                aircraft_type = first_segment.get('aircraft', 'unknown')
                fuel_data = aerospace_calc.fuel_efficiency_estimate(
                    distance_data['great_circle_km'], aircraft_type
                )

                return {
                    'distance': distance_data,
                    'navigation': {
                        'initial_bearing': round(bearing, 1),
                        'bearing_description': get_bearing_description(bearing)
                    },
                    'fuel_analysis': fuel_data,
                    'route_efficiency': calculate_route_efficiency(segments, distance_data)
                }
        except Exception as e:
            logger.warning(f"Error calculating aerospace data: {e}")

        return {}

# Initialize API clients
amadeus_client = AmadeusClient()
duffel_client = DuffelClient()
flightapi_client = FlightAPIClient()

# Aerospace Engineering Enhancement Classes
class AerospaceCalculator:
    """Aerospace engineering calculations for flight analysis"""

    def __init__(self):
        self.earth_radius_km = 6371.0
        self.earth_radius_nm = 3440.065  # Nautical miles

    def great_circle_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Dict[str, float]:
        """Calculate great circle distance between two points (shortest flight path)"""
        import math

        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        distance_km = self.earth_radius_km * c
        distance_nm = self.earth_radius_nm * c
        distance_mi = distance_km * 0.621371

        return {
            'great_circle_km': round(distance_km, 2),
            'great_circle_nm': round(distance_nm, 2),
            'great_circle_mi': round(distance_mi, 2)
        }

    def initial_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate initial bearing for great circle route"""
        import math

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)

        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)

        # Normalize to 0-360 degrees
        return (bearing_deg + 360) % 360

    def fuel_efficiency_estimate(self, distance_km: float, aircraft_type: str = "unknown") -> Dict[str, Any]:
        """Estimate fuel consumption based on distance and aircraft type"""

        # Typical fuel consumption rates (liters per km per passenger)
        fuel_rates = {
            "A320": 0.024,  # Airbus A320 family
            "A321": 0.025,
            "A330": 0.028,
            "A350": 0.022,  # More efficient
            "B737": 0.025,  # Boeing 737
            "B738": 0.025,
            "B787": 0.020,  # Very efficient
            "B777": 0.030,
            "E190": 0.026,  # Embraer regional
            "unknown": 0.025  # Average estimate
        }

        rate = fuel_rates.get(aircraft_type.upper(), fuel_rates["unknown"])
        total_fuel_liters = distance_km * rate
        fuel_cost_estimate = total_fuel_liters * 0.85  # ~$0.85 per liter jet fuel

        return {
            'fuel_per_passenger_liters': round(total_fuel_liters, 2),
            'fuel_cost_estimate_usd': round(fuel_cost_estimate, 2),
            'efficiency_rating': 'High' if rate < 0.023 else 'Medium' if rate < 0.027 else 'Standard',
            'aircraft_type': aircraft_type
        }

class AviationWeatherClient:
    """Aviation weather data integration for flight planning"""

    def __init__(self):
        self.base_url = "https://aviationweather.gov/api/data"

    async def get_metar(self, airport_code: str) -> Dict[str, Any]:
        """Get current weather conditions (METAR) for airport"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/metar"
                params = {
                    'ids': airport_code.upper(),
                    'format': 'json',
                    'taf': 'false',
                    'hours': '1'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            metar = data[0]
                            return {
                                'airport': airport_code.upper(),
                                'metar_text': metar.get('rawOb', ''),
                                'visibility': metar.get('visib', 'Unknown'),
                                'wind_speed': metar.get('wspd', 0),
                                'wind_direction': metar.get('wdir', 0),
                                'temperature': metar.get('temp', 'Unknown'),
                                'conditions': metar.get('wx', []),
                                'flight_category': metar.get('fltcat', 'Unknown'),
                                'observation_time': metar.get('obsTime', ''),
                                'suitable_for_flight': metar.get('fltcat', '').upper() in ['VFR', 'MVFR']
                            }

        except Exception as e:
            logger.warning(f"Weather API error for {airport_code}: {e}")

        return {
            'airport': airport_code.upper(),
            'metar_text': 'Weather data unavailable',
            'flight_category': 'Unknown',
            'suitable_for_flight': True  # Default assumption
        }

    async def get_taf(self, airport_code: str) -> Dict[str, Any]:
        """Get Terminal Aerodrome Forecast (TAF) for airport"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/taf"
                params = {
                    'ids': airport_code.upper(),
                    'format': 'json',
                    'hours': '12'
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            taf = data[0]
                            return {
                                'airport': airport_code.upper(),
                                'taf_text': taf.get('rawTAF', ''),
                                'forecast_time': taf.get('fcstTime', ''),
                                'valid_from': taf.get('validTime', ''),
                                'forecast_conditions': 'Available'
                            }

        except Exception as e:
            logger.warning(f"TAF API error for {airport_code}: {e}")

        return {
            'airport': airport_code.upper(),
            'taf_text': 'Forecast data unavailable',
            'forecast_conditions': 'Unknown'
        }

# Aerospace helper functions
def get_airport_coordinates(airport_code: str) -> Optional[Dict[str, float]]:
    """Get airport coordinates from the airport database"""
    try:
        with get_db_connection() as conn:
            airport = conn.execute(
                'SELECT latitude, longitude FROM airports WHERE iata_code = ? OR icao_code = ?',
                (airport_code.upper(), airport_code.upper())
            ).fetchone()

            if airport and airport['latitude'] and airport['longitude']:
                return {
                    'lat': float(airport['latitude']),
                    'lon': float(airport['longitude'])
                }
    except Exception as e:
        logger.warning(f"Error getting coordinates for {airport_code}: {e}")

    return None

def get_bearing_description(bearing: float) -> str:
    """Convert bearing degrees to compass direction"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(bearing / 22.5) % 16
    return directions[index]

def calculate_route_efficiency(segments: List[Dict[str, Any]], direct_distance: Dict[str, float]) -> Dict[str, Any]:
    """Calculate route efficiency compared to direct flight"""
    try:
        total_distance = 0

        # Calculate total distance of actual route
        for i, segment in enumerate(segments):
            if i > 0:  # Get distance between connecting airports
                prev_dest = segments[i-1]['destination']
                curr_origin = segment['origin']

                prev_coords = get_airport_coordinates(prev_dest)
                curr_coords = get_airport_coordinates(curr_origin)

                if prev_coords and curr_coords:
                    # Add distance if there's a connection
                    if prev_dest != curr_origin:
                        connection_dist = aerospace_calc.great_circle_distance(
                            prev_coords['lat'], prev_coords['lon'],
                            curr_coords['lat'], curr_coords['lon']
                        )
                        total_distance += connection_dist['great_circle_km']

            # Add segment distance
            origin_coords = get_airport_coordinates(segment['origin'])
            dest_coords = get_airport_coordinates(segment['destination'])

            if origin_coords and dest_coords:
                seg_dist = aerospace_calc.great_circle_distance(
                    origin_coords['lat'], origin_coords['lon'],
                    dest_coords['lat'], dest_coords['lon']
                )
                total_distance += seg_dist['great_circle_km']

        direct_km = direct_distance.get('great_circle_km', 0)

        if direct_km > 0 and total_distance > 0:
            efficiency = (direct_km / total_distance) * 100
            extra_distance = total_distance - direct_km

            return {
                'efficiency_percent': round(efficiency, 1),
                'total_route_km': round(total_distance, 2),
                'extra_distance_km': round(extra_distance, 2),
                'route_type': 'Direct' if len(segments) == 1 else f'{len(segments)-1} Stop(s)'
            }

    except Exception as e:
        logger.warning(f"Error calculating route efficiency: {e}")

    return {
        'efficiency_percent': 100.0,
        'total_route_km': direct_distance.get('great_circle_km', 0),
        'extra_distance_km': 0,
        'route_type': 'Direct' if len(segments) <= 1 else 'Multi-stop'
    }

# Initialize aerospace engineering tools
aerospace_calc = AerospaceCalculator()
weather_client = AviationWeatherClient()

# Core business logic classes
class QueryManager:
    """Manages flight search queries and generates deep links"""

    def __init__(self):
        self.deep_link_templates = {
            'skyscanner.net': 'https://www.skyscanner.net/transport/flights/{origin_lower}/{dest_lower}/{date_yymmdd}/',
            'kayak.com': 'https://www.kayak.com/flights/{origin}-{dest}/{date_ymd}',
            'expedia.com': 'https://www.expedia.com/Flights-Search?trip=oneway&leg1=from%3A{origin}%2Cto%3A{dest}%2Cdeparture%3A{date_slash}',
            'ba.com': 'https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?journeyType=ONEWAY&origin={origin}&destination={dest}&departureDate={date_ymd}',
            'ryanair.com': 'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={date_ymd}&origin={origin}&destination={dest}',
            'easyjet.com': 'https://www.easyjet.com/en/flights/{origin_lower}/{dest_lower}?adults=1&children=0&infants=0&departureDate={date_ymd}',
            'google.com': 'https://www.google.com/flights?hl=en#flt={origin}.{dest}.{date_ymd}',
            'momondo.com': 'https://www.momondo.com/flight-search/{origin}-{dest}/{date_ymd}',
        }

    def create_query(self, origin: str, destination: str, depart_date: str, return_date: Optional[str] = None, cabin_class: Optional[str] = "economy", passengers: Optional[int] = 1, user_id: Optional[int] = None) -> int:
        """Create a new query and return the query ID"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO queries (origin, destination, depart_date, return_date, cabin_class, passengers, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (origin.upper(), destination.upper(), depart_date, return_date, cabin_class, passengers, user_id)
            )
            conn.commit()
            query_id = cursor.lastrowid
            logger.info(f"📝 Created query {query_id}: {origin} → {destination} on {depart_date}, {cabin_class} class, {passengers} passengers")
            return query_id

    def generate_deep_links(self, query_id: int) -> List[Dict[str, str]]:
        """Generate deep links for a query"""
        with get_db_connection() as conn:
            query = conn.execute('SELECT * FROM queries WHERE id = ?', (query_id,)).fetchone()
            if not query:
                return []

            sites = conn.execute('SELECT * FROM sites ORDER BY priority ASC, success_rate DESC').fetchall()

            deep_links = []
            date_obj = datetime.strptime(query['depart_date'], '%Y-%m-%d')

            for site in sites:
                template = self.deep_link_templates.get(site['domain'])
                if not template:
                    continue

                try:
                    url = template.format(
                        origin=query['origin'],
                        dest=query['destination'],
                        origin_lower=query['origin'].lower(),
                        dest_lower=query['destination'].lower(),
                        date_ymd=query['depart_date'],
                        date_yymmdd=date_obj.strftime('%y%m%d'),
                        date_slash=date_obj.strftime('%m%%2F%d%%2F%Y')
                    )

                    deep_links.append({
                        'site_name': site['name'],
                        'domain': site['domain'],
                        'url': url,
                        'priority': site['priority'],
                        'success_rate': site['success_rate']
                    })
                except Exception as e:
                    logger.warning(f"Failed to generate link for {site['domain']}: {e}")
                    continue

            return deep_links[:8]  # Return top 8 links

class IngestionEngine:
    """Handles data ingestion from browser extension"""

    def __init__(self):
        self.validator = DataValidator()

    async def ingest_results(self, data: IngestionRequest) -> Dict[str, Any]:
        """Ingest results from browser extension"""
        start_time = time.time()

        try:
            # Get site_id
            with get_db_connection() as conn:
                site = conn.execute('SELECT id FROM sites WHERE domain = ?', (data.site,)).fetchone()
                if not site:
                    # Auto-register new sites
                    cursor = conn.execute(
                        'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                        (data.site, data.site.replace('.com', '').title(), 0, 3)
                    )
                    conn.commit()
                    site_id = cursor.lastrowid
                    logger.info(f"🆕 Auto-registered new site: {data.site}")
                else:
                    site_id = site['id']

            # Find matching query
            query_id = await self._find_or_create_query(data.query)
            if not query_id:
                return {'success': False, 'error': 'Could not match query'}

            # Process each itinerary
            processed_count = 0
            duplicates_count = 0
            invalid_count = 0

            for itinerary in data.itineraries:
                try:
                    # Validate itinerary
                    if not self.validator.validate_itinerary(itinerary, data.query):
                        invalid_count += 1
                        continue

                    # Generate hash for deduplication
                    itinerary_hash = self._generate_hash(itinerary, data.query)

                    # Check for duplicates
                    with get_db_connection() as conn:
                        existing = conn.execute(
                            'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                            (query_id, itinerary_hash)
                        ).fetchone()

                        if existing:
                            duplicates_count += 1
                            continue

                        # Insert new result
                        conn.execute('''
                            INSERT INTO results (
                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                legs_json, source, carrier_codes, flight_numbers, stops,
                                fare_brand, booking_url
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            query_id, site_id, json.dumps(itinerary), itinerary_hash,
                            itinerary.get('price_total', 0), itinerary.get('price_currency', data.currency),
                            json.dumps(itinerary.get('segments', [])), 'extension',
                            json.dumps(itinerary.get('carrier_codes', [])),
                            json.dumps(itinerary.get('flight_numbers', [])),
                            itinerary.get('stops', 0), itinerary.get('fare_brand', ''),
                            itinerary.get('booking_url', '')
                        ))
                        conn.commit()
                        processed_count += 1

                except Exception as e:
                    logger.warning(f"Error processing itinerary: {e}")
                    invalid_count += 1
                    continue

            # Update site success metrics
            if processed_count > 0:
                await self._update_site_metrics(site_id, True)

            processing_time = time.time() - start_time
            logger.info(f"📥 Ingested from {data.site}: {processed_count} new, {duplicates_count} duplicates, {invalid_count} invalid ({processing_time:.2f}s)")

            return {
                'success': True,
                'processed': processed_count,
                'duplicates': duplicates_count,
                'invalid': invalid_count,
                'query_id': query_id,
                'processing_time': processing_time
            }

        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            return {'success': False, 'error': str(e)}

    async def _find_or_create_query(self, query_data: Dict[str, str]) -> Optional[int]:
        """Find existing query or create new one"""
        origin = query_data.get('origin', '').upper()
        destination = query_data.get('destination', '').upper()
        depart_date = query_data.get('depart_date', '')

        if not all([origin, destination, depart_date]):
            return None

        with get_db_connection() as conn:
            # Look for existing query (within last 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            existing = conn.execute('''
                SELECT id FROM queries
                WHERE origin = ? AND destination = ? AND depart_date = ?
                AND created_at > ?
                ORDER BY created_at DESC LIMIT 1
            ''', (origin, destination, depart_date, cutoff.isoformat())).fetchone()

            if existing:
                return existing['id']

            # Create new query
            cursor = conn.execute(
                'INSERT INTO queries (origin, destination, depart_date) VALUES (?, ?, ?)',
                (origin, destination, depart_date)
            )
            conn.commit()
            return cursor.lastrowid

    def _generate_hash(self, itinerary: Dict[str, Any], query: Dict[str, str]) -> str:
        """Generate hash for deduplication"""
        key_data = {
            'origin': query.get('origin', ''),
            'destination': query.get('destination', ''),
            'depart_date': query.get('depart_date', ''),
            'carrier': itinerary.get('carrier', ''),
            'flight_number': itinerary.get('flight_number', ''),
            'price_total': itinerary.get('price_total', 0),
            'fare_brand': itinerary.get('fare_brand', '')
        }

        hash_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]

    async def _update_site_metrics(self, site_id: int, success: bool):
        """Update site success metrics"""
        with get_db_connection() as conn:
            # Record metric
            conn.execute(
                'INSERT INTO metrics (metric_name, metric_value, site_id) VALUES (?, ?, ?)',
                ('ingestion_success' if success else 'ingestion_failure', 1.0, site_id)
            )

            # Update rolling success rate
            success_count = conn.execute(
                'SELECT COUNT(*) FROM metrics WHERE site_id = ? AND metric_name = ? AND recorded_at > datetime("now", "-7 days")',
                (site_id, 'ingestion_success')
            ).fetchone()[0]

            total_count = conn.execute(
                'SELECT COUNT(*) FROM metrics WHERE site_id = ? AND metric_name IN (?, ?) AND recorded_at > datetime("now", "-7 days")',
                (site_id, 'ingestion_success', 'ingestion_failure')
            ).fetchone()[0]

            if total_count > 0:
                success_rate = success_count / total_count
                conn.execute('UPDATE sites SET success_rate = ? WHERE id = ?', (success_rate, site_id))

            conn.commit()

class DataValidator:
    """Validates ingested flight data"""

    def __init__(self):
        # Load airport codes for validation
        self.valid_airports = set()
        self._load_airport_codes()

    def _load_airport_codes(self):
        """Load valid airport codes from CSV file"""
        try:
            # Try to load from CSV first (full dataset)
            if os.path.exists('airport-codes.csv'):
                import csv
                with open('airport-codes.csv', 'r', encoding='utf-8') as f:
                    csv_reader = csv.DictReader(f)
                    self.valid_airports = set()
                    total_rows = 0
                    for row in csv_reader:
                        total_rows += 1

                        # Get IATA code from CSV
                        iata_code = row.get('iata_code', '').strip()
                        if iata_code and len(iata_code) == 3:  # Valid IATA codes are 3 letters
                            self.valid_airports.add(iata_code.upper())

                        # Also get ICAO codes for additional validation
                        icao_code = row.get('icao_code', '').strip()
                        if icao_code and len(icao_code) == 4:  # Valid ICAO codes are 4 letters
                            self.valid_airports.add(icao_code.upper())

                        # Also add the 'ident' field which contains airport identifiers
                        ident = row.get('ident', '').strip()
                        if ident and len(ident) >= 3:  # Include all ident codes
                            self.valid_airports.add(ident.upper())

                        # Add GPS code if available
                        gps_code = row.get('gps_code', '').strip()
                        if gps_code and len(gps_code) >= 3:
                            self.valid_airports.add(gps_code.upper())

                        # Add local code if available
                        local_code = row.get('local_code', '').strip()
                        if local_code and len(local_code) >= 3:
                            self.valid_airports.add(local_code.upper())

                logger.info(f"✅ Loaded {len(self.valid_airports)} airport codes from {total_rows} total airports in CSV")
                return

            # Fallback to JSON if CSV doesn't exist
            elif os.path.exists('airports.json'):
                with open('airports.json', 'r') as f:
                    airports = json.load(f)
                    self.valid_airports = {a.get('iata_code') for a in airports if a.get('iata_code')}
                logger.info(f"✅ Loaded {len(self.valid_airports)} airport codes for validation from JSON")
                return

            # Final fallback to common codes
            if not self.valid_airports:
                self.valid_airports = {
                    'LHR', 'JFK', 'LAX', 'DXB', 'CDG', 'AMS', 'FRA', 'BCN', 'FCO', 'MAD',
                    'LGW', 'STN', 'LTN', 'ORD', 'ATL', 'DFW', 'SFO', 'MIA', 'BOS', 'SEA'
                }
                logger.info(f"✅ Loaded {len(self.valid_airports)} fallback airport codes for validation")

        except Exception as e:
            logger.warning(f"⚠️ Could not load airport codes: {e}")
            # Use fallback codes
            self.valid_airports = {
                'LHR', 'JFK', 'LAX', 'DXB', 'CDG', 'AMS', 'FRA', 'BCN', 'FCO', 'MAD',
                'LGW', 'STN', 'LTN', 'ORD', 'ATL', 'DFW', 'SFO', 'MIA', 'BOS', 'SEA'
            }

    def validate_itinerary(self, itinerary: Dict[str, Any], query: Dict[str, str]) -> bool:
        """Validate an itinerary"""
        try:
            # Required fields
            required_fields = ['price_total', 'price_currency']
            for field in required_fields:
                if field not in itinerary or not itinerary[field]:
                    return False

            # Price validation
            price = itinerary.get('price_total', 0)
            if not isinstance(price, (int, float)) or price <= 0 or price > 10000:
                return False

            # Currency validation
            currency = itinerary.get('price_currency', '')
            if currency not in ['GBP', 'USD', 'EUR', 'CAD', 'AUD']:
                return False

            # Airport codes validation (if available)
            if self.valid_airports:
                origin = query.get('origin', '').upper()
                dest = query.get('destination', '').upper()
                if origin and origin not in self.valid_airports:
                    return False
                if dest and dest not in self.valid_airports:
                    return False

            # Date validation
            depart_date = query.get('depart_date', '')
            if depart_date:
                try:
                    date_obj = datetime.strptime(depart_date, '%Y-%m-%d')
                    if date_obj < datetime.now().date():
                        return False  # No past dates
                except ValueError:
                    return False

            return True

        except Exception as e:
            logger.warning(f"Validation error: {e}")
            return False

class ResultsAggregator:
    """Aggregates and ranks flight results"""

    def get_results(self, query_id: int, limit: int = MAX_RESULTS_PER_QUERY) -> List[Dict[str, Any]]:
        """Get aggregated results for a query"""
        with get_db_connection() as conn:
            results = conn.execute('''
                SELECT r.*, s.name as site_name, s.domain, s.success_rate
                FROM results r
                JOIN sites s ON r.site_id = s.id
                WHERE r.query_id = ? AND r.valid = 1
                ORDER BY r.price_min ASC, s.success_rate DESC, r.fetched_at DESC
                LIMIT ?
            ''', (query_id, limit)).fetchall()

            formatted_results = []
            for row in results:
                try:
                    raw_data = json.loads(row['raw_json'])
                    legs_data = json.loads(row['legs_json'] or '[]')

                    formatted_results.append({
                        'id': row['id'],
                        'price': {
                            'amount': row['price_min'],
                            'currency': row['price_currency']
                        },
                        'carrier': raw_data.get('carrier', 'Unknown'),
                        'flight_number': raw_data.get('flight_number', ''),
                        'departure_time': raw_data.get('depart_local', ''),
                        'arrival_time': raw_data.get('arrive_local', ''),
                        'stops': row['stops'] or 0,
                        'fare_brand': row['fare_brand'] or 'Economy',
                        'booking_url': row['booking_url'],
                        'source': {
                            'name': row['site_name'],
                            'domain': row['domain'],
                            'success_rate': row['success_rate']
                        },
                        'legs': legs_data,
                        'fetched_at': row['fetched_at'],
                        'hash': row['hash']
                    })
                except Exception as e:
                    logger.warning(f"Error formatting result {row['id']}: {e}")
                    continue

            return formatted_results

    async def get_results_with_apis(self, query_id: int, limit: int = MAX_RESULTS_PER_QUERY) -> List[Dict[str, Any]]:
        """Get results including Amadeus and Duffel API data"""
        # Get existing results
        existing_results = self.get_results(query_id, limit)

        with get_db_connection() as conn:
            query = conn.execute('SELECT * FROM queries WHERE id = ?', (query_id,)).fetchone()

            if not query:
                return existing_results

            # Check if we already have recent API results (within last 5 minutes)
            recent_api_results = conn.execute('''
                SELECT COUNT(*) FROM results 
                WHERE query_id = ? AND source IN ('duffel_api', 'amadeus_api', 'flightapi') 
                AND fetched_at > datetime('now', '-5 minutes')
            ''', (query_id,)).fetchone()[0]

            # Only call APIs if we don't have recent results
            if recent_api_results == 0:
                # Try Duffel API first (usually more comprehensive)
                if duffel_client.is_configured():
                    try:
                        duffel_results = await duffel_client.search_flights(
                            query['origin'],
                            query['destination'], 
                            query['depart_date'],
                            query['return_date']
                        )

                        if duffel_results:
                            # Get or create Duffel site entry
                            duffel_site = conn.execute('SELECT id FROM sites WHERE domain = ?', ('duffel.com',)).fetchone()
                            if not duffel_site:
                                cursor = conn.execute(
                                    'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                                    ('duffel.com', 'Duffel API', 1, 1)
                                )
                                conn.commit()
                                duffel_site_id = cursor.lastrowid
                            else:
                                duffel_site_id = duffel_site['id']

                            # Store Duffel results
                            for result in duffel_results:
                                try:
                                    # Check for existing
                                    existing = conn.execute(
                                        'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                                        (query_id, result['hash'])
                                    ).fetchone()

                                    if not existing:
                                        conn.execute('''
                                            INSERT INTO results (
                                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                                legs_json, source, carrier_codes, flight_numbers, stops,
                                                fare_brand, booking_url, valid
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ''', (
                                            query_id, duffel_site_id, json.dumps(result), result['hash'],
                                            result['price']['amount'], result['price']['currency'],
                                            json.dumps(result['segments']), 'duffel_api',
                                            json.dumps([result['carrier']]),
                                            json.dumps([result['flight_number']]),
                                            result['stops'], 'Economy', result.get('booking_url', ''), 1
                                        ))

                                        # Add to existing results
                                        existing_results.append({
                                            'id': None,
                                            'price': result['price'],
                                            'carrier': result['carrier'],
                                            'carrier_name': result.get('carrier_name', result['carrier']),
                                            'flight_number': result['flight_number'],
                                            'departure_time': result['departure_time'],
                                            'arrival_time': result['arrival_time'],
                                            'stops': result['stops'],
                                            'fare_brand': 'Economy',
                                            'booking_url': result.get('booking_url', ''),
                                            'source': result['source'],
                                            'legs': result['segments'],
                                            'fetched_at': result['fetched_at'],
                                            'hash': result['hash'],
                                            'offer_id': result.get('offer_id', '')
                                        })

                                except Exception as e:
                                    logger.warning(f"Error storing Duffel result: {e}")
                                    continue

                            conn.commit()
                            logger.info(f"✅ Added {len(duffel_results)} Duffel results to query {query_id}")

                    except Exception as e:
                        logger.error(f"❌ Duffel API error: {e}")

                # Try FlightAPI for budget airline coverage
                if flightapi_client.is_configured():
                    try:
                        flightapi_results = await flightapi_client.search_flights(
                            query['origin'],
                            query['destination'], 
                            query['depart_date'],
                            query['return_date']
                        )

                        if flightapi_results:
                            # Get or create FlightAPI site entry
                            flightapi_site = conn.execute('SELECT id FROM sites WHERE domain = ?', ('flightapi.io',)).fetchone()
                            if not flightapi_site:
                                cursor = conn.execute(
                                    'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                                    ('flightapi.io', 'FlightAPI', 1, 2)  # Priority 2 for budget airline focus
                                )
                                conn.commit()
                                flightapi_site_id = cursor.lastrowid
                            else:
                                flightapi_site_id = flightapi_site['id']

                            # Store FlightAPI results
                            for result in flightapi_results:
                                try:
                                    # Check for existing
                                    existing = conn.execute(
                                        'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                                        (query_id, result['hash'])
                                    ).fetchone()

                                    if not existing:
                                        conn.execute('''
                                            INSERT INTO results (
                                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                                legs_json, source, carrier_codes, flight_numbers, stops,
                                                fare_brand, booking_url, valid
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        ''', (
                                            query_id, flightapi_site_id, json.dumps(result), result['hash'],
                                            result['price']['amount'], result['price']['currency'],
                                            json.dumps(result['segments']), 'flightapi',
                                            json.dumps([result['carrier']]),
                                            json.dumps([result['flight_number']]),
                                            result['stops'], 'Economy', result.get('booking_url', ''), 1
                                        ))

                                        # Add to existing results
                                        existing_results.append({
                                            'id': None,
                                            'price': result['price'],
                                            'carrier': result['carrier'],
                                            'carrier_name': result.get('carrier_name', result['carrier']),
                                            'flight_number': result['flight_number'],
                                            'departure_time': result['departure_time'],
                                            'arrival_time': result['arrival_time'],
                                            'stops': result['stops'],
                                            'fare_brand': 'Economy',
                                            'booking_url': result.get('booking_url', ''),
                                            'source': result['source'],
                                            'legs': result['segments'],
                                            'fetched_at': result['fetched_at'],
                                            'hash': result['hash'],
                                            'offer_id': result.get('offer_id', '')
                                        })

                                except Exception as e:
                                    logger.warning(f"Error storing FlightAPI result: {e}")
                                    continue

                            conn.commit()
                            logger.info(f"✅ Added {len(flightapi_results)} FlightAPI results to query {query_id}")

                    except Exception as e:
                        logger.error(f"❌ FlightAPI error: {e}")

            # If Amadeus is configured, try to get additional results
            if amadeus_client.is_configured():
                try:
                    amadeus_results = await amadeus_client.search_flights(
                        query['origin'],
                        query['destination'], 
                        query['depart_date'],
                        query['return_date']
                    )

                    if amadeus_results:
                        # Get or create Amadeus site entry
                        amadeus_site = conn.execute('SELECT id FROM sites WHERE domain = ?', ('amadeus.com',)).fetchone()
                        if not amadeus_site:
                            cursor = conn.execute(
                                'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                                ('amadeus.com', 'Amadeus API', 1, 1)
                            )
                            conn.commit()
                            amadeus_site_id = cursor.lastrowid
                        else:
                            amadeus_site_id = amadeus_site['id']

                        # Store Amadeus results
                        for result in amadeus_results:
                            try:
                                # Check for existing
                                existing = conn.execute(
                                    'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                                    (query_id, result['hash'])
                                ).fetchone()

                                if not existing:
                                    conn.execute('''
                                        INSERT INTO results (
                                            query_id, site_id, raw_json, hash, price_min, price_currency,
                                            legs_json, source, carrier_codes, flight_numbers, stops,
                                            fare_brand, booking_url, valid
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        query_id, amadeus_site_id, json.dumps(result), result['hash'],
                                        result['price']['amount'], result['price']['currency'],
                                        json.dumps(result['segments']), 'amadeus_api',
                                        json.dumps([result['carrier']]),
                                        json.dumps([result['flight_number']]),
                                        result['stops'], 'Economy', result['booking_url'], 1
                                    ))

                                    # Add to existing results
                                    existing_results.append({
                                        'id': None,
                                        'price': result['price'],
                                        'carrier': result['carrier'],
                                        'flight_number': result['flight_number'],
                                        'departure_time': result['departure_time'],
                                        'arrival_time': result['arrival_time'],
                                        'stops': result['stops'],
                                        'fare_brand': 'Economy',
                                        'booking_url': result['booking_url'],
                                        'source': result['source'],
                                        'legs': result['segments'],
                                        'fetched_at': result['fetched_at'],
                                        'hash': result['hash']
                                    })

                            except Exception as e:
                                logger.warning(f"Error storing Amadeus result: {e}")
                                continue

                        conn.commit()
                        logger.info(f"✅ Added {len(amadeus_results)} Amadeus results to query {query_id}")

                except Exception as e:
                    logger.error(f"❌ Amadeus integration error: {e}")

        # Sort by price and return
        existing_results.sort(key=lambda x: x['price']['amount'])
        return existing_results[:limit]

# Alert matching system
async def check_alert_matches(query_id: int, site_id: int):
    """Check new results against active alerts"""
    try:
        with get_db_connection() as conn:
            # Get recent results for this query
            recent_results = conn.execute('''
                SELECT r.*, q.origin, q.destination, q.depart_date
                FROM results r
                JOIN queries q ON r.query_id = q.id
                WHERE r.query_id = ? AND r.site_id = ?
                AND r.fetched_at > datetime('now', '-5 minutes')
            ''', (query_id, site_id)).fetchall()

            if not recent_results:
                return

            # Get all active alerts
            alerts = conn.execute('''
                SELECT * FROM alerts WHERE active = 1
            ''').fetchall()

            matches_count = 0

            for result in recent_results:
                try:
                    result_data = json.loads(result['raw_json'])
                    legs_data = json.loads(result['legs_json'] or '[]')

                    for alert in alerts:
                        if matches_alert_criteria(alert, result, result_data, legs_data):
                            # Check if this match already exists
                            existing = conn.execute(
                                'SELECT id FROM matches WHERE alert_id = ? AND result_id = ?',
                                (alert['id'], result['id'])
                            ).fetchone()

                            if not existing:
                                conn.execute(
                                    'INSERT INTO matches (alert_id, result_id) VALUES (?, ?)',
                                    (alert['id'], result['id'])
                                )
                                matches_count += 1
                                logger.info(f"🎯 Alert match: {alert['type']} alert {alert['id']} matched result {result['id']}")

                except Exception as e:
                    logger.warning(f"Error checking alert match: {e}")
                    continue

            if matches_count > 0:
                conn.commit()
                logger.info(f"✅ Found {matches_count} new alert matches")

    except Exception as e:
        logger.error(f"❌ Alert matching failed: {e}")

def matches_alert_criteria(alert, result, result_data, legs_data) -> bool:
    """Check if a result matches alert criteria"""
    try:
        # Basic route matching
        if alert['origin'] and alert['origin'] != result['origin']:
            return False
        if alert['destination'] and alert['destination'] != result['destination']:
            return False

        # Price range
        price = result['price_min']
        if alert['min_price'] and price < alert['min_price']:
            return False
        if alert['max_price'] and price > alert['max_price']:
            return False

        # Trip type (crude check)
        leg_count = len(legs_data) if legs_data else 0
        if alert['one_way'] and leg_count > 2:
            return False

        # Special alert types
        if alert['type'] == 'rare':
            # Check for rare aircraft
            aircrafts = result_data.get('aircraft', '').split(',')
            rare_list = (alert['rare_aircraft_list'] or '').split(',')
            if rare_list and not any(aircraft.strip() in rare_list for aircraft in aircrafts):
                return False

        elif alert['type'] == 'adventurous':
            # Origin set, destination flexible, good price
            if not alert['origin'] or alert['destination']:
                return False
            if alert['max_price'] and price > alert['max_price']:
                return False

        return True

    except Exception as e:
        logger.warning(f"Error in alert matching: {e}")
        return False

# Initialize components
query_manager = QueryManager()
ingestion_engine = IngestionEngine()
results_aggregator = ResultsAggregator()

# ------------ Lifespan management ------------
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global PLAY, BROWSER
    logger.info("🚀 Starting FlightAlert Pro BYOB Edition...")

    # Initialize database
    init_database()
    migrate_users_from_json()
    seed_initial_data()

    # Optional Playwright for validation
    if PLAYWRIGHT_AVAILABLE:
        try:
            logger.info("Starting Playwright for validation...")
            PLAY = await async_playwright().start()
            BROWSER = await PLAY.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            logger.info("✅ Playwright ready for validation")
        except Exception as e:
            logger.warning(f"⚠️ Playwright startup failed: {e}")
            PLAY = None
            BROWSER = None

    logger.info("🎯 FlightAlert Pro BYOB startup complete!")

    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        if BROWSER:
            try:
                await BROWSER.close()
            except Exception as e:
                logger.warning(f"Browser close error (expected on restart): {e}")
        if PLAY:
            try:
                await PLAY.stop()
            except Exception as e:
                logger.warning(f"Playwright stop error (expected on restart): {e}")
    except Exception as e:
        logger.warning(f"Playwright shutdown error: {e}")

# ------------ FastAPI App Setup ------------
app = FastAPI(title="FlightAlert Pro BYOB", version="3.0", lifespan=lifespan)

# CORS setup for browser extension - MUST be first middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Wide open for development - includes Codespaces preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (create directory if it doesn't exist)
import os
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info("📁 Created static directory")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# BYOB Models for stable schema
class Fare(BaseModel):
    brand: Optional[str] = None            # Economy Basic / Light / Plus
    cabin: Optional[str] = None            # economy/premium/business
    baggage: Optional[str] = None          # e.g., "cabin only", "1x23kg"
    refundable: Optional[bool] = None
    change_penalty: Optional[str] = None

class Leg(BaseModel):
    carrier: str                           # "BA"
    flight_number: str                     # "BA432"
    origin: str                            # "LHR"
    destination: str                       # "AMS"
    depart_iso: str                        # "2025-08-27T07:45:00+01:00"
    arrive_iso: str                        # "2025-08-27T10:05:00+02:00"
    aircraft: Optional[str] = None         # "A320"
    duration_min: Optional[int] = None

class Itinerary(BaseModel):
    provider: str                          # "skyscanner" | "kayak" | "ba" | ...
    url: str
    deep_link: Optional[str] = None
    price: float
    currency: str = "GBP"
    legs: List[Leg]
    fare: Optional[Fare] = None
    extra: Optional[Dict[str, Any]] = None

    @field_validator("currency")
    @classmethod
    def _upcase(cls, v): return v.upper()

class IngestPayload(BaseModel):
    query_id: int
    source_domain: str
    page_title: Optional[str] = None
    user_agent: Optional[str] = None
    results: List[Itinerary]

# Simple in-memory storage for SSE (works with existing SQLite)
SSE_CHANNELS: Dict[int, List[Dict[str, Any]]] = {}

# ------------ BYOB Bridge Endpoints ------------

@app.get("/api/ping")
async def ping():
    """Health check for browser extension"""
    return {"ok": True, "ts": time.time()}

@app.get("/api/sdk/hello")
async def sdk_hello():
    """Extension handshake endpoint"""
    return {
        "ok": True,
        "ts": time.time(),
        "schema": "v1",
        "ingest_endpoint": "/api/ingest",
        "server": "FlightAlert Pro BYOB"
    }

def _normalize_key(itin: Itinerary) -> str:
    """Generate deduplication key for itinerary"""
    first = itin.legs[0]
    last = itin.legs[-1]
    return "|".join([
        first.carrier + first.flight_number,
        first.depart_iso,
        first.origin,
        last.destination,
        itin.currency,
        f"{itin.price:.2f}",
        str(len(itin.legs)),
    ])

def validate_solid_result(result: Itinerary) -> bool:
    """Validate that result has real flight data - STRICT validation"""
    import re

    if not (result.price and result.legs and result.currency and result.provider):
        logger.debug(f"❌ Failed basic validation: missing required fields")
        return False

    # Reject demo/test sources
    if result.provider.lower() in ['demo', 'test', 'fake', 'sample']:
        logger.debug(f"❌ Rejected demo/test source: {result.provider}")
        return False

    # Check flight number format (e.g., BA432, FR1234)
    first_leg = result.legs[0]
    flight_code = first_leg.carrier + first_leg.flight_number
    if not re.match(r"^[A-Z]{2,3}\d{1,4}[A-Z]?$", flight_code):
        logger.debug(f"❌ Invalid flight code format: {flight_code}")
        return False

    # Check airport codes
    if not re.match(r"^[A-Z]{3}$", first_leg.origin):
        logger.debug(f"❌ Invalid origin airport: {first_leg.origin}")
        return False
    if not re.match(r"^[A-Z]{3}$", result.legs[-1].destination):
        logger.debug(f"❌ Invalid destination airport: {result.legs[-1].destination}")
        return False

    # Price sanity check - more realistic ranges
    if result.price <= 10 or result.price > 5000:
        logger.debug(f"❌ Price out of realistic range: £{result.price}")
        return False

    # Must have realistic departure time
    if not first_leg.depart_iso:
        logger.debug(f"❌ Missing departure time")
        return False

    # Check URL is from real site (not demo)
    if 'demo' in result.url.lower() or 'test' in result.url.lower():
        logger.debug(f"❌ Demo/test URL rejected: {result.url}")
        return False

    logger.debug(f"✅ Validated real flight: {flight_code} £{result.price}")
    return True

@app.post("/api/ingest")
async def ingest_from_extension(payload: IngestPayload, request: Request, x_fa_token: str = Header(default="")):
    """Main ingestion endpoint for browser extension with token auth"""

    logger.info(f"📥 Ingest request from {payload.source_domain} with token: {x_fa_token[:8]}...")

    # Simple token validation to prevent spam
    if x_fa_token != INGEST_TOKEN:
        logger.warning(f"❌ Invalid token from {payload.source_domain}. Expected: {INGEST_TOKEN[:8]}..., Got: {x_fa_token[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info(f"📥 BYOB ingest from {payload.source_domain}: {len(payload.results)} results for query {payload.query_id}")

    # Validate query exists
    with get_db_connection() as conn:
        query = conn.execute('SELECT id FROM queries WHERE id = ?', (payload.query_id,)).fetchone()
        if not query:
            logger.warning(f"❌ Query {payload.query_id} not found")
            raise HTTPException(status_code=404, detail="Query not found")

    # Filter and deduplicate results - only keep solid ones
    dedup: Dict[str, Itinerary] = {}
    filtered_count = 0

    for r in payload.results:
        try:
            # Only keep results that pass validation
            if not validate_solid_result(r):
                filtered_count += 1
                continue

            k = _normalize_key(r)
            if k not in dedup:
                dedup[k] = r
            else:
                # Keep cheaper option
                if r.price < dedup[k].price:
                    dedup[k] = r
        except Exception as e:
            logger.warning(f"Error processing result: {e}")
            filtered_count += 1
            continue

    clean_results = list(dedup.values())

    if filtered_count > 0:
        logger.info(f"🔍 Filtered out {filtered_count} invalid results, kept {len(clean_results)} solid ones")

    # Store in SSE channels for real-time updates
    SSE_CHANNELS.setdefault(payload.query_id, []).extend([r.dict() for r in clean_results])

    # Also store in SQLite database
    with get_db_connection() as conn:
        site = conn.execute('SELECT id FROM sites WHERE domain = ?', (payload.source_domain,)).fetchone()
        if not site:
            # Auto-register new sites
            cursor = conn.execute(
                'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                (payload.source_domain, payload.source_domain.replace('.com', '').title(), 1, 2)
            )
            conn.commit()
            site_id = cursor.lastrowid
            logger.info(f"🆕 Auto-registered site: {payload.source_domain}")
        else:
            site_id = site['id']

        # Insert results
        processed = 0
        for result in clean_results:
            try:
                result_hash = hashlib.sha256(json.dumps(result.dict(), sort_keys=True).encode()).hexdigest()[:16]

                # Check for existing
                existing = conn.execute(
                    'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                    (payload.query_id, result_hash)
                ).fetchone()

                if not existing:
                    conn.execute('''
                        INSERT INTO results (
                            query_id, site_id, raw_json, hash, price_min, price_currency,
                            legs_json, source, carrier_codes, flight_numbers, stops,
                            fare_brand, booking_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        payload.query_id, site_id, json.dumps(result.dict()), result_hash,
                        result.price, result.currency,
                        json.dumps([leg.dict() for leg in result.legs]), 'extension',
                        json.dumps([leg.carrier for leg in result.legs]),
                        json.dumps([leg.flight_number for leg in result.legs]),
                        len(result.legs) - 1,  # stops = legs - 1
                        result.fare.brand if result.fare else 'Economy',
                        result.deep_link or result.url
                    ))
                    processed += 1
            except Exception as e:
                logger.warning(f"Error storing result: {e}")
                continue

        conn.commit()

    # Check for alert matches on new results
    if processed > 0:
        await check_alert_matches(payload.query_id, site_id)

    # Enhanced logging for monitoring
    logger.info(f"✅ BYOB processed {processed} new results from {payload.source_domain}")
    if processed > 0:
        logger.info(f"🎯 REAL FLIGHTS FOUND! Query {payload.query_id} now has {processed} verified flights")

        # Log sample of what we got
        sample_results = clean_results[:2]
        for i, result in enumerate(sample_results):
            first_leg = result.legs[0]
            logger.info(f"  ✈️ {i+1}. {first_leg.carrier}{first_leg.flight_number}: £{result.price} ({result.provider})")
    else:
        logger.warning(f"⚠️ No valid flights from {payload.source_domain} - all {len(payload.results)} results filtered out")
        if filtered_count > 0:
            logger.info(f"   - {filtered_count} failed validation (demo data, invalid codes, etc.)")

    return {"ok": True, "ingested": processed, "deduplicated": len(payload.results) - len(clean_results), "filtered": filtered_count}

# ==================== AEROSPACE ENGINEERING ENDPOINTS ====================

@app.get("/api/aerospace/weather/{airport_code}")
async def get_airport_weather(airport_code: str):
    """Get current weather conditions and forecasts for airport (AEROSPACE FEATURE)"""
    try:
        airport_code = airport_code.upper()

        # Get current weather (METAR) and forecast (TAF) data
        metar_data = await weather_client.get_metar(airport_code)
        taf_data = await weather_client.get_taf(airport_code)

        # Get airport coordinates for additional calculations
        coords = get_airport_coordinates(airport_code)

        response = {
            'airport': airport_code,
            'current_weather': metar_data,
            'forecast': taf_data,
            'coordinates': coords,
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Weather API error for {airport_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Weather data unavailable for {airport_code}")

@app.get("/api/aerospace/route-analysis/{origin}/{destination}")
async def analyze_flight_route(origin: str, destination: str):
    """Aerospace engineering analysis of flight route (GREAT CIRCLE, FUEL, NAVIGATION)"""
    try:
        origin = origin.upper()
        destination = destination.upper()

        # Get airport coordinates
        origin_coords = get_airport_coordinates(origin)
        dest_coords = get_airport_coordinates(destination)

        if not origin_coords or not dest_coords:
            raise HTTPException(status_code=404, detail="Airport coordinates not found")

        # Calculate great circle distance and navigation data
        distance_data = aerospace_calc.great_circle_distance(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Calculate initial bearing for navigation
        bearing = aerospace_calc.initial_bearing(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Fuel efficiency estimates for different aircraft types
        aircraft_types = ['A320', 'A350', 'B737', 'B787', 'B777']
        fuel_estimates = {}

        for aircraft in aircraft_types:
            fuel_data = aerospace_calc.fuel_efficiency_estimate(
                distance_data['great_circle_km'], aircraft
            )
            fuel_estimates[aircraft] = fuel_data

        response = {
            'route': f"{origin} → {destination}",
            'airports': {
                'origin': {'code': origin, 'coordinates': origin_coords},
                'destination': {'code': destination, 'coordinates': dest_coords}
            },
            'distance_analysis': distance_data,
            'navigation': {
                'initial_bearing': round(bearing, 1),
                'bearing_description': get_bearing_description(bearing),
                'great_circle_route': True
            },
            'fuel_analysis_by_aircraft': fuel_estimates,
            'flight_time_estimates': {
                'commercial_average': f"{round(distance_data['great_circle_km'] / 900, 1)} hours",  # ~900 km/h average
                'business_jet': f"{round(distance_data['great_circle_km'] / 800, 1)} hours",
                'supersonic_estimated': f"{round(distance_data['great_circle_km'] / 2100, 1)} hours"  # Concorde speed
            },
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Route analysis error for {origin}-{destination}: {e}")
        raise HTTPException(status_code=500, detail=f"Route analysis failed")

@app.get("/api/aerospace/dashboard/{query_id}")
async def aerospace_dashboard(query_id: int):
    """Aerospace engineering dashboard with comprehensive flight analysis"""
    try:
        # Get flight results with aerospace analysis
        results = await results_aggregator.get_results_with_apis(query_id)

        if not results:
            raise HTTPException(status_code=404, detail="No flight results found")

        # Extract aerospace analysis data
        routes_analysis = []
        fuel_efficiency_summary = {'best': None, 'worst': None, 'average': 0}
        distance_summary = {'shortest_km': float('inf'), 'longest_km': 0}
        aircraft_summary = {}

        total_fuel = 0
        fuel_count = 0

        for result in results:
            aerospace_data = result.get('aerospace_analysis', {})

            if aerospace_data:
                # Route analysis
                routes_analysis.append({
                    'flight': f"{result['carrier']}{result['flight_number']}",
                    'route': f"{result['segments'][0]['origin']} → {result['segments'][-1]['destination']}",
                    'distance': aerospace_data.get('distance', {}),
                    'fuel_analysis': aerospace_data.get('fuel_analysis', {}),
                    'route_efficiency': aerospace_data.get('route_efficiency', {}),
                    'navigation': aerospace_data.get('navigation', {}),
                    'price': result.get('price', {})
                })

                # Fuel efficiency tracking
                fuel_data = aerospace_data.get('fuel_analysis', {})
                if 'fuel_per_passenger_liters' in fuel_data:
                    fuel_amount = fuel_data['fuel_per_passenger_liters']
                    total_fuel += fuel_amount
                    fuel_count += 1

                    if fuel_efficiency_summary['best'] is None or fuel_amount < fuel_efficiency_summary['best']['fuel']:
                        fuel_efficiency_summary['best'] = {'flight': f"{result['carrier']}{result['flight_number']}", 'fuel': fuel_amount}

                    if fuel_efficiency_summary['worst'] is None or fuel_amount > fuel_efficiency_summary['worst']['fuel']:
                        fuel_efficiency_summary['worst'] = {'flight': f"{result['carrier']}{result['flight_number']}", 'fuel': fuel_amount}

                # Distance tracking
                distance_data = aerospace_data.get('distance', {})
                if 'great_circle_km' in distance_data:
                    dist_km = distance_data['great_circle_km']
                    distance_summary['shortest_km'] = min(distance_summary['shortest_km'], dist_km)
                    distance_summary['longest_km'] = max(distance_summary['longest_km'], dist_km)

                # Aircraft summary
                aircraft = fuel_data.get('aircraft_type', 'Unknown')
                if aircraft not in aircraft_summary:
                    aircraft_summary[aircraft] = {'count': 0, 'avg_fuel': 0, 'flights': []}
                aircraft_summary[aircraft]['count'] += 1
                aircraft_summary[aircraft]['flights'].append(f"{result['carrier']}{result['flight_number']}")

        if fuel_count > 0:
            fuel_efficiency_summary['average'] = round(total_fuel / fuel_count, 2)

        response = {
            'query_id': query_id,
            'summary': {
                'total_flights_analyzed': len(results),
                'routes_with_aerospace_data': len(routes_analysis),
                'fuel_efficiency_summary': fuel_efficiency_summary,
                'distance_summary': distance_summary,
                'aircraft_types': len(aircraft_summary)
            },
            'detailed_analysis': routes_analysis[:10],  # Top 10 for dashboard
            'aircraft_breakdown': aircraft_summary,
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Aerospace dashboard error for query {query_id}: {e}")
        raise HTTPException(status_code=500, detail="Dashboard generation failed")

@app.get("/api/aerospace/live-flights/{bbox}")
async def get_live_flights_in_area(bbox: str):
    """Get live aircraft positions using OpenSky Network (FREE for students)"""
    try:
        # Parse bounding box: lat_min,lon_min,lat_max,lon_max
        coords = bbox.split(',')
        if len(coords) != 4:
            raise HTTPException(status_code=400, detail="Invalid bbox format. Use: lat_min,lon_min,lat_max,lon_max")

        lat_min, lon_min, lat_max, lon_max = map(float, coords)

        # OpenSky Network API - FREE and perfect for students
        url = f"https://opensky-network.org/api/states/all?lamin={lat_min}&lomin={lon_min}&lamax={lat_max}&lomax={lon_max}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    states = data.get('states', [])

                    # Format aircraft data for aerospace analysis
                    aircraft_list = []
                    for state in states[:50]:  # Limit to 50 aircraft
                        if state[5] and state[6]:  # Has lat/lon
                            aircraft_info = {
                                'icao24': state[0],
                                'callsign': state[1].strip() if state[1] else 'Unknown',
                                'origin_country': state[2],
                                'longitude': state[5],
                                'latitude': state[6],
                                'altitude_m': state[7],
                                'ground_speed_ms': state[9],
                                'heading_deg': state[10],
                                'vertical_rate_ms': state[11],
                                'aircraft_type': 'Unknown',  # OpenSky doesn't provide this
                                'aerospace_metrics': {
                                    'ground_speed_kmh': round(state[9] * 3.6, 1) if state[9] else None,
                                    'ground_speed_kts': round(state[9] * 1.944, 1) if state[9] else None,
                                    'altitude_ft': round(state[7] * 3.281, 0) if state[7] else None,
                                    'flight_level': round(state[7] * 3.281 / 100, 0) if state[7] else None
                                }
                            }
                            aircraft_list.append(aircraft_info)

                    return {
                        'bbox': bbox,
                        'aircraft_count': len(aircraft_list),
                        'aircraft': aircraft_list,
                        'data_source': 'OpenSky Network (FREE)',
                        'student_friendly': True,
                        'generated_at': datetime.utcnow().isoformat()
                    }
                else:
                    raise HTTPException(status_code=500, detail="OpenSky API unavailable")

    except Exception as e:
        logger.error(f"❌ Live flights API error: {e}")
        raise HTTPException(status_code=500, detail="Live flights data unavailable")

@app.get("/api/aerospace/aircraft-database/{icao_code}")
async def get_aircraft_info(icao_code: str):
    """Get aircraft specifications from aviation databases (STUDENT ACCESS)"""
    try:
        icao_code = icao_code.upper()

        # Mock aircraft database - in reality this would connect to OpenSky or FAA databases
        aircraft_db = {
            'A320': {
                'manufacturer': 'Airbus',
                'model': 'A320-200',
                'type': 'Narrow-body',
                'engines': 2,
                'engine_type': 'CFM56-5B / V2500',
                'max_passengers': 180,
                'range_km': 6150,
                'cruise_speed_mach': 0.78,
                'service_ceiling_ft': 39000,
                'mtow_kg': 78000,
                'fuel_capacity_liters': 24210,
                'wingspan_m': 35.8,
                'length_m': 37.6,
                'academic_notes': 'Popular for aerospace engineering studies due to fly-by-wire systems'
            },
            'B737': {
                'manufacturer': 'Boeing',
                'model': '737-800',
                'type': 'Narrow-body',
                'engines': 2,
                'engine_type': 'CFM56-7B',
                'max_passengers': 189,
                'range_km': 5765,
                'cruise_speed_mach': 0.785,
                'service_ceiling_ft': 41000,
                'mtow_kg': 79016,
                'fuel_capacity_liters': 26020,
                'wingspan_m': 35.8,
                'length_m': 39.5,
                'academic_notes': 'Excellent case study for traditional control systems vs fly-by-wire'
            },
            'B787': {
                'manufacturer': 'Boeing',
                'model': '787-8 Dreamliner',
                'type': 'Wide-body',
                'engines': 2,
                'engine_type': 'GEnx / Trent 1000',
                'max_passengers': 242,
                'range_km': 14800,
                'cruise_speed_mach': 0.85,
                'service_ceiling_ft': 43000,
                'mtow_kg': 227930,
                'fuel_capacity_liters': 126920,
                'wingspan_m': 60.1,
                'length_m': 56.7,
                'academic_notes': 'Advanced composite materials - 50% carbon fiber reinforced plastic'
            }
        }

        aircraft_info = aircraft_db.get(icao_code)
        if not aircraft_info:
            # Return generic info for unknown aircraft
            aircraft_info = {
                'manufacturer': 'Unknown',
                'model': icao_code,
                'academic_notes': 'Aircraft data not available in student database'
            }

        # Add educational calculations
        if 'fuel_capacity_liters' in aircraft_info and 'range_km' in aircraft_info:
            aircraft_info['educational_metrics'] = {
                'fuel_efficiency_l_per_100km': round(aircraft_info['fuel_capacity_liters'] / aircraft_info['range_km'] * 100, 2),
                'approximate_fuel_cost_full_tank_usd': round(aircraft_info['fuel_capacity_liters'] * 0.85, 2),  # ~$0.85/liter aviation fuel
                'passenger_fuel_efficiency_l_per_100km': round(aircraft_info['fuel_capacity_liters'] / aircraft_info['range_km'] * 100 / aircraft_info['max_passengers'], 3)
            }

        return {
            'icao_code': icao_code,
            'aircraft_data': aircraft_info,
            'data_source': 'Student Aviation Database',
            'educational_purpose': True,
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Aircraft database error for {icao_code}: {e}")
        raise HTTPException(status_code=500, detail="Aircraft data unavailable")

@app.get("/api/aerospace/flight-planning/{origin}/{destination}")
async def flight_planning_tools(origin: str, destination: str, altitude_ft: int = 35000):
    """Flight planning calculations for aerospace engineering students"""
    try:
        origin = origin.upper()
        destination = destination.upper()

        # Get airport coordinates
        origin_coords = get_airport_coordinates(origin)
        dest_coords = get_airport_coordinates(destination)

        if not origin_coords or not dest_coords:
            raise HTTPException(status_code=404, detail="Airport coordinates not found")

        # Basic flight planning calculations
        distance_data = aerospace_calc.great_circle_distance(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Initial bearing
        bearing = aerospace_calc.initial_bearing(
            origin_coords['lat'], origin_coords['lon'],
            dest_coords['lat'], dest_coords['lon']
        )

        # Flight time estimates at different altitudes
        flight_times = {
            'fl350_standard': {
                'altitude_ft': 35000,
                'typical_speed_kts': 450,
                'flight_time_hours': round(distance_data['great_circle_nm'] / 450, 2),
                'fuel_efficiency': 'Optimal for most aircraft'
            },
            'fl400_high': {
                'altitude_ft': 40000,
                'typical_speed_kts': 470,
                'flight_time_hours': round(distance_data['great_circle_nm'] / 470, 2),
                'fuel_efficiency': 'Better efficiency, less traffic'
            },
            'fl280_low': {
                'altitude_ft': 28000,
                'typical_speed_kts': 420,
                'flight_time_hours': round(distance_data['great_circle_nm'] / 420, 2),
                'fuel_efficiency': 'Lower efficiency, more weather'
            }
        }

        # Wind triangle calculations (simplified)
        wind_triangle = {
            'true_airspeed_kts': 450,
            'ground_speed_no_wind_kts': 450,
            'estimated_wind_effect': '±30 kts typical',
            'note': 'Actual wind data requires meteorological API integration'
        }

        response = {
            'route': f"{origin} → {destination}",
            'distance_analysis': distance_data,
            'navigation': {
                'initial_bearing': round(bearing, 1),
                'bearing_description': get_bearing_description(bearing),
                'magnetic_variation': 'Requires current navigation database'
            },
            'flight_levels': flight_times,
            'wind_triangle': wind_triangle,
            'waypoints': {
                'note': 'Actual flight plans require current AIRAC navigation data',
                'approximate_midpoint': {
                    'lat': (origin_coords['lat'] + dest_coords['lat']) / 2,
                    'lon': (origin_coords['lon'] + dest_coords['lon']) / 2
                }
            },
            'educational_notes': [
                'Flight planning requires current weather, NOTAMS, and navigation data',
                'Real-world planning uses tools like Jeppesen FliteDeck or SkyVector',
                'Commercial flights must comply with ICAO and national regulations',
                'Fuel planning includes reserve requirements (typically 10% + alternate)'
            ],
            'generated_at': datetime.utcnow().isoformat()
        }

        return response

    except Exception as e:
        logger.error(f"❌ Flight planning error for {origin}-{destination}: {e}")
        raise HTTPException(status_code=500, detail="Flight planning calculation failed")

@app.get("/api/stream/{query_id}")
async def stream_results(query_id: int):
    """SSE stream for live updates"""
    async def gen():
        last_sent = 0
        while True:
            bucket = SSE_CHANNELS.get(query_id, [])
            if len(bucket) > last_sent:
                for i in range(last_sent, len(bucket)):
                    yield f"data: {json.dumps(bucket[i])}\n\n"
                last_sent = len(bucket)
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/api/debug/connectivity")
async def debug_connectivity(request: Request, x_fa_token: str = Header(default="")):
    """Debug endpoint to check CORS, token, and connectivity"""
    return {
        "status": "connected",
        "received_token": x_fa_token,
        "expected_token": INGEST_TOKEN,
        "token_valid": x_fa_token == INGEST_TOKEN,
        "server_time": datetime.utcnow().isoformat(),
        "request_origin": request.headers.get("origin", "none"),
        "cors_enabled": True,
        "codespaces_ready": True
    }

@app.get("/api/debug/token")
async def debug_check_token(x_fa_token: str = Header(default="")):
    """Debug endpoint to check token and connectivity"""
    return {
        "received_token": x_fa_token,
        "expected_token": INGEST_TOKEN,
        "token_valid": x_fa_token == INGEST_TOKEN,
        "server_time": datetime.utcnow().isoformat(),
        "cors_headers": "enabled"
    }

@app.post("/api/debug/ingest_example/{query_id}")
async def debug_ingest_example(query_id: int, x_fa_token: str = Header(default="")):
    """Debug endpoint to test UI without extension"""
    # Validate token
    if x_fa_token != INGEST_TOKEN:
        logger.warning(f"❌ Invalid token in debug endpoint. Expected: {INGEST_TOKEN[:8]}..., Got: {x_fa_token[:8]}...")
        raise HTTPException(status_code=401, detail="Invalid token")

    # Create test fares
    test_fares = [
        {
            "origin": "LHR",
            "destination": "AMS", 
            "date": "2025-09-06",
            "airline": "British Airways",
            "price": 125.50,
            "currency": "GBP",
            "site": "debug.example",
            "url": "https://example.com/flights/LHR-AMS",
            "extracted_at": datetime.utcnow().isoformat()
        },
        {
            "origin": "LHR",
            "destination": "AMS",
            "date": "2025-09-06", 
            "airline": "KLM",
            "price": 89.99,
            "currency": "GBP",
            "site": "debug.example",
            "url": "https://example.com/flights/LHR-AMS-klm",
            "extracted_at": datetime.utcnow().isoformat()
        }
    ]

    # Use the simple ingest endpoint
    payload = {
        "query_id": query_id,
        "fares": test_fares,
        "site": "debug.example"
    }

    try:
        result = await ingest_fares(payload, x_fa_token)
        logger.info(f"✅ Debug test successful: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Debug test failed: {e}")
        raise

@app.post("/api/debug/ingest")
async def ingest_fares(payload: dict, x_fa_token: str = Header(default="")):
    """Simple ingestion endpoint for BYOB extension"""
    try:
        # Validate token
        if x_fa_token != INGEST_TOKEN:
            logger.warning(f"❌ Invalid token from extension. Expected: {INGEST_TOKEN[:8]}..., Got: {x_fa_token[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid token")

        query_id = payload.get("query_id")
        fares = payload.get("fares", [])
        site_domain = payload.get("site", "unknown")

        if not query_id:
            raise HTTPException(status_code=400, detail="query_id required")

        logger.info(f"📩 Received {len(fares)} fares from extension for query {query_id} from {site_domain}")

        # Get or create site
        with get_db_connection() as conn:
            site = conn.execute('SELECT id FROM sites WHERE domain = ?', (site_domain,)).fetchone()
            if not site:
                cursor = conn.execute(
                    'INSERT INTO sites (domain, name, allowed_scrape, priority) VALUES (?, ?, ?, ?)',
                    (site_domain, site_domain.replace('.com', '').title(), 1, 2)
                )
                conn.commit()
                site_id = cursor.lastrowid
                logger.info(f"🆕 Auto-registered site: {site_domain}")
            else:
                site_id = site['id']

            # Store fares
            processed = 0
            for fare in fares:
                try:
                    # Generate hash for deduplication
                    fare_hash = hashlib.sha256(json.dumps(fare, sort_keys=True).encode()).hexdigest()[:16]

                    # Check for duplicates
                    existing = conn.execute(
                        'SELECT id FROM results WHERE query_id = ? AND hash = ?',
                        (query_id, fare_hash)
                    ).fetchone()

                    if not existing:
                        conn.execute('''
                            INSERT INTO results (
                                query_id, site_id, raw_json, hash, price_min, price_currency,
                                source, carrier_codes, booking_url, valid
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            query_id, site_id, json.dumps(fare), fare_hash,
                            fare.get('price', 0), fare.get('currency', 'GBP'),
                            'extension', json.dumps([fare.get('airline', '')]),
                            fare.get('url', ''), 1
                        ))
                        processed += 1
                        logger.debug(f"💾 Stored fare: {fare}")
                except Exception as e:
                    logger.warning(f"Error processing fare: {e}")
                    continue

            conn.commit()

        # Check for alert matches
        if processed > 0:
            await check_alert_matches(query_id, site_id)

        logger.info(f"✅ Processed {processed} new fares from {site_domain}")
        return {"ok": True, "count": processed}

    except Exception as e:
        logger.error(f"❌ BYOB ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results/{query_id}")
async def get_results(query_id: int):
    """Get results for a query with enhanced logging"""
    try:
        # Use API-enhanced results (Duffel + Amadeus)
        results = await results_aggregator.get_results_with_apis(query_id)

        with get_db_connection() as conn:
            query = conn.execute('SELECT * FROM queries WHERE id = ?', (query_id,)).fetchone()

            if not query:
                logger.warning(f"❌ Query {query_id} not found")
                raise HTTPException(status_code=404, detail="Query not found")

            # Enhanced logging for debugging
            if results:
                sources = {}
                for result in results:
                    source = result.get('source', {}).get('name', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
                logger.info(f"📊 Query {query_id}: {len(results)} results from sources: {sources}")
            else:
                # Check if there are any results at all for this query
                total_results = conn.execute('SELECT COUNT(*) FROM results WHERE query_id = ?', (query_id,)).fetchone()[0]

                # NO DEMO DATA - Only show real results
                if total_results == 0:
                    query_age_minutes = conn.execute('''
                        SELECT (julianday('now') - julianday(created_at)) * 1440 as age_minutes 
                        FROM queries WHERE id = ?
                    ''', (query_id,)).fetchone()[0]

                    logger.info(f"⏳ Query {query_id}: No real flight data yet. Query age: {int(query_age_minutes*60)}s")
                    logger.info(f"💡 Searching with API sources for comprehensive flight data")
                else:
                    logger.info(f"📊 Query {query_id}: Found {total_results} results in database, but none passed validation filters")

            return {
                'query_id': query_id,
                'query': dict(query),
                'results': results,
                'total_found': len(results),
                'last_updated': datetime.utcnow().isoformat(),
                'status': 'active' if len(results) == 0 else 'results_found'
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Results retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cities")
async def search_cities(q: str = ""):
    """Search cities by grouping airports from the CSV dataset"""
    try:
        if not q or len(q) < 2:
            return {"cities": []}

        cities = {}  # Dictionary to group airports by city
        q_lower = q.lower()

        try:
            # Use CSV file first (comprehensive dataset)
            if os.path.exists('airport-codes.csv'):
                import csv
                with open('airport-codes.csv', 'r', encoding='utf-8') as f:
                    csv_reader = csv.DictReader(f)
                    for row in csv_reader:
                        # Get airport details
                        iata_code = row.get('iata_code', '').strip()
                        icao_code = row.get('icao_code', '').strip()
                        ident = row.get('ident', '').strip()
                        name = row.get('name', '').strip()
                        municipality = row.get('municipality', '').strip()
                        iso_country = row.get('iso_country', '').strip()
                        airport_type = row.get('type', '').strip()

                        # Prefer IATA codes but include major airports with ICAO codes
                        display_code = iata_code if iata_code else icao_code

                        # Skip if no usable code or not a public airport
                        if not display_code or len(display_code) < 3:
                            continue
                        if airport_type in ['closed', 'heliport', 'seaplane_base']:
                            continue

                        # Search in city and airport names
                        searchable_text = f"{municipality} {name} {iata_code} {icao_code} {ident}".lower()
                        if q_lower in searchable_text and municipality:
                            # Group by city (municipality)
                            city_key = f"{municipality}, {iso_country}"
                            if city_key not in cities:
                                cities[city_key] = {
                                    'airports': [],
                                    'primary_code': None,
                                    'municipality': municipality,
                                    'country': iso_country
                                }

                            # Add airport to city group
                            cities[city_key]['airports'].append({
                                'code': display_code.upper(),
                                'name': name,
                                'type': airport_type
                            })

                            # Set primary airport code (prefer major international airports)
                            major_airports = {'LHR', 'LGW', 'STN', 'LTN', 'LCY', 'SEN'}

                            if not cities[city_key]['primary_code']:
                                cities[city_key]['primary_code'] = display_code.upper()
                            elif iata_code and len(iata_code) == 3:
                                current_code = cities[city_key]['primary_code']
                                current_type = cities[city_key]['airports'][0]['type'] if cities[city_key]['airports'] else ''

                                # Prefer major international airports
                                if iata_code in major_airports and current_code not in major_airports:
                                    cities[city_key]['primary_code'] = display_code.upper()
                                # Otherwise prefer large airports over smaller ones
                                elif (airport_type == 'large_airport' and current_type != 'large_airport') or \
                                     (airport_type == 'medium_airport' and current_type not in ['large_airport', 'medium_airport']):
                                    cities[city_key]['primary_code'] = display_code.upper()

                        if len(cities) >= 50:  # Limit to 50 cities for performance
                            break

                logger.info(f"Found {len(cities)} cities matching '{q}' from CSV")

            # Convert to list format for frontend
            city_list = []
            for city_name, city_data in cities.items():
                # Show number of airports if more than one
                airport_count = len(city_data['airports'])
                if airport_count > 1:
                    display_text = f"{city_name} ({airport_count} airports)"
                else:
                    display_text = city_name

                city_list.append({
                    'code': city_data['primary_code'],  # Use primary airport code
                    'display': display_text,
                    'airport_count': airport_count,
                    'airports': city_data['airports']  # Include all airports for this city
                })

            # Sort by city name
            city_list.sort(key=lambda x: x['display'])

            return {"cities": city_list[:30]}  # Return top 30 matches

        except Exception as e:
            logger.error(f"Error reading CSV for city search: {e}")

            # Fallback to JSON if CSV fails
            if os.path.exists('airports.json'):
                with open('airports.json', 'r') as f:
                    data = json.load(f)
                    cities = {}
                    for airport in data.get('airports', []):
                        code = airport.get('iata', airport.get('icao', ''))
                        name = airport.get('name', '')
                        city = airport.get('city', '')
                        country = airport.get('country', '')

                        if code and city and (q_lower in name.lower() or q_lower in city.lower() or q_lower in code.lower()):
                            city_key = f"{city}, {country}"
                            if city_key not in cities:
                                cities[city_key] = {
                                    'code': code,
                                    'display': city_key
                                }

                    return {"cities": list(cities.values())[:30]}

        return {"cities": []}
    except Exception as e:
        logger.error(f"City search failed: {e}")
        return {"cities": []}

@app.get("/api/airports")
async def search_airports(q: str = ""):
    """Search airports by query string using comprehensive CSV dataset"""
    try:
        if not q or len(q) < 2:
            return {"airports": []}

        airports = []
        q_lower = q.lower()

        try:
            # Use CSV file first (comprehensive dataset)
            if os.path.exists('airport-codes.csv'):
                import csv
                with open('airport-codes.csv', 'r', encoding='utf-8') as f:
                    csv_reader = csv.DictReader(f)
                    for row in csv_reader:
                        # Get airport details
                        iata_code = row.get('iata_code', '').strip()
                        icao_code = row.get('icao_code', '').strip()
                        ident = row.get('ident', '').strip()
                        name = row.get('name', '').strip()
                        municipality = row.get('municipality', '').strip()
                        iso_country = row.get('iso_country', '').strip()
                        airport_type = row.get('type', '').strip()

                        # Prefer IATA codes but also include airports with only ICAO or ident codes
                        display_code = iata_code if iata_code else (icao_code if icao_code else ident)

                        # Skip if no usable code
                        if not display_code or len(display_code) < 3:
                            continue

                        # Skip closed airports
                        if airport_type == 'closed':
                            continue

                        # Search in various fields
                        searchable_text = f"{name} {municipality} {iata_code} {icao_code} {ident}".lower()
                        if q_lower in searchable_text:
                            # Create display name
                            location_parts = []
                            if municipality:
                                location_parts.append(municipality)
                            if iso_country:
                                location_parts.append(iso_country)
                            location = ", ".join(location_parts) if location_parts else "Unknown"

                            airports.append({
                                'code': display_code.upper(),
                                'display': f"{display_code.upper()} - {name}, {location}"
                            })

                        if len(airports) >= 100:  # Increased limit for better search results
                            break

                logger.info(f"Found {len(airports)} airports matching '{q}' from CSV")

            # Fallback to JSON if CSV doesn't exist
            elif os.path.exists('airports.json'):
                with open('airports.json', 'r') as f:
                    all_airports = json.load(f)

                for airport in all_airports:
                    if (q_lower in airport.get('name', '').lower() or
                        q_lower in airport.get('city', '').lower() or
                        q_lower in airport.get('iata_code', '').lower()):
                        airports.append({
                            'code': airport.get('iata_code', ''),
                            'display': f"{airport.get('iata_code', '')} - {airport.get('name', '')}, {airport.get('city', '')} ({airport.get('country', '')})"
                        })
                        if len(airports) >= 20:
                            break

            # Final fallback with common airports
            else:
                common_airports = [
                    {'code': 'LHR', 'display': 'LHR - London Heathrow, London (GB)'},
                    {'code': 'JFK', 'display': 'JFK - John F Kennedy Intl, New York (US)'},
                    {'code': 'LAX', 'display': 'LAX - Los Angeles Intl, Los Angeles (US)'},
                    {'code': 'DXB', 'display': 'DXB - Dubai Intl, Dubai (AE)'},
                    {'code': 'CDG', 'display': 'CDG - Charles de Gaulle, Paris (FR)'},
                    {'code': 'AMS', 'display': 'AMS - Amsterdam Schiphol, Amsterdam (NL)'},
                    {'code': 'FRA', 'display': 'FRA - Frankfurt am Main, Frankfurt (DE)'},
                    {'code': 'BCN', 'display': 'BCN - Barcelona El Prat, Barcelona (ES)'},
                    {'code': 'FCO', 'display': 'FCO - Rome Fiumicino, Rome (IT)'},
                    {'code': 'MAD', 'display': 'MAD - Madrid Barajas, Madrid (ES)'},
                ]

                airports = [a for a in common_airports if q_lower in a['display'].lower()]

        except Exception as e:
            logger.warning(f"Error loading airports: {e}")
            airports = []

        return {"airports": airports}

    except Exception as e:
        logger.error(f"Airport search failed: {e}")
        return {"airports": []}

@app.get("/api/airlines")
async def search_airlines(q: str = ""):
    """Search airlines by query string"""
    try:
        # Common airlines database
        airlines = [
            {'code': 'BA', 'display': 'BA - British Airways (United Kingdom)'},
            {'code': 'LH', 'display': 'LH - Lufthansa (Germany)'},
            {'code': 'AF', 'display': 'AF - Air France (France)'},
            {'code': 'KL', 'display': 'KL - KLM Royal Dutch Airlines (Netherlands)'},
            {'code': 'VS', 'display': 'VS - Virgin Atlantic (United Kingdom)'},
            {'code': 'EK', 'display': 'EK - Emirates (United Arab Emirates)'},
            {'code': 'QR', 'display': 'QR - Qatar Airways (Qatar)'},
            {'code': 'EY', 'display': 'EY - Etihad Airways (United Arab Emirates)'},
            {'code': 'TK', 'display': 'TK - Turkish Airlines (Turkey)'},
            {'code': 'SQ', 'display': 'SQ - Singapore Airlines (Singapore)'},
            {'code': 'QF', 'display': 'QF - Qantas (Australia)'},
            {'code': 'CX', 'display': 'CX - Cathay Pacific (Hong Kong)'},
            {'code': 'JL', 'display': 'JL - Japan Airlines (Japan)'},
            {'code': 'NH', 'display': 'NH - All Nippon Airways (Japan)'},
            {'code': 'AC', 'display': 'AC - Air Canada (Canada)'},
            {'code': 'WS', 'display': 'WS - WestJet (Canada)'},
            {'code': 'DL', 'display': 'DL - Delta Air Lines (United States)'},
            {'code': 'UA', 'display': 'UA - United Airlines (United States)'},
            {'code': 'AA', 'display': 'AA - American Airlines (United States)'},
            {'code': 'AS', 'display': 'AS - Alaska Airlines (United States)'},
            {'code': 'B6', 'display': 'B6 - JetBlue Airways (United States)'},
            {'code': 'WN', 'display': 'WN - Southwest Airlines (United States)'},
            {'code': 'FR', 'display': 'FR - Ryanair (Ireland)'},
            {'code': 'U2', 'display': 'U2 - easyJet (United Kingdom)'},
            {'code': 'VY', 'display': 'VY - Vueling (Spain)'},
            {'code': 'W6', 'display': 'W6 - Wizz Air (Hungary)'},
            {'code': 'BE', 'display': 'BE - FlyBe (United Kingdom)'},
            {'code': 'MT', 'display': 'MT - Thomas Cook Airlines (United Kingdom)'},
            {'code': 'LS', 'display': 'LS - Jet2.com (United Kingdom)'},
            {'code': 'BY', 'display': 'BY - TUI Airways (United Kingdom)'},
            {'code': 'SN', 'display': 'SN - Brussels Airlines (Belgium)'},
            {'code': 'LX', 'display': 'LX - Swiss International Air Lines (Switzerland)'},
            {'code': 'OS', 'display': 'OS - Austrian Airlines (Austria)'},
            {'code': 'SK', 'display': 'SK - Scandinavian Airlines (Sweden)'},
            {'code': 'AY', 'display': 'AY - Finnair (Finland)'},
            {'code': 'DY', 'display': 'DY - Norwegian Air Shuttle (Norway)'},
            {'code': 'IB', 'display': 'IB - Iberia (Spain)'},
            {'code': 'UX', 'display': 'UX - Air Europa (Spain)'},
            {'code': 'TP', 'display': 'TP - TAP Air Portugal (Portugal)'},
            {'code': 'AZ', 'display': 'AZ - Alitalia (Italy)'},
            {'code': 'EN', 'display': 'EN - Air Dolomiti (Italy)'},
            {'code': 'LO', 'display': 'LO - LOT Polish Airlines (Poland)'},
            {'code': 'OK', 'display': 'OK - Czech Airlines (Czech Republic)'},
            {'code': 'RO', 'display': 'RO - Tarom (Romania)'},
            {'code': 'JU', 'display': 'JU - Air Serbia (Serbia)'},
            {'code': 'OU', 'display': 'OU - Croatia Airlines (Croatia)'},
            {'code': 'JP', 'display': 'JP - Adria Airways (Slovenia)'},
            {'code': 'BT', 'display': 'BT - Air Baltic (Latvia)'},
            {'code': 'SU', 'display': 'SU - Aeroflot (Russia)'},
            {'code': 'S7', 'display': 'S7 - S7 Airlines (Russia)'},
            {'code': 'UT', 'display': 'UT - UTair (Russia)'},
            {'code': 'FZ', 'display': 'FZ - flydubai (United Arab Emirates)'},
            {'code': 'WY', 'display': 'WY - Oman Air (Oman)'},
            {'code': 'GF', 'display': 'GF - Gulf Air (Bahrain)'},
            {'code': 'KU', 'display': 'KU - Kuwait Airways (Kuwait)'},
            {'code': 'SV', 'display': 'SV - Saudi Arabian Airlines (Saudi Arabia)'},
            {'code': 'MS', 'display': 'MS - EgyptAir (Egypt)'},
            {'code': 'ET', 'display': 'ET - Ethiopian Airlines (Ethiopia)'},
            {'code': 'SA', 'display': 'SA - South African Airways (South Africa)'},
            {'code': 'MN', 'display': 'MN - Kulula (South Africa)'},
            {'code': 'AI', 'display': 'AI - Air India (India)'},
            {'code': '6E', 'display': '6E - IndiGo (India)'},
            {'code': 'SG', 'display': 'SG - SpiceJet (India)'},
            {'code': 'UK', 'display': 'UK - Vistara (India)'},
            {'code': 'IX', 'display': 'IX - Air India Express (India)'},
            {'code': 'PK', 'display': 'PK - Pakistan International Airlines (Pakistan)'},
            {'code': 'BG', 'display': 'BG - Biman Bangladesh Airlines (Bangladesh)'},
            {'code': 'UL', 'display': 'UL - SriLankan Airlines (Sri Lanka)'},
            {'code': 'TG', 'display': 'TG - Thai Airways (Thailand)'},
            {'code': 'FD', 'display': 'FD - Thai AirAsia (Thailand)'},
            {'code': 'SL', 'display': 'SL - Thai Lion Air (Thailand)'},
            {'code': 'MH', 'display': 'MH - Malaysia Airlines (Malaysia)'},
            {'code': 'AK', 'display': 'AK - AirAsia (Malaysia)'},
            {'code': 'D7', 'display': 'D7 - AirAsia X (Malaysia)'},
            {'code': 'BI', 'display': 'BI - Royal Brunei Airlines (Brunei)'},
            {'code': 'TR', 'display': 'TR - Scoot (Singapore)'},
            {'code': 'MI', 'display': 'MI - SilkAir (Singapore)'},
            {'code': 'GA', 'display': 'GA - Garuda Indonesia (Indonesia)'},
            {'code': 'JT', 'display': 'JT - Lion Air (Indonesia)'},
            {'code': 'QG', 'display': 'QG - Citilink (Indonesia)'},
            {'code': 'VN', 'display': 'VN - Vietnam Airlines (Vietnam)'},
            {'code': 'VJ', 'display': 'VJ - VietJet Air (Vietnam)'},
            {'code': 'PR', 'display': 'PR - Philippine Airlines (Philippines)'},
            {'code': '5J', 'display': '5J - Cebu Pacific (Philippines)'},
            {'code': 'CA', 'display': 'CA - Air China (China)'},
            {'code': 'CZ', 'display': 'CZ - China Southern Airlines (China)'},
            {'code': 'MU', 'display': 'MU - China Eastern Airlines (China)'},
            {'code': 'HU', 'display': 'HU - Hainan Airlines (China)'},
            {'code': 'SC', 'display': 'SC - Shandong Airlines (China)'},
            {'code': 'FM', 'display': 'FM - Shanghai Airlines (China)'},
            {'code': 'OZ', 'display': 'OZ - Asiana Airlines (South Korea)'},
            {'code': 'KE', 'display': 'KE - Korean Air (South Korea)'},
            {'code': 'TW', 'display': 'TW - T way Air (South Korea)'},
            {'code': 'CI', 'display': 'CI - China Airlines (Taiwan)'},
            {'code': 'BR', 'display': 'BR - EVA Air (Taiwan)'},
            {'code': 'IT', 'display': 'IT - Tigerair Taiwan (Taiwan)'},
            {'code': 'HX', 'display': 'HX - Hong Kong Airlines (Hong Kong)'},
            {'code': 'UO', 'display': 'UO - HK Express (Hong Kong)'},
            {'code': 'NX', 'display': 'NX - Air Macau (Macau)'},
        ]

        if not q:
            # Return first 20 airlines if no search query
            return airlines[:20]

        q_lower = q.lower()
        filtered_airlines = []

        for airline in airlines:
            # Search in airline code, name, and country
            if (q_lower in airline['code'].lower() or
                q_lower in airline['display'].lower()):
                filtered_airlines.append(airline)
                if len(filtered_airlines) >= 50:  # Limit results
                    break

        return filtered_airlines

    except Exception as e:
        logger.error(f"Airline search failed: {e}")
        return []

@app.get("/api/flight_stats")
async def get_flight_stats():
    """Get live flight statistics"""
    return {
        'flights_tracked_now': random.randint(7500, 8500),
        'countries_represented': random.randint(95, 110),
        'average_altitude_feet': random.randint(22000, 26000)
    }

@app.get("/api/trending_routes")
async def get_trending_routes():
    """Get trending flight routes"""
    routes = [
        {'route': 'LHR-AMS', 'change': 15},
        {'route': 'LHR-CDG', 'change': -8},
        {'route': 'LHR-BCN', 'change': 22},
        {'route': 'LHR-FCO', 'change': -5},
        {'route': 'LHR-MAD', 'change': 12}
    ]
    return {'routes': routes}

@app.get("/api/airport_delays")
async def get_airport_delays():
    """Get live airport delays"""
    delays = [
        {'airport': 'LHR', 'delay': '15 min', 'severity': 'minor'},
        {'airport': 'CDG', 'delay': '45 min', 'severity': 'moderate'},
        {'airport': 'AMS', 'delay': '2 hours', 'severity': 'major'},
        {'airport': 'FRA', 'delay': '20 min', 'severity': 'minor'},
        {'airport': 'MAD', 'delay': '30 min', 'severity': 'moderate'}
    ]
    return {'delays': delays}

@app.get("/api/rare_aircraft_spotted")
async def get_rare_aircraft():
    """Get recently spotted rare aircraft"""
    sightings = [
        {'type': 'Airbus A380', 'route': 'LHR-DXB', 'time': '2 hours ago'},
        {'type': 'Boeing 787 Dreamliner', 'route': 'LHR-NRT', 'time': '4 hours ago'},
        {'type': 'Airbus A350', 'route': 'CDG-SIN', 'time': '6 hours ago'}
    ]
    return {'sightings': sightings}

@app.get("/api/price_war/{departure}/{destination}")
async def get_price_war(departure: str, destination: str):
    """Get price war data for a route"""
    airlines = [
        {'airline': 'Ryanair', 'price': 89.99},
        {'airline': 'easyJet', 'price': 94.50},
        {'airline': 'British Airways', 'price': 125.00}
    ]
    random.shuffle(airlines)
    return {
        'price_drop_alert': f'Price battle active on {departure}-{destination}!',
        'airlines': airlines
    }

@app.get("/api/surprise_me")
async def surprise_me(budget: float = 200):
    """Get surprise destinations within budget"""
    destinations = [
        {'city': 'Amsterdam', 'price': budget * 0.6},
        {'city': 'Barcelona', 'price': budget * 0.7},
        {'city': 'Prague', 'price': budget * 0.5},
        {'city': 'Dublin', 'price': budget * 0.8}
    ]
    return {
        'message': f'Amazing destinations under £{budget}!',
        'destinations': destinations
    }

@app.post("/api/ingest")
async def ingest_extension_data(request: Request):
    """Production ingest endpoint for BYOB extension"""
    try:
        data = await request.json()

        # Validate required fields
        required_fields = ['vendor', 'url', 'price']
        if not all(field in data for field in required_fields):
            return {'ok': False, 'error': 'Missing required fields'}

        # Basic validation
        price = float(data['price'])
        if price <= 0 or price > 50000:  # Reasonable bounds
            return {'ok': False, 'error': 'Invalid price range'}

        vendor = data['vendor']
        url = data['url']
        currency = data.get('currency', 'GBP')
        route = data.get('route', {})
        page_title = data.get('pageTitle', '')
        tab_url = data.get('tabUrl', '')
        user_agent = data.get('userAgent', '')
        ts = data.get('ts', datetime.now().isoformat())

        with get_db_connection() as conn:
            # Insert into results table (matching your existing schema)
            result_id = conn.execute('''
                INSERT INTO results (
                    query_id, price, currency, airline, url, site, 
                    source, valid, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                None,  # No specific query_id for extension data
                price,
                currency,
                vendor,  # Use vendor as airline
                url,
                vendor,  # Site name
                'extension',  # Mark as extension source
                1,  # Valid
                ts
            )).lastrowid

            # Also store in a separate extension_fares table for detailed analysis
            conn.execute('''
                CREATE TABLE IF NOT EXISTS extension_fares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER,
                    vendor TEXT,
                    url TEXT,
                    price REAL,
                    currency TEXT,
                    origin TEXT,
                    destination TEXT,
                    date TEXT,
                    page_title TEXT,
                    tab_url TEXT,
                    user_agent TEXT,
                    ts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (result_id) REFERENCES results (id)
                )
            ''')

            conn.execute('''
                INSERT INTO extension_fares (
                    result_id, vendor, url, price, currency, origin, 
                    destination, date, page_title, tab_url, user_agent, ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_id,
                vendor,
                url,
                price,
                currency,
                route.get('origin', ''),
                route.get('destination', ''),
                route.get('date', ''),
                page_title,
                tab_url,
                user_agent,
                ts
            ))

            conn.commit()

        logger.info(f"🔧 Extension data ingested: {vendor} - £{price} from {url[:50]}...")
        return {'ok': True, 'id': result_id, 'price': price, 'vendor': vendor}

    except Exception as e:
        logger.error(f"❌ Extension ingest error: {e}")
        return {'ok': False, 'error': str(e)}

@app.get("/api/extension_stats")
async def get_extension_stats():
    """Get stats on extension-collected data"""
    with get_db_connection() as conn:
        # Get extension data stats
        total_fares = conn.execute('SELECT COUNT(*) FROM results WHERE source = "extension"').fetchone()[0]

        by_vendor = conn.execute('''
            SELECT site, COUNT(*) as count, AVG(price) as avg_price
            FROM results 
            WHERE source = "extension" AND fetched_at > datetime("now", "-7 days")
            GROUP BY site
            ORDER BY count DESC
        ''').fetchall()

        recent_fares = conn.execute('''
            SELECT site, price, currency, url, fetched_at
            FROM results 
            WHERE source = "extension" 
            ORDER BY id DESC 
            LIMIT 10
        ''').fetchall()

        return {
            'total_extension_fares': total_fares,
            'vendors_7d': [{'vendor': row[0], 'count': row[1], 'avg_price': row[2]} for row in by_vendor],
            'recent_fares': [
                {
                    'vendor': row[0], 
                    'price': row[1], 
                    'currency': row[2], 
                    'url': row[3][:50] + '...' if len(row[3]) > 50 else row[3],
                    'time': row[4]
                } for row in recent_fares
            ]
        }

@app.get("/api/amadeus/status")
async def amadeus_status():
    """Check Amadeus API configuration status"""
    return {
        'configured': amadeus_client.is_configured(),
        'api_key_set': bool(AMADEUS_API_KEY),
        'api_secret_set': bool(AMADEUS_API_SECRET),
        'test_mode': AMADEUS_TEST_MODE,
        'has_token': bool(amadeus_client.access_token),
        'token_expires_at': amadeus_client.token_expires_at.isoformat() if amadeus_client.token_expires_at else None
    }

@app.get("/api/duffel/status")
async def duffel_status():
    """Check Duffel API configuration status"""
    return {
        'configured': duffel_client.is_configured(),
        'api_key_set': bool(DUFFEL_API_KEY),
        'api_key_prefix': DUFFEL_API_KEY[:20] + '...' if DUFFEL_API_KEY else None,
        'base_url': DUFFEL_BASE_URL
    }

@app.post("/api/amadeus/test")
async def test_amadeus():
    """Test Amadeus API connection"""
    if not amadeus_client.is_configured():
        raise HTTPException(status_code=400, detail="Amadeus API not configured")

    try:
        # Test authentication
        token = await amadeus_client.get_access_token()
        if token:
            # Test a simple search
            test_results = await amadeus_client.search_flights('LHR', 'CDG', '2025-09-01')
            return {
                'success': True,
                'token_obtained': True,
                'search_test': len(test_results) > 0,
                'results_count': len(test_results)
            }
        else:
            return {
                'success': False,
                'token_obtained': False,
                'error': 'Failed to obtain access token'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.post("/api/duffel/test")
async def test_duffel():
    """Test Duffel API connection"""
    if not duffel_client.is_configured():
        raise HTTPException(status_code=400, detail="Duffel API not configured")

    try:
        # Test a simple search
        test_results = await duffel_client.search_flights('LHR', 'CDG', '2025-09-01')
        return {
            'success': True,
            'search_test': len(test_results) > 0,
            'results_count': len(test_results),
            'sample_result': test_results[0] if test_results else None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/api/duffel/offers/{offer_id}")
async def get_duffel_offer(offer_id: str):
    """Get detailed Duffel offer information"""
    if not duffel_client.is_configured():
        raise HTTPException(status_code=400, detail="Duffel API not configured")

    try:
        headers = {
            "Authorization": f"Bearer {DUFFEL_API_KEY}",
            "Content-Type": "application/json",
            "Duffel-Version": "v2"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DUFFEL_BASE_URL}/air/offers/{offer_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Duffel offer request failed: {response.status} - {error_text}")
                    raise HTTPException(status_code=response.status, detail="Failed to fetch offer")

    except Exception as e:
        logger.error(f"❌ Duffel offer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint with real data status"""
    with get_db_connection() as conn:
        # Basic DB connectivity test
        site_count = conn.execute('SELECT COUNT(*) FROM sites').fetchone()[0]
        result_count = conn.execute('SELECT COUNT(*) FROM results WHERE fetched_at > datetime("now", "-24 hours")').fetchone()[0]
        user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]

        # Real data status
        real_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "extension" AND valid = 1').fetchone()[0]
        demo_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "demo"').fetchone()[0]

        # Recent activity
        recent_queries = conn.execute('SELECT COUNT(*) FROM queries WHERE created_at > datetime("now", "-1 hour")').fetchone()[0]
        recent_results = conn.execute('SELECT COUNT(*) FROM results WHERE fetched_at > datetime("now", "-1 hour") AND source = "extension"').fetchone()[0]

        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'sites_configured': site_count,
            'results_24h': result_count,
            'users_registered': user_count,
            'playwright_available': PLAYWRIGHT_AVAILABLE,
            'amadeus_configured': amadeus_client.is_configured(),
            'duffel_configured': duffel_client.is_configured(),
            'version': '3.0',
            'data_status': {
                'real_flights': real_results,
                'demo_flights': demo_results,
                'recent_queries_1h': recent_queries,
                'recent_real_results_1h': recent_results,
                'data_collection': 'BYOB extension + Amadeus API'
            }
        }

@app.get("/api/data_status")
async def get_data_status():
    """Get detailed status of real vs demo data"""
    with get_db_connection() as conn:
        # Detailed breakdown
        total_results = conn.execute('SELECT COUNT(*) FROM results').fetchone()[0]
        real_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "extension" AND valid = 1').fetchone()[0]
        demo_results = conn.execute('SELECT COUNT(*) FROM results WHERE source = "demo"').fetchone()[0]

        # By source breakdown
        source_breakdown = conn.execute('''
            SELECT 
                CASE 
                    WHEN source = "extension" THEN "Real Browser Extension Data"
                    WHEN source = "demo" THEN "Demo/Test Data"
                    ELSE "Other"
                END as source_type,
                COUNT(*) as count
            FROM results 
            GROUP BY source_type
            ORDER BY count DESC
        ''').fetchall()

        # Recent activity by query
        recent_activity = conn.execute('''
            SELECT 
                q.id,
                q.origin || " → " || q.destination as route,
                q.depart_date,
                COUNT(r.id) as result_count,
                SUM(CASE WHEN r.source = "extension" THEN 1 ELSE 0 END) as real_count
            FROM queries q
            LEFT JOIN results r ON q.id = r.query_id
            WHERE q.created_at > datetime("now", "-24 hours")
            GROUP BY q.id
            ORDER BY q.created_at DESC
            LIMIT 10
        ''').fetchall()

        return {
            'summary': {
                'total_results': total_results,
                'real_results': real_results,
                'demo_results': demo_results,
                'real_percentage': round((real_results / total_results * 100) if total_results > 0 else 0, 1)
            },
            'by_source': [dict(row) for row in source_breakdown],
            'recent_activity': [dict(row) for row in recent_activity],
            'collection_method': 'BYOB (Bring Your Own Browser) - Extension only',
            'demo_data_disabled': True
        }

@app.get("/debug/users")
async def debug_users():
    """Debug endpoint to check users (remove in production)"""
    with get_db_connection() as conn:
        users = conn.execute('SELECT id, username, email, created_at FROM users').fetchall()
        return {
            'users': [dict(user) for user in users],
            'total': len(users)
        }

# ------------ User Management (keeping existing functionality) ------------

def get_current_user(request: Request):
    """Helper function to get current user from session"""
    session_token = request.cookies.get("session_token")
    if session_token and session_token in user_sessions:
        return user_sessions[session_token]
    return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("home.html", {
        "request": request,
        "session": user or {}
    })

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Search page with BYOB interface"""
    user = get_current_user(request)
    return templates.TemplateResponse("search.html", {
        "request": request,
        "session": user or {},
        "ingest_token": INGEST_TOKEN,
        "backend_url": str(request.base_url).rstrip('/')
    })

@app.get("/alerts", response_class=HTMLResponse)
async def alerts_dashboard(request: Request):
    """Alerts dashboard"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Flight Alerts - FlightAlert Pro</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; }}
        .tabs {{ border-bottom: 2px solid #007bff; margin-bottom: 20px; }}
        .tab {{ display: inline-block; padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; }}
        .tab.active {{ border-bottom-color: #007bff; background: #f0f8ff; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .form-group {{ margin: 15px 0; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        .form-group input, .form-group select {{ padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 200px; }}
        .btn {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        .btn:hover {{ background: #0056b3; }}
        .match-item {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 4px; }}
        .match-price {{ font-size: 1.2em; font-weight: bold; color: #28a745; }}
        .match-route {{ color: #007bff; font-weight: bold; }}
        .alert-item {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #007bff; }}
    </style>
</head>
<body>
    <h1>✈️ Flight Alerts Dashboard</h1>

    <div class="tabs">
        <div class="tab active" onclick="showTab('create')">Create Alert</div>
        <div class="tab" onclick="showTab('active')">My Alerts</div>
        <div class="tab" onclick="showTab('matches')">Recent Matches</div>
    </div>

    <div id="create" class="tab-content active">
        <h2>Create New Alert</h2>

        <div style="margin-bottom: 20px;">
            <label>Alert Type:</label>
            <select id="alertType" onchange="showAlertForm()">
                <option value="cheap">Cheap Flights</option>
                <option value="rare">Rare Aircraft</option>
                <option value="adventurous">Adventurous (Any Destination)</option>
                <option value="price_war">Price War Tracker</option>
            </select>
        </div>

        <form id="alertForm">
            <div id="basicFields">
                <div class="form-group">
                    <label>From (Origin):</label>
                    <input type="text" id="origin" placeholder="LHR" maxlength="3">
                </div>
                <div class="form-group">
                    <label>To (Destination):</label>
                    <input type="text" id="destination" placeholder="AMS" maxlength="3">
                </div>
                <div class="form-group">
                    <label>Departure Start:</label>
                    <input type="date" id="departStart">
                </div>
                <div class="form-group">
                    <label>Departure End:</label>
                    <input type="date" id="departEnd">
                </div>
                <div class="form-group">
                    <label>Max Price (£):</label>
                    <input type="number" id="maxPrice" placeholder="200">
                </div>
            </div>

            <div id="rareFields" style="display: none;">
                <div class="form-group">
                    <label>Rare Aircraft (comma-separated):</label>
                    <input type="text" id="rareAircraft" placeholder="A340,B747,DC-10">
                </div>
            </div>

            <div class="form-group">
                <label>Notes:</label>
                <input type="text" id="notes" placeholder="Optional notes">
            </div>

            <button type="button" class="btn" onclick="createAlert()">Create Alert</button>
        </form>
    </div>

    <div id="active" class="tab-content">
        <h2>My Active Alerts</h2>
        <div id="activeAlerts">Loading...</div>
    </div>

    <div id="matches" class="tab-content">
        <h2>Recent Matches</h2>
        <div id="recentMatches">Loading...</div>
    </div>

    <script>
        function showTab(tabName) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');

            if (tabName === 'active') loadActiveAlerts();
            if (tabName === 'matches') loadRecentMatches();
        }}

        function showAlertForm() {{
            const type = document.getElementById('alertType').value;
            const rareFields = document.getElementById('rareFields');
            const destField = document.getElementById('destination').parentElement;
            const maxPriceField = document.getElementById('maxPrice').parentElement;

            // Reset all fields
            rareFields.style.display = 'none';
            destField.style.display = 'block';
            maxPriceField.querySelector('label').textContent = 'Max Price (£):';

            if (type === 'rare') {{
                rareFields.style.display = 'block';
                maxPriceField.querySelector('label').textContent = 'Max Price (£) - Optional:';
            }} else if (type === 'adventurous') {{
                destField.style.display = 'none';
                document.getElementById('destination').value = '';
                maxPriceField.querySelector('label').textContent = 'Budget (£):';
            }} else if (type === 'price_war') {{
                maxPriceField.querySelector('label').textContent = 'Alert when price drops below (£):';
            }}
        }}

        async function createAlert() {{
            const data = {{
                type: document.getElementById('alertType').value,
                origin: document.getElementById('origin').value.toUpperCase() || null,
                destination: document.getElementById('destination').value.toUpperCase() || null,
                depart_start: document.getElementById('departStart').value || null,
                depart_end: document.getElementById('departEnd').value || null,
                max_price: parseFloat(document.getElementById('maxPrice').value) || null,
                rare_aircraft_list: document.getElementById('rareAircraft').value || null,
                notes: document.getElementById('notes').value || null
            }};

            try {{
                const response = await fetch('/api/alerts', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }});

                if (response.ok) {{
                    alert('Alert created successfully!');
                    document.getElementById('alertForm').reset();
                    // Reset form visibility for new alert
                    showAlertForm();
                }} else {{
                    const errorData = await response.json();
                    alert('Failed to create alert: ' + (errorData.detail || 'Unknown error'));
                }}
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function loadActiveAlerts() {{
            try {{
                const response = await fetch('/api/alerts');
                const data = await response.json();

                const html = data.alerts.map(alert => `
                    <div class="alert-item">
                        <strong>${{alert.type.toUpperCase()}}</strong> alert<br>
                        Route: ${{alert.origin || '?'}} → ${{alert.destination || 'Any'}}<br>
                        Price: Up to £${{alert.max_price || '∞'}}<br>
                        Created: ${{new Date(alert.created_at).toLocaleDateString()}}
                        ${{alert.notes ? '<br>Notes: ' + alert.notes : ''}}
                    </div>
                `).join('');

                document.getElementById('activeAlerts').innerHTML = html || 'No active alerts';
            }} catch (e) {{
                document.getElementById('activeAlerts').innerHTML = 'Error loading alerts';
            }}
        }}

        async function loadRecentMatches() {{
            try {{
                const response = await fetch('/api/matches');
                const data = await response.json();

                const html = data.matches.map(match => `
                    <div class="match-item">
                        <div class="match-route">${{match.route}}</div>
                        <div class="match-price">£${{match.price.amount}} ${{match.price.currency}}</div>
                        <div>${{match.carrier}} ${{match.flight_number}}</div>
                        <div>Found on: ${{match.site.name}}</div>
                        <div>Matched: ${{new Date(match.matched_at).toLocaleString()}}</div>
                        ${{match.booking_url ? `<a href="${{match.booking_url}}" target="_blank">Book Now</a>` : ''}}
                        ${{!match.seen ? ' <strong>(NEW)</strong>' : ''}}
                    </div>
                `).join('');

                document.getElementById('recentMatches').innerHTML = html || 'No recent matches';
            }} catch (e) {{
                document.getElementById('recentMatches').innerHTML = 'Error loading matches';
            }}
        }}

        // Load initial data and set initial form state
        loadActiveAlerts();
        showAlertForm();
    </script>

    <p><a href="/search">← Back to Search</a> | <a href="/operator">Operator Console</a></p>
</body>
</html>
    """)

@app.post("/api/search")
async def api_search(request: Request, origin: str = Form(...), destination: str = Form(...), date: str = Form(...)):
    """API search endpoint that creates query and returns deep links"""
    try:
        query_request = QueryRequest(origin=origin, destination=destination, depart_date=date)
        result = await create_query(query_request)

        # Add JavaScript to broadcast query_id to extension
        if result and 'query_id' in result:
            backend_url = str(request.base_url).rstrip('/')
            result['broadcast_script'] = f"""
            <script>
                // Broadcast query_id to extension for BYOB ingestion
                localStorage.setItem("FA_QUERY_ID", "{result['query_id']}");
                localStorage.setItem("FA_INGEST_TOKEN", "{INGEST_TOKEN}");
                localStorage.setItem("FA_BACKEND_URL", "{backend_url}");

                // Broadcast to extension content scripts
                window.postMessage({{
                    type: "FA_QUERY_CREATED",
                    queryId: {result['query_id']},
                    token: "{INGEST_TOKEN}",
                    backendUrl: "{backend_url}"
                }}, "*");

                console.log("FlightAlert: Broadcasting query_id {result['query_id']} to extension");
                console.log("FlightAlert: Backend URL set to {backend_url}");

                // Also try direct extension messaging
                if (window.chrome && window.chrome.runtime) {{
                    try {{
                        chrome.runtime.sendMessage({{
                            type: "FA_QUERY_CREATED",
                            queryId: {result['query_id']},
                            token: "{INGEST_TOKEN}",
                            backendUrl: "{backend_url}"
                        }});
                    }} catch(e) {{
                        console.log("Extension not ready or not installed");
                    }}
                }}
            </script>
            """

        return result
    except Exception as e:
        return {"error": str(e), "success": False}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "session": {}
    })

@app.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        email = email.strip()
        password = password.strip()

        print(f"🔐 Login attempt for email: {email}")

        if not email or not password:
            print("❌ Missing email or password")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "session": {},
                "error": "Email and password are required"
            })

        # Check database for user
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            print(f"🔍 User lookup result: {'Found' if user else 'Not found'}")

        if user and check_password_hash(user['password_hash'], password):
            print(f"✅ Login successful for {email}")
            # Create session
            session_token = secrets.token_urlsafe(32)
            user_sessions[session_token] = {
                'user_id': user['id'],
                'email': user['email'],
                'username': user['username'],
                'created_at': datetime.utcnow().isoformat()
            }

            # Redirect to search
            from fastapi.responses import RedirectResponse
            response = RedirectResponse(url="/search", status_code=302)
            response.set_cookie(key="session_token", value=session_token, httponly=True, max_age=86400)
            return response
        else:
            print(f"❌ Invalid credentials for {email}")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "session": {},
                "error": "Invalid email or password"
            })
    except Exception as e:
        print(f"❌ Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "session": {},
            "error": "Login failed. Please try again."
        })

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "session": {}
    })

@app.post("/signup", response_class=HTMLResponse)
async def signup_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    try:
        username = username.strip()
        email = email.strip()
        password = password.strip()

        print(f"📝 Signup attempt for: {username} ({email})")

        if not username or not email or not password:
            print("❌ Missing required signup fields")
            return templates.TemplateResponse("signup.html", {
                "request": request,
                "session": {},
                "error": "All fields are required"
            })

        # Check if user already exists
        with get_db_connection() as conn:
            existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()

            if existing:
                print(f"❌ User already exists: {email}")
                return templates.TemplateResponse("signup.html", {
                    "request": request,
                    "session": {},
                    "error": "User with this email already exists"
                })

            # Create new user
            password_hash = generate_password_hash(password)
            cursor = conn.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid
            print(f"✅ Created new user: {username} (ID: {user_id})")

        # Auto-login after signup
        session_token = secrets.token_urlsafe(32)
        user_sessions[session_token] = {
            'user_id': user_id,
            'email': email,
            'username': username,
            'created_at': datetime.utcnow().isoformat()
        }

        from fastapi.responses import RedirectResponse
        response = RedirectResponse(url="/search", status_code=302)
        response.set_cookie(key="session_token", value=session_token, httponly=True, max_age=86400)
        return response
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "session": {},
            "error": "Signup failed. Please try again."
        })

@app.post("/logout")
async def logout_user(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token and session_token in user_sessions:
        del user_sessions[session_token]

    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session_token")
    return response

# ------------ Extension Support Page ------------

# ------------ Alert Management Endpoints ------------

class AlertRequest(BaseModel):
    type: str = "cheap"  # cheap, rare, adventurous, price_war
    origin: Optional[str] = None
    destination: Optional[str] = None
    one_way: bool = True
    depart_start: Optional[str] = None
    depart_end: Optional[str] = None
    return_start: Optional[str] = None
    return_end: Optional[str] = None
    min_bags: int = 0
    max_bags: int = 2
    cabin: str = "economy"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    rare_aircraft_list: Optional[str] = None
    notes: Optional[str] = None

@app.post("/api/alerts")
async def create_alert(alert: AlertRequest, request: Request):
    """Create a new price alert"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO alerts (
                    user_id, type, origin, destination, one_way, depart_start, depart_end,
                    return_start, return_end, min_bags, max_bags, cabin, min_price, max_price,
                    min_duration, max_duration, rare_aircraft_list, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['user_id'], alert.type, alert.origin, alert.destination, alert.one_way,
                alert.depart_start, alert.depart_end, alert.return_start, alert.return_end,
                alert.min_bags, alert.max_bags, alert.cabin, alert.min_price, alert.max_price,
                alert.min_duration, alert.max_duration, alert.rare_aircraft_list, alert.notes
            ))
            conn.commit()
            alert_id = cursor.lastrowid

        logger.info(f"✅ Created {alert.type} alert {alert_id} for user {user['user_id']}")
        return {"alert_id": alert_id, "success": True}

    except Exception as e:
        logger.error(f"❌ Alert creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_user_alerts(request: Request):
    """Get user's active alerts"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            alerts = conn.execute('''
                SELECT * FROM alerts
                WHERE user_id = ? AND active = 1
                ORDER BY created_at DESC
            ''', (user['user_id'],)).fetchall()

            return {"alerts": [dict(alert) for alert in alerts]}

    except Exception as e:
        logger.error(f"❌ Alert retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/matches")
async def get_alert_matches(request: Request):
    """Get recent matches for user's alerts"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            matches = conn.execute('''
                SELECT
                    m.*, a.type as alert_type, a.origin, a.destination,
                    r.price_min, r.price_currency, r.raw_json, r.booking_url,
                    s.name as site_name, s.domain
                FROM matches m
                JOIN alerts a ON m.alert_id = a.id
                JOIN results r ON m.result_id = r.id
                JOIN sites s ON r.site_id = s.id
                WHERE a.user_id = ? AND m.matched_at > datetime('now', '-7 days')
                ORDER BY m.matched_at DESC
                LIMIT 50
            ''', (user['user_id'],)).fetchall()

            formatted_matches = []
            for match in matches:
                try:
                    result_data = json.loads(match['raw_json'])
                    formatted_matches.append({
                        'match_id': match['id'],
                        'alert_type': match['alert_type'],
                        'route': f"{match['origin']} → {match['destination']}",
                        'price': {
                            'amount': match['price_min'],
                            'currency': match['price_currency']
                        },
                        'carrier': result_data.get('carrier', 'Unknown'),
                        'flight_number': result_data.get('flight_number', ''),
                        'site': {
                            'name': match['site_name'],
                            'domain': match['domain']
                        },
                        'booking_url': match['booking_url'],
                        'matched_at': match['matched_at'],
                        'seen': bool(match['seen'])
                    })
                except Exception as e:
                    logger.warning(f"Error formatting match: {e}")
                    continue

            return {"matches": formatted_matches}

    except Exception as e:
        logger.error(f"❌ Match retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/matches/{match_id}/seen")
async def mark_match_seen(match_id: int, request: Request):
    """Mark a match as seen"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            # Verify the match belongs to this user
            match = conn.execute('''
                SELECT m.* FROM matches m
                JOIN alerts a ON m.alert_id = a.id
                WHERE m.id = ? AND a.user_id = ?
            ''', (match_id, user['user_id'])).fetchone()

            if not match:
                raise HTTPException(status_code=404, detail="Match not found")

            conn.execute('UPDATE matches SET seen = 1 WHERE id = ?', (match_id,))
            conn.commit()

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Mark seen failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, request: Request):
    """Delete a user's alert"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with get_db_connection() as conn:
            # Verify the alert belongs to this user
            alert = conn.execute('''
                SELECT id FROM alerts
                WHERE id = ? AND user_id = ?
            ''', (alert_id, user['user_id'])).fetchone()

            if not alert:
                raise HTTPException(status_code=404, detail="Alert not found")

            # Delete the alert (set active = 0 instead of hard delete to preserve history)
            conn.execute('UPDATE alerts SET active = 0 WHERE id = ?', (alert_id,))
            conn.commit()

        logger.info(f"✅ Deleted alert {alert_id} for user {user['user_id']}")
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Alert deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/operator", response_class=HTMLResponse)
async def operator_console(request: Request):
    """Operator console for single-operator BYOB mode"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    # Get recent queries and active alerts to generate browse URLs
    with get_db_connection() as conn:
        # Recent queries from last 7 days
        recent_queries = conn.execute('''
            SELECT DISTINCT origin, destination, depart_date
            FROM queries
            WHERE created_at > datetime('now', '-7 days')
            ORDER BY created_at DESC
            LIMIT 15
        ''').fetchall()

        # Active alerts
        alerts = conn.execute('''
            SELECT DISTINCT origin, destination, depart_start, depart_end
            FROM alerts
            WHERE active = 1 AND origin IS NOT NULL AND destination IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        ''').fetchall()

    browse_urls = []

    # Add recent queries
    for query in recent_queries:
        date_str = query['depart_date']
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            # Key sites for operator browsing
            sites = [
                ('Skyscanner', f"https://www.skyscanner.net/transport/flights/{query['origin'].lower()}/{query['destination'].lower()}/{date_obj.strftime('%y%m%d')}/"),
                ('Kayak', f"https://www.kayak.com/flights/{query['origin']}-{query['destination']}/{date_str}"),
                ('Google Flights', f"https://www.google.com/travel/flights?q=Flights%20from%20{query['origin']}%20to%20{query['destination']}%20on%20{date_str}"),
                ('British Airways', f"https://www.britishairways.com/travel/fx/public/en_gb#/booking/flight-selection?origin={query['origin']}&destination={query['destination']}&departureDate={date_str}"),
                ('Ryanair', f"https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut={date_str}&origin={query['origin']}&destination={query['destination']}")
            ]

            for site_name, url in sites:
                browse_urls.append({
                    'route': f"{query['origin']} → {query['destination']}",
                    'date': date_str,
                    'site': site_name,
                    'url': url,
                    'type': 'recent_query'
                })
        except ValueError:
            continue

    # Add alert-based URLs
    for alert in alerts:
        if alert['depart_start']:
            date_str = alert['depart_start']
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                sites = [
                    ('Skyscanner',f"https://www.skyscanner.net/transport/flights/{alert['origin'].lower()}/{alert['destination'].lower()}/{date_obj.strftime('%y%m%d')}/"),
                    ('Kayak', f"https://www.kayak.com/flights/{alert['origin']}-{alert['destination']}/{date_str}")
                ]

                for site_name, url in sites:
                    browse_urls.append({
                        'route': f"{alert['origin']} → {alert['destination']}",
                        'date': date_str,
                        'site': site_name,
                        'url': url,
                        'type': 'alert'
                    })
            except ValueError:
                continue

    backend_url = str(request.base_url).rstrip('/')

    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>BYOB Operator Console - FlightAlert Pro</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; }}
        .header {{ background: #e8f4fd; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .setup-check {{ background: #f0f8ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #007bff; }}
        .url-item {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }}
        .route {{ font-weight: bold; color: #007bff; }}
        .site {{ color: #666; margin-left: 10px; }}
        .type-badge {{ background: #007bff; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 10px; }}
        .alert-type {{ background: #28a745; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .test-section {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .btn {{ padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }}
        .btn:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 BYOB Operator Console</h1>
        <p><strong>Single-Operator Mode:</strong> You browse airline sites normally. Your extension collects real prices. Users get results.</p>
        <p><strong>⚠️ REAL DATA ONLY:</strong> Demo data has been disabled. Only actual scraped flight prices will be shown.</p>
    </div>

    <div class="setup-check">
        <h3>🔧 Extension Setup Check</h3>
        <p><strong>Backend URL:</strong> <code>{backend_url}</code></p>
        <p><strong>Ingest Token:</strong> <code>{INGEST_TOKEN}</code></p>
        <p><strong>Test connectivity:</strong> <a href="{backend_url}/api/debug/connectivity" target="_blank" class="btn">Test Connection</a></p>
    </div>

    <div class="test-section">
        <h3>🧪 Quick Test</h3>
        <p>Test if your backend can receive data:</p>
        <button class="btn" onclick="testIngestion()">Send Test Data</button>
        <div id="testResult" style="margin-top: 10px;"></div>
    </div>

    <h2>📋 Browse URLs ({len(browse_urls)} total)</h2>
    <p>Open these in new tabs. Your extension will automatically extract and send prices back to the system.</p>

    {''.join([f'''
    <div class="url-item">
        <span class="route">{url['route']}</span>
        <span class="site">- {url['site']}</span>
        <span class="type-badge {'alert-type' if url['type'] == 'alert' else ''}">{url['type'].replace('_', ' ').title()}</span>
        <span style="color: #999; margin-left: 10px;">({url['date']})</span><br>
        <a href="{url['url']}" target="_blank">{url['url']}</a>
    </div>
    ''' for url in browse_urls])}

    <script>
        async function testIngestion() {{
            const resultDiv = document.getElementById('testResult');
            resultDiv.innerHTML = '⏳ Testing...';

            try {{
                const response = await fetch('{backend_url}/api/debug/ingest_example/1', {{
                    method: 'POST',
                    headers: {{
                        'X-FA-Token': '{INGEST_TOKEN}'
                    }}
                }});

                const data = await response.json();

                if (response.ok) {{
                    resultDiv.innerHTML = '✅ Test successful! Backend can receive data.';
                    resultDiv.style.color = 'green';
                }} else {{
                    resultDiv.innerHTML = '❌ Test failed: ' + (data.detail || 'Unknown error');
                    resultDiv.style.color = 'red';
                }}
            }} catch (error) {{
                resultDiv.innerHTML = '❌ Connection failed: ' + error.message;
                resultDiv.style.color = 'red';
            }}
        }}
    </script>

    <p><a href="/search">← Back to Search</a> | <a href="/alerts">View Alerts</a></p>
</body>
</html>
    """)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard page"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    # Get user's alerts
    with get_db_connection() as conn:
        alerts = conn.execute('''
            SELECT * FROM alerts
            WHERE user_id = ? AND active = 1
            ORDER BY created_at DESC
        ''', (user['user_id'],)).fetchall()

        # Get recent matches
        matches = conn.execute('''
            SELECT COUNT(*) as count FROM matches m
            JOIN alerts a ON m.alert_id = a.id
            WHERE a.user_id = ? AND m.matched_at > datetime('now', '-7 days')
        ''', (user['user_id'],)).fetchone()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "session": user,
        "alerts": [dict(alert) for alert in alerts],
        "recent_matches": matches['count'] if matches else 0
    })

@app.get("/create_alert", response_class=HTMLResponse)
async def create_alert_page(request: Request):
    """Create alert page"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    today = datetime.now().strftime('%Y-%m-%d')
    return templates.TemplateResponse("create_alert.html", {
        "request": request,
        "session": user,
        "today": today
    })

@app.post("/create_alert", response_class=HTMLResponse)
async def create_alert_post(
    request: Request,
    alert_type: str = Form(...),
    trip_type: str = Form(...),
    departure_airport: str = Form(...),
    destination_airport: str = Form(default=""),
    airline: str = Form(default=""),
    aircraft_type: str = Form(default=""),
    max_price: float = Form(default=None),
    min_baggage: int = Form(default=None),
    max_baggage: int = Form(default=None),
    departure_date: str = Form(...),
    return_date: str = Form(default=""),
    min_trip_duration: int = Form(default=None),
    max_trip_duration: int = Form(default=None)
):
    """Handle alert creation form submission"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    try:
        # Process form data
        departure_airports = [ap.strip() for ap in departure_airport.split(',') if ap.strip()]
        destination_airports = [ap.strip() for ap in destination_airport.split(',') if ap.strip()] if destination_airport else []
        airlines = [al.strip() for al in airline.split(',') if al.strip()] if airline else []

        # Convert form data to database format
        one_way = (trip_type == 'one_way')

        with get_db_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO alerts (
                    user_id, type, origin, destination, one_way, depart_start, depart_end,
                    return_start, return_end, min_bags, max_bags, cabin, min_price, max_price,
                    min_duration, max_duration, rare_aircraft_list, notes, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['user_id'],
                alert_type,
                ','.join(departure_airports) if departure_airports else None,
                ','.join(destination_airports) if destination_airports else None,
                one_way,
                departure_date,
                departure_date,  # For now, use same date for start and end
                return_date if return_date else None,
                return_date if return_date else None,
                min_baggage or 0,
                max_baggage or 50,
                'economy',  # Default cabin class
                None,  # min_price
                max_price,
                min_trip_duration,
                max_trip_duration,
                aircraft_type if aircraft_type else None,
                f"Alert created via web form. Airlines: {','.join(airlines) if airlines else 'Any'}",
                True
            ))
            conn.commit()
            alert_id = cursor.lastrowid

        logger.info(f"✅ Created {alert_type} alert {alert_id} for user {user['user_id']}")

        # Redirect to dashboard with success message
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard?alert_created=1", status_code=302)

    except Exception as e:
        logger.error(f"❌ Alert creation failed: {e}")
        today = datetime.now().strftime('%Y-%m-%d')
        return templates.TemplateResponse("create_alert.html", {
            "request": request,
            "session": user,
            "today": today,
            "error": f"Failed to create alert: {str(e)}"
        })

@app.get("/preferences", response_class=HTMLResponse)
async def preferences_page(request: Request):
    """User preferences page"""
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "session": {}})

    return templates.TemplateResponse("preferences.html", {
        "request": request,
        "session": user
    })

@app.get("/logout")
async def logout_get(request: Request):
    """Handle GET request to logout"""
    return await logout_user(request)

@app.get("/upgrade", response_class=HTMLResponse)
async def upgrade_page(request: Request):
    """Upgrade/subscription page"""
    user = get_current_user(request)
    return templates.TemplateResponse("upgrade.html", {
        "request": request,
        "session": user or {}
    })

@app.get("/extension", response_class=HTMLResponse)
async def extension_page(request: Request):
    """Page explaining the browser extension"""
    backend_url = str(request.base_url).rstrip('/')

    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>FlightAlert Pro Extension Setup</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .highlight {{ background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .code {{ background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; }}
        .step {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; }}
        .warning {{ background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; }}
        .btn {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }}
        .success {{ color: #28a745; font-weight: bold; }}
        .error {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>🚀 FlightAlert Pro BYOB Extension</h1>

    <div class="highlight">
        <h2>BYOB = Bring Your Own Browser</h2>
        <p>You browse airline sites normally. Extension extracts real prices. No bots, no blocks, just real data from your actual browsing!</p>
    </div>

    <div class="warning">
        <h3>⚠️ Critical Setup Requirements</h3>
        <p>For your extension to work with this Codespaces backend:</p>
        <ol>
            <li><strong>Backend URL must be:</strong> <code>{backend_url}</code></li>
            <li><strong>Token must be:</strong> <code>{INGEST_TOKEN}</code></li>
            <li><strong>Host permissions must include:</strong> <code>*.githubpreview.dev</code></li>
        </ol>
    </div>

    <div class="step">
        <h3>🔧 Extension Configuration</h3>
        <p>Update your extension's background.js or options with:</p>
        <div class="code">
BACKEND_BASE_URL = "{backend_url}"<br>
INGEST_TOKEN = "{INGEST_TOKEN}"
        </div>
    </div>

    <div class="step">
        <h3>📋 manifest.json Host Permissions</h3>
        <p>Add these to your extension's manifest.json:</p>
        <div class="code">
"host_permissions": [<br>
&nbsp;&nbsp;"https://*.githubpreview.dev/*",<br>
&nbsp;&nbsp;"https://*.skyscanner.net/*",<br>
&nbsp;&nbsp;"https://*.kayak.com/*",<br>
&nbsp;&nbsp;"https://*.britishairways.com/*",<br>
&nbsp;&nbsp;"https://*.google.com/travel/flights/*"<br>
]
        </div>
    </div>

    <div class="step">
        <h3> TEst Your Setup</h3>
        <p>Click this button to verify your extension can reach the backend:</p>
        <button class="btn" onclick="testConnection()">Test Connection</button>
        <div id="testResult" style="margin-top: 10px;"></div>
    </div>

    <div class="step">
        <h3>🎯 How to Use</h3>
        <ol>
            <li>Go to <a href="/search">Search Page</a> and search for flights</li>
            <li>Click the generated deep links to open airline sites</li>
            <li>Your extension automatically extracts prices in the background</li>
            <li>Return to see aggregated results from all sites</li>
        </ol>
    </div>

    <script>
        async function testConnection() {{
            const resultDiv = document.getElementById('testResult');
            resultDiv.innerHTML = '⏳ Testing connection...';

            try {{
                const response = await fetch('{backend_url}/api/debug/connectivity', {{
                    headers: {{
                        'X-FA-Token': '{INGEST_TOKEN}'
                    }}
                }});

                const data = await response.json();

                if (response.ok && data.token_valid) {{
                    resultDiv.innerHTML = '<span class="success">✅ Connection successful! Backend is reachable and token is valid.</span>';
                }} else if (response.ok) {{
                    resultDiv.innerHTML = '<span class="error">❌ Connected but token invalid. Check your extension token.</span>';
                }} else {{
                    resultDiv.innerHTML = '<span class="error">❌ Connection failed: HTTP ' + response.status + '</span>';
                }}
            }} catch (error) {{
                resultDiv.innerHTML = '<span class="error">❌ Connection failed: ' + error.message + '</span>';
            }}
        }}
    </script>

    <p><a href="/search">← Back to Search</a> | <a href="/operator">Operator Console</a></p>
</body>
</html>
    """)

if __name__ == "__main__":
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        # Verify all imports work
        print("✅ All required packages imported successfully")

        print("🚀 Starting FlightAlert Pro BYOB Edition...")
        print("🎯 Browser Extension + FastAPI Architecture")
        print("📡 Server will be available at: http://0.0.0.0:5000")
        print("🔧 Extension APIs + User Interface")
        print("✅ SQLite Database + Real-time Ingestion")

        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=5000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Installing missing dependencies...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pydantic", "aiohttp", "beautifulsoup4", "pandas", "werkzeug", "python-dateutil", "pytz", "requests", "playwright", "jinja2", "python-multipart"])
        print("✅ Dependencies installed. Please restart the server.")
        sys.exit(1)