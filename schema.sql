-- Flight Alert App Database Schema
-- SQLite database schema with all required tables

-- users
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT,
  is_admin INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- queries (search requests)
CREATE TABLE IF NOT EXISTS queries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  departure_iata TEXT NOT NULL,
  arrival_iata TEXT NOT NULL,
  depart_date TEXT NOT NULL,
  return_date TEXT,
  passengers INTEGER DEFAULT 1,
  cabin TEXT DEFAULT 'ECONOMY',
  min_price REAL,
  max_price REAL,
  alert_price REAL,
  currency TEXT DEFAULT 'GBP',
  rare_aircraft_filter TEXT,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

-- itineraries (results)
CREATE TABLE IF NOT EXISTS itineraries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query_id INTEGER,
  provider TEXT,
  deep_link TEXT,
  url TEXT,
  price REAL,
  currency TEXT,
  price_minor INTEGER,
  legs_json TEXT,
  fare_json TEXT,
  dedupe_key TEXT,
  confidence REAL DEFAULT 0.0,
  source_domain TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(query_id) REFERENCES queries(id)
);
CREATE INDEX IF NOT EXISTS idx_itin_dedupe ON itineraries(dedupe_key);

-- airlines (map IATA/ICAO to full name)
CREATE TABLE IF NOT EXISTS airlines (
  code TEXT PRIMARY KEY,
  name TEXT,
  domain TEXT
);

-- deep link templates per airline (for validated airline-only links)
CREATE TABLE IF NOT EXISTS airline_deeplinks (
  airline_code TEXT PRIMARY KEY,
  template_url TEXT,  -- e.g. https://www.britishairways.com/travel/{orig}/{dest}/{date}
  validated INTEGER DEFAULT 0
);

-- payments / subscriptions
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  stripe_session_id TEXT,
  stripe_payment_intent TEXT,
  product_type TEXT, -- 'monthly' | 'lifetime'
  amount INTEGER, -- minor units pence
  currency TEXT,
  status TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

-- rare aircrafts
CREATE TABLE IF NOT EXISTS rare_aircrafts (
  code TEXT PRIMARY KEY,   -- e.g., "A380", "B747-8", "A321neoLR"
  manufacturer TEXT,
  model TEXT,
  popularity_score INTEGER DEFAULT 0
);

-- Insert sample airline data
INSERT OR IGNORE INTO airlines (code, name, domain) VALUES 
('BA', 'British Airways', 'britishairways.com'),
('FR', 'Ryanair', 'ryanair.com'),  
('U2', 'easyJet', 'easyjet.com'),
('AA', 'American Airlines', 'aa.com'),
('DL', 'Delta Air Lines', 'delta.com'),
('UA', 'United Airlines', 'united.com'),
('EK', 'Emirates', 'emirates.com'),
('LH', 'Lufthansa', 'lufthansa.com'),
('AF', 'Air France', 'airfrance.com'),
('KL', 'KLM', 'klm.com');

-- Insert sample rare aircraft data
INSERT OR IGNORE INTO rare_aircrafts (code, manufacturer, model, popularity_score) VALUES
('A380', 'Airbus', 'A380-800', 95),
('B747-8', 'Boeing', '747-8', 90),
('A350-1000', 'Airbus', 'A350-1000', 85),
('B787-10', 'Boeing', '787-10 Dreamliner', 80),
('A321neoLR', 'Airbus', 'A321neo Long Range', 75),
('B777-9', 'Boeing', '777-9', 70),
('A220-300', 'Airbus', 'A220-300', 65);

-- Insert sample deep link templates  
INSERT OR IGNORE INTO airline_deeplinks (airline_code, template_url, validated) VALUES
('BA', 'https://www.britishairways.com/travel/flights/search?from={orig}&to={dest}&departure={date}&passengers={passengers}', 1),
('AA', 'https://www.aa.com/booking/search?from={orig}&to={dest}&departure={date}&passengers={passengers}', 1),
('DL', 'https://www.delta.com/flight-search/book-a-flight?from={orig}&to={dest}&departure={date}&passengers={passengers}', 1),
('UA', 'https://www.united.com/en/us/flights/search?from={orig}&to={dest}&departure={date}&passengers={passengers}', 1),
('EK', 'https://www.emirates.com/us/english/search/book?from={orig}&to={dest}&departure={date}&passengers={passengers}', 1);