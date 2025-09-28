#!/usr/bin/env python3
"""
Database models for Flight Alert App
"""

from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
import sqlite3
import json
import os

class SubscriptionType(str, Enum):
    MONTHLY = "monthly"
    LIFETIME = "lifetime"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class User(BaseModel):
    id: Optional[int] = None
    email: str
    subscription_type: Optional[SubscriptionType] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.EXPIRED
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    created_at: datetime = datetime.now()
    api_calls_today: int = 0
    last_api_call: Optional[datetime] = None

class FlightQuery(BaseModel):
    departure: str
    arrival: str
    date: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    airline: Optional[str] = None
    max_duration: Optional[int] = None
    alert_price: Optional[float] = None
    currency: str = "GBP"
    rare_aircraft_only: bool = False

class PaymentRequest(BaseModel):
    email: str
    subscription_type: SubscriptionType

class DatabaseManager:
    def __init__(self, db_path: str = "flight_alert.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                subscription_type TEXT,
                subscription_status TEXT DEFAULT 'expired',
                subscription_start TEXT,
                subscription_end TEXT,
                stripe_customer_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                api_calls_today INTEGER DEFAULT 0,
                last_api_call TEXT
            )
        ''')
        
        # Flight searches table (for analytics)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flight_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                departure TEXT NOT NULL,
                arrival TEXT NOT NULL,
                search_date TEXT,
                filters TEXT,
                results_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Price alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                departure TEXT NOT NULL,
                arrival TEXT NOT NULL,
                target_price REAL NOT NULL,
                currency TEXT DEFAULT 'GBP',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                triggered_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0],
                email=row[1],
                subscription_type=row[2],
                subscription_status=row[3],
                subscription_start=datetime.fromisoformat(row[4]) if row[4] else None,
                subscription_end=datetime.fromisoformat(row[5]) if row[5] else None,
                stripe_customer_id=row[6],
                created_at=datetime.fromisoformat(row[7]),
                api_calls_today=row[8],
                last_api_call=datetime.fromisoformat(row[9]) if row[9] else None
            )
        return None
    
    def create_user(self, user: User) -> User:
        """Create new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (email, subscription_type, subscription_status, 
                              subscription_start, subscription_end, stripe_customer_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user.email,
            user.subscription_type,
            user.subscription_status,
            user.subscription_start.isoformat() if user.subscription_start else None,
            user.subscription_end.isoformat() if user.subscription_end else None,
            user.stripe_customer_id
        ))
        
        user.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user
    
    def update_user_subscription(self, user_id: int, subscription_type: SubscriptionType, 
                               stripe_customer_id: str) -> bool:
        """Update user subscription"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now()
        if subscription_type == SubscriptionType.LIFETIME:
            end_date = start_date + timedelta(days=36500)  # 100 years
        else:  # Monthly
            end_date = start_date + timedelta(days=30)
        
        cursor.execute('''
            UPDATE users 
            SET subscription_type = ?, subscription_status = 'active', 
                subscription_start = ?, subscription_end = ?, stripe_customer_id = ?
            WHERE id = ?
        ''', (
            subscription_type,
            start_date.isoformat(),
            end_date.isoformat(),
            stripe_customer_id,
            user_id
        ))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def increment_api_calls(self, user_id: int) -> bool:
        """Increment API call count for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET api_calls_today = api_calls_today + 1, last_api_call = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

# Global database instance
db = DatabaseManager()