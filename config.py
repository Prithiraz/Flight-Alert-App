#!/usr/bin/env python3
"""
Configuration management for Flight Alert App
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Stripe Configuration
    stripe_secret_key: str = "sk_test_demo_key"
    stripe_publishable_key: str = "pk_test_demo_key"
    stripe_webhook_secret: str = "whsec_demo_secret"
    
    # Subscription Prices
    monthly_price_gbp: float = 5.00
    lifetime_price_gbp: float = 70.00
    
    # JWT Configuration
    jwt_secret_key: str = "flight_alert_super_secret_key_change_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # API Keys for Real Flight Data
    amadeus_client_id: Optional[str] = None
    amadeus_client_secret: Optional[str] = None
    skyscanner_api_key: Optional[str] = None
    flightaware_api_key: Optional[str] = None
    
    # Currency Exchange API
    exchange_rate_api_key: Optional[str] = None
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Database Configuration
    database_url: str = "sqlite:///./flight_alert.db"
    
    # Application Settings
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()