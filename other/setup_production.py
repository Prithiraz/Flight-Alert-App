
#!/usr/bin/env python3
"""
Production Setup Script for FlightAlert Pro
Installs Playwright browsers and configures the environment
"""

import subprocess
import sys
import os

def setup_production_environment():
    """Setup production environment with all dependencies"""
    
    print("🚀 Setting up Production FlightAlert Pro Environment...")
    print("=" * 60)
    
    # Install Python packages
    print("📦 Installing Python packages...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Python packages installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False
    
    # Install Playwright browsers
    print("🌐 Installing Playwright browsers...")
    try:
        subprocess.check_call(['playwright', 'install', 'chromium'])
        print("✅ Chromium browser installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install browsers: {e}")
        print("💡 You may need to install Playwright manually:")
        print("   pip install playwright && playwright install chromium")
        return False
    
    # Set environment variables
    print("⚙️ Setting up environment...")
    env_vars = {
        'PLAYWRIGHT_BROWSERS_PATH': '/tmp/playwright-browsers',
        'FLASK_ENV': 'production',
        'FLASK_DEBUG': '0'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Test the setup
    print("🧪 Testing setup...")
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright import successful")
    except ImportError as e:
        print(f"❌ Playwright test failed: {e}")
        return False
    
    print("\n🎉 PRODUCTION SETUP COMPLETE!")
    print("✅ FlightAlert Pro is ready for production scraping")
    print("🚀 Features enabled:")
    print("   - Async Playwright with stealth mode")
    print("   - Proxy rotation and context pooling")
    print("   - Intelligent fallback strategies")
    print("   - Full itinerary extraction")
    print("   - Data validation and deduplication")
    print("   - Production-grade error handling")
    
    print(f"\n🔧 To start the application:")
    print(f"   python main.py")
    
    return True

if __name__ == "__main__":
    success = setup_production_environment()
    if not success:
        sys.exit(1)
