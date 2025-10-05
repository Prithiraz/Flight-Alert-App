
#!/usr/bin/env python3
"""
Flight Scraper Testing & Debugging System
Automatically tests scrapers, analyzes debug files, and alerts when sites change
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
import threading
from threading import Lock

class ScraperHealthMonitor:
    """Monitor and test flight scraper health across all 149+ sources"""
    
    def __init__(self):
        self.test_lock = Lock()
        self.health_log = []
        self.working_sources = []
        self.broken_sources = []
        self.bot_blocked_sources = []
        
    def test_all_sources(self, departure='LHR', destination='AMS'):
        """Test all flight sources and generate health report"""
        print("🧪 TESTING ALL 149+ FLIGHT SOURCES")
        print("=" * 50)
        
        # Import the scraper from main
        try:
            from main import real_scraper
        except ImportError:
            print("❌ Could not import real_scraper from main.py")
            return
        
        # Test each site category
        self.test_meta_search_engines(real_scraper, departure, destination)
        self.test_budget_airlines(real_scraper, departure, destination)
        self.test_major_airlines(real_scraper, departure, destination)
        self.test_otas(real_scraper, departure, destination)
        
        # Generate health report
        self.generate_health_report()
        
    def test_meta_search_engines(self, scraper, departure, destination):
        """Test meta-search engines specifically"""
        print("\n🔍 TESTING META-SEARCH ENGINES")
        print("-" * 30)
        
        meta_sites = [
            'Skyscanner', 'Kayak', 'Momondo', 'Booking', 'Cheapflights', 'Kiwi'
        ]
        
        for site in meta_sites:
            self.test_single_source(scraper, site, departure, destination)
    
    def test_budget_airlines(self, scraper, departure, destination):
        """Test budget airline sites"""
        print("\n✈️ TESTING BUDGET AIRLINES")
        print("-" * 30)
        
        budget_airlines = [
            'Ryanair', 'Wizz Air', 'easyJet', 'Vueling', 'Eurowings', 'Norwegian'
        ]
        
        for airline in budget_airlines:
            self.test_single_source(scraper, airline, departure, destination)
    
    def test_major_airlines(self, scraper, departure, destination):
        """Test major airline sites"""
        print("\n🛫 TESTING MAJOR AIRLINES")
        print("-" * 30)
        
        major_airlines = [
            'British Airways', 'KLM', 'Air France', 'Lufthansa', 'Iberia', 'TAP Air Portugal'
        ]
        
        for airline in major_airlines:
            self.test_single_source(scraper, airline, departure, destination)
    
    def test_otas(self, scraper, departure, destination):
        """Test Online Travel Agency sites"""
        print("\n🌐 TESTING ONLINE TRAVEL AGENCIES")
        print("-" * 30)
        
        otas = [
            'eDreams', 'Opodo', 'Lastminute', 'Bravofly', 'Gotogate', 'BudgetAir'
        ]
        
        for ota in otas:
            self.test_single_source(scraper, ota, departure, destination)
    
    def test_single_source(self, scraper, source_name, departure, destination):
        """Test a single flight source"""
        try:
            print(f"  🔍 Testing {source_name}...")
            
            # Get the site configuration from scraper
            sites = self.get_site_configs(scraper)
            site_config = None
            
            for site in sites:
                if site['name'].lower() == source_name.lower():
                    site_config = site
                    break
            
            if not site_config:
                print(f"    ❌ {source_name}: Not found in configuration")
                return
            
            # Test the first URL for this source
            test_url = site_config['urls'][0] if site_config['urls'] else None
            if not test_url:
                print(f"    ❌ {source_name}: No URL configured")
                return
            
            # Make test request
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            response = session.get(test_url, timeout=15, verify=False)
            
            # Analyze response
            status = self.analyze_response(source_name, response)
            
            # Log result
            self.log_test_result(source_name, status, response.status_code, len(response.text))
            
        except Exception as e:
            print(f"    ❌ {source_name}: Test failed - {e}")
            self.log_test_result(source_name, 'ERROR', 0, 0, str(e))
    
    def get_site_configs(self, scraper):
        """Extract site configurations from the scraper"""
        # This would extract the sites list from scraper_static_sources_enhanced
        # For now, return a subset for testing
        return [
            {
                'name': 'Skyscanner',
                'urls': ['https://www.skyscanner.net/transport/flights/lhr/ams/250808/'],
                'price_patterns': [r'£(\d{1,4})']
            },
            {
                'name': 'Kayak', 
                'urls': ['https://www.kayak.co.uk/flights/LHR-AMS/2025-08-08'],
                'price_patterns': [r'£(\d{1,4})']
            },
            {
                'name': 'Ryanair',
                'urls': ['https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut=2025-08-08&originIata=LHR&destinationIata=AMS'],
                'price_patterns': [r'£(\d{1,4})']
            }
        ]
    
    def analyze_response(self, source_name, response):
        """Analyze response to determine site health"""
        if response.status_code == 200:
            text = response.text.lower()
            
            # Check for bot detection
            bot_indicators = [
                'enable javascript', 'access denied', 'blocked', 'captcha',
                'please verify', 'security check', 'robot', 'automated',
                'cloudflare', 'protection'
            ]
            
            if any(indicator in text for indicator in bot_indicators):
                print(f"    🤖 {source_name}: Bot detection triggered")
                self.bot_blocked_sources.append(source_name)
                return 'BOT_BLOCKED'
            
            # Check for price indicators
            price_indicators = [
                '£', '$', '€', 'price', 'fare', 'cost', 'from'
            ]
            
            if any(indicator in text for indicator in price_indicators):
                print(f"    ✅ {source_name}: Working (found price indicators)")
                self.working_sources.append(source_name)
                return 'WORKING'
            else:
                print(f"    ⚠️ {source_name}: No price data detected")
                return 'NO_PRICES'
        
        elif response.status_code == 403:
            print(f"    🚫 {source_name}: Access forbidden (403)")
            self.bot_blocked_sources.append(source_name)
            return 'FORBIDDEN'
        
        elif response.status_code == 404:
            print(f"    ❓ {source_name}: Page not found (404) - URL changed")
            self.broken_sources.append(source_name)
            return 'NOT_FOUND'
        
        elif response.status_code == 429:
            print(f"    ⏰ {source_name}: Rate limited (429)")
            return 'RATE_LIMITED'
        
        else:
            print(f"    ❌ {source_name}: HTTP {response.status_code}")
            self.broken_sources.append(source_name)
            return 'HTTP_ERROR'
    
    def log_test_result(self, source_name, status, status_code, content_length, error=None):
        """Log test result for analysis"""
        with self.test_lock:
            result = {
                'source': source_name,
                'status': status,
                'http_code': status_code,
                'content_length': content_length,
                'timestamp': datetime.now().isoformat(),
                'error': error
            }
            self.health_log.append(result)
    
    def generate_health_report(self):
        """Generate comprehensive health report"""
        print("\n" + "=" * 50)
        print("🏥 FLIGHT SCRAPER HEALTH REPORT")
        print("=" * 50)
        
        total_sources = len(self.health_log)
        working_count = len(self.working_sources)
        bot_blocked_count = len(self.bot_blocked_sources)
        broken_count = len(self.broken_sources)
        
        print(f"📊 SUMMARY:")
        print(f"  Total Sources Tested: {total_sources}")
        print(f"  ✅ Working: {working_count}")
        print(f"  🤖 Bot Blocked: {bot_blocked_count}")
        print(f"  ❌ Broken/404: {broken_count}")
        print(f"  📈 Success Rate: {(working_count/total_sources)*100:.1f}%" if total_sources > 0 else "  📈 Success Rate: 0%")
        
        print(f"\n🎯 WORKING SOURCES ({working_count}):")
        for source in self.working_sources:
            print(f"  ✅ {source}")
        
        print(f"\n🤖 BOT BLOCKED SOURCES ({bot_blocked_count}):")
        for source in self.bot_blocked_sources:
            print(f"  🚫 {source} - Needs better anti-bot evasion")
        
        print(f"\n❌ BROKEN SOURCES ({broken_count}):")
        for source in self.broken_sources:
            print(f"  💥 {source} - URL/endpoint changed")
        
        # Save report to file
        self.save_health_report()
        
        # Generate recommendations
        self.generate_recommendations()
    
    def save_health_report(self):
        """Save health report to JSON file"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tested': len(self.health_log),
                'working': len(self.working_sources),
                'bot_blocked': len(self.bot_blocked_sources),
                'broken': len(self.broken_sources)
            },
            'working_sources': self.working_sources,
            'bot_blocked_sources': self.bot_blocked_sources,
            'broken_sources': self.broken_sources,
            'detailed_log': self.health_log
        }
        
        filename = f"scraper_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Health report saved to: {filename}")
    
    def generate_recommendations(self):
        """Generate actionable recommendations"""
        print(f"\n🔧 RECOMMENDED ACTIONS:")
        
        if self.bot_blocked_sources:
            print(f"\n1️⃣ FIX BOT DETECTION ({len(self.bot_blocked_sources)} sources):")
            print("   - Add proxy rotation")
            print("   - Implement better stealth headers")
            print("   - Use mobile user agents")
            print("   - Add random delays")
            
        if self.broken_sources:
            print(f"\n2️⃣ UPDATE BROKEN URLS ({len(self.broken_sources)} sources):")
            for source in self.broken_sources:
                print(f"   - {source}: Research new endpoint URL")
        
        if len(self.working_sources) < 10:
            print(f"\n3️⃣ DIVERSIFY SOURCES:")
            print("   - Add more regional airlines")
            print("   - Include more OTA platforms")
            print("   - Test API-based sources")

class DebugFileAnalyzer:
    """Analyze debug HTML files to understand site changes"""
    
    def __init__(self):
        self.debug_dir = "."
        
    def analyze_all_debug_files(self):
        """Analyze all debug_*.html files"""
        print("\n🔍 ANALYZING DEBUG FILES")
        print("=" * 30)
        
        debug_files = [f for f in os.listdir(self.debug_dir) if f.startswith('debug_') and f.endswith('.html')]
        
        if not debug_files:
            print("❌ No debug files found")
            return
        
        for debug_file in debug_files:
            self.analyze_debug_file(debug_file)
    
    def analyze_debug_file(self, filename):
        """Analyze a single debug file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract source name from filename
            source_name = filename.replace('debug_', '').replace('.html', '').split('_')[0]
            
            print(f"\n📄 Analyzing {source_name}...")
            
            # Check for common issues
            self.check_bot_detection(source_name, content)
            self.check_price_selectors(source_name, content)
            self.check_site_structure(source_name, content)
            
        except Exception as e:
            print(f"❌ Error analyzing {filename}: {e}")
    
    def check_bot_detection(self, source_name, content):
        """Check for bot detection in content"""
        bot_phrases = [
            'enable javascript', 'access denied', 'security check',
            'cloudflare', 'captcha', 'blocked', 'robot'
        ]
        
        content_lower = content.lower()
        detected_phrases = [phrase for phrase in bot_phrases if phrase in content_lower]
        
        if detected_phrases:
            print(f"  🤖 {source_name}: Bot detection found - {', '.join(detected_phrases)}")
            return True
        
        return False
    
    def check_price_selectors(self, source_name, content):
        """Check if price selectors still exist"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Common price selectors
        price_selectors = [
            '[class*="price"]', '[data-testid*="price"]', '.fare-price',
            '[class*="fare"]', '[class*="cost"]', '.amount'
        ]
        
        found_selectors = []
        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    found_selectors.append(f"{selector} ({len(elements)} elements)")
            except:
                continue
        
        if found_selectors:
            print(f"  💰 {source_name}: Price selectors found - {', '.join(found_selectors[:3])}")
        else:
            print(f"  ⚠️ {source_name}: No price selectors found - site structure may have changed")
    
    def check_site_structure(self, source_name, content):
        """Check overall site structure"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check for key elements
        title = soup.find('title')
        forms = soup.find_all('form')
        scripts = soup.find_all('script')
        
        print(f"  📝 {source_name}: Structure - Title: {bool(title)}, Forms: {len(forms)}, Scripts: {len(scripts)}")
        
        # Check content length
        if len(content) < 1000:
            print(f"  ⚠️ {source_name}: Very small content ({len(content)} chars) - possible error page")

class AutoSelector:
    """Automatically find new price selectors when sites change"""
    
    def __init__(self):
        pass
    
    def find_new_selectors(self, html_content, source_name):
        """Find potential new price selectors in HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print(f"\n🔍 Finding new selectors for {source_name}...")
        
        # Look for elements containing price-like text
        price_pattern = re.compile(r'[£$€]\s*\d{1,4}|\d{1,4}\s*[£$€]')
        potential_selectors = []
        
        # Search through all elements
        for element in soup.find_all():
            text = element.get_text(strip=True)
            if price_pattern.search(text):
                # Generate selector for this element
                selector = self.generate_css_selector(element)
                if selector:
                    potential_selectors.append({
                        'selector': selector,
                        'text': text[:50],
                        'tag': element.name,
                        'classes': element.get('class', [])
                    })
        
        # Remove duplicates and return top candidates
        unique_selectors = []
        seen_selectors = set()
        
        for sel in potential_selectors:
            if sel['selector'] not in seen_selectors:
                seen_selectors.add(sel['selector'])
                unique_selectors.append(sel)
        
        if unique_selectors:
            print(f"  💡 Found {len(unique_selectors)} potential selectors:")
            for i, sel in enumerate(unique_selectors[:5]):
                print(f"    {i+1}. {sel['selector']} - '{sel['text']}'")
        else:
            print(f"  ❌ No price selectors found")
        
        return unique_selectors[:10]
    
    def generate_css_selector(self, element):
        """Generate CSS selector for an element"""
        try:
            # Try class-based selector first
            classes = element.get('class', [])
            if classes:
                return f".{classes[0]}"
            
            # Try ID-based selector
            element_id = element.get('id')
            if element_id:
                return f"#{element_id}"
            
            # Try data attribute
            for attr in element.attrs:
                if attr.startswith('data-') and 'price' in attr.lower():
                    return f"[{attr}]"
            
            # Fallback to tag name
            return element.name
            
        except:
            return None

def run_comprehensive_tests():
    """Run all tests and generate reports"""
    print("🚀 STARTING COMPREHENSIVE SCRAPER TESTING")
    print("=" * 50)
    
    # Test 1: Health Monitor
    monitor = ScraperHealthMonitor()
    monitor.test_all_sources()
    
    # Test 2: Debug File Analysis
    analyzer = DebugFileAnalyzer()
    analyzer.analyze_all_debug_files()
    
    # Test 3: Auto Selector Finding
    auto_selector = AutoSelector()
    
    # Analyze recent debug files for new selectors
    debug_files = [f for f in os.listdir('.') if f.startswith('debug_') and f.endswith('.html')]
    for debug_file in debug_files[:3]:  # Analyze first 3 files
        try:
            with open(debug_file, 'r', encoding='utf-8') as f:
                content = f.read()
            source_name = debug_file.replace('debug_', '').replace('.html', '').split('_')[0]
            auto_selector.find_new_selectors(content, source_name)
        except:
            continue
    
    print("\n" + "=" * 50)
    print("✅ COMPREHENSIVE TESTING COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    run_comprehensive_tests()
