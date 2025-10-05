
#!/usr/bin/env python3
"""
Test Runner for Flight Scraper
Run various tests and monitoring tasks
"""

import os
import sys
import subprocess
import time

def run_health_check():
    """Run comprehensive health check"""
    print("🏥 Running health check...")
    try:
        subprocess.run([sys.executable, 'scraper_test_debug.py'], check=True)
    except subprocess.CalledProcessError:
        print("❌ Health check failed")
    except FileNotFoundError:
        print("❌ scraper_test_debug.py not found")

def run_selector_update():
    """Update selectors based on debug files"""
    print("🔧 Updating selectors...")
    try:
        subprocess.run([sys.executable, 'selector_updater.py'], check=True)
    except subprocess.CalledProcessError:
        print("❌ Selector update failed")
    except FileNotFoundError:
        print("❌ selector_updater.py not found")

def run_quick_test():
    """Run quick tests"""
    print("⚡ Running quick tests...")
    try:
        subprocess.run([sys.executable, 'quick_test.py'], check=True)
    except subprocess.CalledProcessError:
        print("❌ Quick test failed")
    except FileNotFoundError:
        print("❌ quick_test.py not found")

def cleanup_debug_files():
    """Clean up old debug files"""
    print("🧹 Cleaning up debug files...")
    
    debug_files = [f for f in os.listdir('.') if f.startswith('debug_') and f.endswith('.html')]
    
    if len(debug_files) > 20:  # Keep only 20 most recent
        debug_files.sort(key=lambda x: os.path.getmtime(x))
        files_to_remove = debug_files[:-20]
        
        for file in files_to_remove:
            try:
                os.remove(file)
                print(f"   🗑️ Removed {file}")
            except:
                print(f"   ⚠️ Could not remove {file}")
    else:
        print("   ✅ Debug files under limit")

def main():
    """Main test runner"""
    print("🚀 FLIGHT SCRAPER TEST RUNNER")
    print("=" * 40)
    
    print("Options:")
    print("1. Health check (comprehensive)")
    print("2. Update selectors")
    print("3. Quick test")
    print("4. Cleanup debug files")
    print("5. Run all")
    print("6. Monitor mode (continuous)")
    
    choice = input("\nChoose option (1-6): ").strip()
    
    if choice == '1':
        run_health_check()
    elif choice == '2':
        run_selector_update()
    elif choice == '3':
        run_quick_test()
    elif choice == '4':
        cleanup_debug_files()
    elif choice == '5':
        print("🔄 Running all tests...")
        run_health_check()
        time.sleep(2)
        run_selector_update()
        time.sleep(2)
        run_quick_test()
        cleanup_debug_files()
        print("✅ All tests complete!")
    elif choice == '6':
        print("🔄 Starting monitor mode...")
        try:
            subprocess.run([sys.executable, 'site_monitor.py'], check=True)
        except subprocess.CalledProcessError:
            print("❌ Monitor failed")
        except FileNotFoundError:
            print("❌ site_monitor.py not found")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
