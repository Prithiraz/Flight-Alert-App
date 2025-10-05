
import requests
import json

def test_microservice():
    """Test the microservice directly"""
    print("🧪 Testing microservice...")
    
    # Test deployed microservice
    try:
        url = "https://dynamic-flight-scraper-prithirazchoudh.replit.app/scrape"
        params = {'origin': 'LHR', 'dest': 'AMS'}
        
        print(f"📞 Calling: {url}")
        print(f"📊 Params: {params}")
        
        response = requests.get(url, params=params, timeout=30)
        print(f"🔄 Status: {response.status_code}")
        print(f"📝 Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('count', 0)} flights found")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Microservice test failed: {e}")

def test_local_scraping():
    """Test local scraping methods"""
    print("🧪 Testing local scraping...")
    
    try:
        from flight_scraper import FlightScraper
        scraper = FlightScraper()
        
        # Test Google search scraping
        flights = scraper.scrape_google_flights_search('LHR', 'AMS', '2025-07-08')
        print(f"🔍 Google search results: {len(flights)} flights")
        
        for flight in flights[:3]:
            print(f"  ✈️ {flight['airline']}: £{flight['price']}")
            
    except Exception as e:
        print(f"❌ Local scraping test failed: {e}")

if __name__ == "__main__":
    test_microservice()
    test_local_scraping()
