
#!/usr/bin/env python3
"""
Quick Test Script
Fast testing of specific scrapers and selectors
"""

import requests
import time
from bs4 import BeautifulSoup
import re

def quick_test_site(site_name, url, selectors, patterns):
    """Quickly test a specific site"""
    print(f"🧪 Quick testing {site_name}...")
    print(f"URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)} chars")
        
        if response.status_code == 200:
            # Test CSS selectors
            soup = BeautifulSoup(response.text, 'html.parser')
            
            print("\n🔍 Testing CSS selectors:")
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        print(f"  ✅ {selector}: {len(elements)} elements found")
                        # Show first element text
                        first_text = elements[0].get_text(strip=True)[:50]
                        print(f"      First: '{first_text}'")
                    else:
                        print(f"  ❌ {selector}: No elements found")
                except Exception as e:
                    print(f"  ⚠️ {selector}: Error - {e}")
            
            # Test regex patterns
            print("\n🔍 Testing regex patterns:")
            for pattern in patterns:
                try:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    if matches:
                        print(f"  ✅ {pattern}: {len(matches)} matches")
                        print(f"      Samples: {matches[:3]}")
                    else:
                        print(f"  ❌ {pattern}: No matches")
                except Exception as e:
                    print(f"  ⚠️ {pattern}: Error - {e}")
        
        # Save debug file
        debug_file = f"quick_test_{site_name.lower().replace(' ', '_')}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\n💾 Debug file saved: {debug_file}")
        
    except Exception as e:
        print(f"❌ Error testing {site_name}: {e}")

def test_working_sites():
    """Test the sites that are currently working"""
    print("🧪 TESTING WORKING SITES")
    print("=" * 30)
    
    working_sites = [
        {
            'name': 'Kayak',
            'url': 'https://www.kayak.co.uk/flights/LHR-AMS/2025-08-08',
            'selectors': ['.price-text', '[data-resultid] .price', '.Common-Booking-MultiBookProvider-Display-price'],
            'patterns': [r'£(\d{1,4})', r'"price":(\d{1,4})', r'price["\s:]+(\d{1,4})']
        },
        {
            'name': 'Momondo', 
            'url': 'https://www.momondo.co.uk/flight-search/LHR-AMS/2025-08-08',
            'selectors': ['[data-testid*="price"]', '.price', '.fare-price'],
            'patterns': [r'£(\d{1,4})', r'"price":(\d{1,4})', r'price["\s:]+(\d{1,4})']
        },
        {
            'name': 'Booking',
            'url': 'https://www.booking.com/flights/search.html?origin=LHR&destination=AMS&departure_date=2025-08-08',
            'selectors': ['[data-testid*="price"]', '.price', '[class*="price"]'],
            'patterns': [r'£(\d{1,4})', r'"price":(\d{1,4})', r'"totalPrice":(\d{1,4})']
        }
    ]
    
    for site in working_sites:
        quick_test_site(site['name'], site['url'], site['selectors'], site['patterns'])
        print("\n" + "-" * 50 + "\n")
        time.sleep(3)  # Rate limiting

def test_broken_sites():
    """Test sites that are currently broken"""
    print("🧪 TESTING BROKEN SITES")
    print("=" * 30)
    
    broken_sites = [
        {
            'name': 'Skyscanner',
            'url': 'https://www.skyscanner.net/transport/flights/lhr/ams/250808/',
            'selectors': ['[data-testid*="price"]', '.price', '.BpkText_bpk-text__money'],
            'patterns': [r'£(\d{1,4})', r'"price":(\d{1,4})', r'data-price="(\d{1,4})"']
        },
        {
            'name': 'Ryanair',
            'url': 'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut=2025-08-08&originIata=LHR&destinationIata=AMS',
            'selectors': ['.fare-card__price', '.price', '[data-ref*="price"]'],
            'patterns': [r'£(\d{1,4})', r'"price":(\d{1,4})', r'fare["\s:]+(\d{1,4})']
        },
        {
            'name': 'easyJet',
            'url': 'https://www.easyjet.com/en/cheap-flights/LHR/AMS?from=LHR&to=AMS&departDate=2025-08-08&adults=1',
            'selectors': ['.fare-light__price', '.price', '[class*="price"]'],
            'patterns': [r'£(\d{1,4})', r'"price":(\d{1,4})', r'fare["\s:]+(\d{1,4})']
        }
    ]
    
    for site in broken_sites:
        quick_test_site(site['name'], site['url'], site['selectors'], site['patterns'])
        print("\n" + "-" * 50 + "\n")
        time.sleep(5)  # Longer delay for broken sites

def test_specific_selector(url, selector):
    """Test a specific selector on a specific URL"""
    print(f"🎯 Testing specific selector: {selector}")
    print(f"URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        elements = soup.select(selector)
        
        if elements:
            print(f"✅ Found {len(elements)} elements")
            for i, elem in enumerate(elements[:5]):
                text = elem.get_text(strip=True)
                print(f"  {i+1}. '{text[:100]}'")
        else:
            print("❌ No elements found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 QUICK TEST OPTIONS")
    print("1. Test working sites")
    print("2. Test broken sites") 
    print("3. Test specific selector")
    print("4. Test all")
    
    choice = input("Choose option (1-4): ").strip()
    
    if choice == '1':
        test_working_sites()
    elif choice == '2':
        test_broken_sites()
    elif choice == '3':
        url = input("Enter URL: ").strip()
        selector = input("Enter CSS selector: ").strip()
        test_specific_selector(url, selector)
    elif choice == '4':
        test_working_sites()
        print("\n" + "=" * 50 + "\n")
        test_broken_sites()
    else:
        print("Invalid choice")
