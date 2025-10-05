
#!/usr/bin/env python3
"""
Setup Playwright for real flight data scraping
"""

import subprocess
import sys
import os

def setup_playwright():
    """Install and configure Playwright for Replit environment"""
    
    print("🚀 Setting up Playwright for REAL flight data...")
    print("=" * 60)
    
    try:
        # Install Playwright
        print("📦 Installing Playwright...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'playwright==1.40.0'])
        print("✅ Playwright package installed")
        
        # Install browser
        print("🌐 Installing Chromium browser...")
        subprocess.check_call(['playwright', 'install', 'chromium'])
        print("✅ Chromium browser installed")
        
        # Set environment variables for Replit
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/home/runner/.cache/ms-playwright'
        
        # Test installation
        print("🧪 Testing Playwright installation...")
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://www.google.com')
            browser.close()
            
        print("✅ Playwright test successful!")
        print("🎉 READY FOR REAL FLIGHT DATA SCRAPING!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print("💡 Alternative: Using requests-based scraping as fallback")

if __name__ == "__main__":
    setup_playwright()
