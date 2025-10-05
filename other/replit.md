# FlightAlert Pro

## Overview

FlightAlert Pro is a comprehensive flight price monitoring and alerting system built with a BYOB (Bring Your Own Browser) architecture. The application combines a FastAPI backend with browser extension support for real-time flight data collection and price tracking. Users can create flight alerts, monitor price wars between airlines, and receive notifications when flight prices drop below their specified thresholds.

The system employs a multi-layered approach to flight data collection, utilizing browser extensions for data ingestion, Playwright for validation scraping, and multiple fallback mechanisms to ensure reliable price monitoring across 100+ flight booking websites and airline portals.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### September 25, 2025
- **Console Error Cleanup**: Completely eliminated repeated API error spam in console logs
- **Smart Rate Limiting**: Added intelligent retry logic for failed API services (Amadeus, FlightAPI)
- **Improved Error Handling**: APIs now fail gracefully with informative one-time warnings instead of repeated errors
- **API Management**: Fixed Amadeus 401 authentication failures and FlightAPI 404 errors with proper fallback behavior
- **System Reliability**: Enhanced overall application stability with cleaner logging and better resource management

## System Architecture

### Backend Framework
- **FastAPI with Uvicorn**: Asynchronous web framework providing RESTful APIs and real-time data processing
- **SQLite Database**: Lightweight relational database storing user accounts, flight alerts, airport data, and collected flight information
- **Background Job System**: Async worker queues for non-blocking flight data processing and alert management

### Data Collection Strategy
- **BYOB Architecture**: Primary data collection through browser extensions that users install to gather real-time flight prices
- **Playwright Integration**: Headless browser automation for validation scraping and fallback data collection
- **Multi-Source Scraping**: Support for 100+ flight booking sites including Skyscanner, Kayak, Expedia, and direct airline websites
- **Site Configuration Management**: JSON-based configuration system for CSS selectors, URL patterns, and anti-bot detection

### Frontend Architecture
- **Server-Side Rendering**: Jinja2 templates for user interface rendering
- **RESTful API Layer**: JSON APIs for frontend-backend communication
- **Real-time Updates**: Polling-based system for live flight price updates
- **Responsive Design**: Mobile-friendly interface for flight search and alert management

### Authentication & Security
- **Password Hashing**: Scrypt-based password security with salt
- **Session Management**: Server-side session handling for user authentication
- **Bot Protection**: User-agent rotation, request throttling, and anti-detection measures for scraping operations

### Database Schema
- **Users Table**: User accounts with subscription tiers and XP gamification
- **Alerts Table**: Flight alert configurations with price thresholds and notification settings
- **Airports Table**: Comprehensive airport database with IATA/ICAO codes
- **Flight Data Tables**: Real-time flight prices and historical data storage

### Monitoring & Health
- **Health Monitoring**: Automated scraper performance tracking and site availability checks
- **Selector Updates**: Dynamic CSS selector updating when websites change their structure
- **Debug Systems**: HTML capture and analysis for troubleshooting scraping issues
- **Performance Metrics**: Success rate tracking and response time monitoring

## External Dependencies

### Core Web Framework
- **FastAPI**: Modern async web framework for API development
- **Uvicorn**: ASGI server for FastAPI applications
- **Pydantic**: Data validation and serialization

### Web Scraping & Automation
- **Playwright**: Browser automation for headless scraping and validation
- **BeautifulSoup4**: HTML parsing and CSS selector processing
- **aiohttp**: Async HTTP client for concurrent requests
- **requests**: HTTP library for simple web requests
- **lxml**: XML/HTML parsing engine

### Data Processing
- **pandas**: Data manipulation and airport database processing
- **python-dateutil**: Date parsing and manipulation for flight schedules
- **pytz**: Timezone handling for international flight data

### Reliability & Performance
- **tenacity**: Retry mechanisms with exponential backoff
- **fake-useragent**: User-agent rotation for bot detection avoidance
- **validators**: URL and data validation utilities

### Development & Monitoring
- **python-dotenv**: Environment variable management
- **backoff**: Backoff strategies for failed requests

The application maintains a comprehensive airport database loaded from CSV files and uses a sophisticated site configuration system to adapt to changes in flight booking websites. The BYOB architecture reduces server load while providing users with real-time, accurate flight price data through their own browsing activities.