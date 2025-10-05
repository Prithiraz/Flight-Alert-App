
#!/usr/bin/env python3
"""
Site Change Monitor
Continuously monitors flight booking sites for changes that break scraping
"""

import time
import json
import os
import hashlib
import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MimeText

class SiteChangeMonitor:
    """Monitor sites for changes that affect scraping"""
    
    def __init__(self):
        self.baseline_hashes = {}
        self.alert_threshold = 0.7  # Alert if content similarity drops below 70%
        self.check_interval = 3600  # Check every hour
        
    def create_baseline(self, sites_to_monitor):
        """Create baseline fingerprints for sites"""
        print("📸 Creating baseline fingerprints for sites...")
        
        for site_name, url in sites_to_monitor.items():
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    # Create content fingerprint
                    fingerprint = self.create_content_fingerprint(response.text)
                    self.baseline_hashes[site_name] = {
                        'fingerprint': fingerprint,
                        'timestamp': datetime.now().isoformat(),
                        'url': url,
                        'content_length': len(response.text)
                    }
                    print(f"  ✅ {site_name}: Baseline created")
                else:
                    print(f"  ❌ {site_name}: Failed to create baseline ({response.status_code})")
                    
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"  ❌ {site_name}: Error creating baseline - {e}")
        
        self.save_baselines()
    
    def create_content_fingerprint(self, html_content):
        """Create a fingerprint of important page elements"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract key elements that matter for scraping
        fingerprint_elements = []
        
        # 1. All class names (structure indicators)
        for element in soup.find_all(class_=True):
            fingerprint_elements.extend(element.get('class', []))
        
        # 2. All data attributes (often used for prices)
        for element in soup.find_all():
            for attr in element.attrs:
                if attr.startswith('data-'):
                    fingerprint_elements.append(f"{attr}={element.attrs[attr]}")
        
        # 3. Form structure (search forms)
        for form in soup.find_all('form'):
            form_inputs = [inp.get('name', '') for inp in form.find_all('input')]
            fingerprint_elements.append(f"form:{'-'.join(form_inputs)}")
        
        # 4. Script sources (JS apps change these)
        for script in soup.find_all('script', src=True):
            src = script.get('src', '')
            if src:
                # Extract just filename, not full URL
                filename = src.split('/')[-1].split('?')[0]
                fingerprint_elements.append(f"script:{filename}")
        
        # Create hash from sorted elements
        content_string = '|'.join(sorted(set(fingerprint_elements)))
        return hashlib.md5(content_string.encode()).hexdigest()
    
    def check_for_changes(self):
        """Check all monitored sites for significant changes"""
        print("🔍 Checking sites for changes...")
        
        if not self.baseline_hashes:
            print("❌ No baselines found. Run create_baseline() first.")
            return
        
        changes_detected = []
        
        for site_name, baseline in self.baseline_hashes.items():
            try:
                # Fetch current content
                response = requests.get(baseline['url'], timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    current_fingerprint = self.create_content_fingerprint(response.text)
                    
                    # Compare with baseline
                    similarity = self.calculate_similarity(baseline['fingerprint'], current_fingerprint)
                    
                    if similarity < self.alert_threshold:
                        change_info = {
                            'site': site_name,
                            'similarity': similarity,
                            'baseline_date': baseline['timestamp'],
                            'current_date': datetime.now().isoformat(),
                            'url': baseline['url'],
                            'content_length_change': len(response.text) - baseline['content_length']
                        }
                        changes_detected.append(change_info)
                        print(f"  🚨 {site_name}: Significant change detected ({similarity:.1%} similarity)")
                    else:
                        print(f"  ✅ {site_name}: No significant changes ({similarity:.1%} similarity)")
                else:
                    print(f"  ❌ {site_name}: HTTP {response.status_code}")
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"  ❌ {site_name}: Error checking - {e}")
        
        if changes_detected:
            self.handle_changes_detected(changes_detected)
        
        return changes_detected
    
    def calculate_similarity(self, hash1, hash2):
        """Calculate similarity between two fingerprints"""
        if hash1 == hash2:
            return 1.0
        
        # For now, use simple hash comparison
        # In a more sophisticated version, you could compare actual elements
        return 0.0 if hash1 != hash2 else 1.0
    
    def handle_changes_detected(self, changes):
        """Handle detected changes"""
        print(f"\n🚨 ALERT: {len(changes)} sites have significant changes!")
        
        # Log changes
        self.log_changes(changes)
        
        # Generate alert report
        self.generate_alert_report(changes)
        
        # Send notifications (if configured)
        self.send_notifications(changes)
    
    def log_changes(self, changes):
        """Log changes to file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'changes_detected': len(changes),
            'details': changes
        }
        
        log_file = 'site_changes.log'
        
        # Read existing log
        existing_log = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    existing_log = json.load(f)
            except:
                existing_log = []
        
        # Add new entry
        existing_log.append(log_entry)
        
        # Keep only last 100 entries
        existing_log = existing_log[-100:]
        
        # Save updated log
        with open(log_file, 'w') as f:
            json.dump(existing_log, f, indent=2)
        
        print(f"📝 Changes logged to {log_file}")
    
    def generate_alert_report(self, changes):
        """Generate detailed alert report"""
        report_lines = []
        report_lines.append("🚨 SITE CHANGE ALERT REPORT")
        report_lines.append("=" * 50)
        report_lines.append(f"Timestamp: {datetime.now().isoformat()}")
        report_lines.append(f"Sites with changes: {len(changes)}")
        report_lines.append("")
        
        for change in changes:
            report_lines.append(f"🔍 {change['site']}:")
            report_lines.append(f"  URL: {change['url']}")
            report_lines.append(f"  Similarity: {change['similarity']:.1%}")
            report_lines.append(f"  Baseline: {change['baseline_date']}")
            report_lines.append(f"  Content size change: {change['content_length_change']:+d} chars")
            report_lines.append("")
        
        report_lines.append("📋 RECOMMENDED ACTIONS:")
        report_lines.append("1. Check debug files for these sites")
        report_lines.append("2. Update CSS selectors if needed")
        report_lines.append("3. Test scrapers for these sites")
        report_lines.append("4. Update regex patterns if necessary")
        
        report_content = "\n".join(report_lines)
        
        # Save report
        report_file = f"change_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"📄 Alert report saved to {report_file}")
        
        # Also print to console
        print("\n" + report_content)
    
    def send_notifications(self, changes):
        """Send notifications about changes (placeholder)"""
        # This would implement email/SMS/Slack notifications
        print(f"📧 Would send notifications about {len(changes)} changed sites")
        
        # Example email notification (configure SMTP settings)
        # self.send_email_alert(changes)
    
    def save_baselines(self):
        """Save baseline fingerprints to file"""
        with open('site_baselines.json', 'w') as f:
            json.dump(self.baseline_hashes, f, indent=2)
        print(f"💾 Baselines saved to site_baselines.json")
    
    def load_baselines(self):
        """Load baseline fingerprints from file"""
        try:
            with open('site_baselines.json', 'r') as f:
                self.baseline_hashes = json.load(f)
            print(f"📂 Loaded {len(self.baseline_hashes)} baselines")
            return True
        except FileNotFoundError:
            print("❌ No baseline file found")
            return False
        except Exception as e:
            print(f"❌ Error loading baselines: {e}")
            return False
    
    def start_monitoring(self, sites_to_monitor, check_interval_hours=1):
        """Start continuous monitoring"""
        self.check_interval = check_interval_hours * 3600
        
        print(f"🚀 Starting continuous monitoring (checking every {check_interval_hours}h)")
        
        # Create baselines if they don't exist
        if not self.load_baselines():
            self.create_baseline(sites_to_monitor)
        
        # Monitoring loop
        try:
            while True:
                changes = self.check_for_changes()
                
                if changes:
                    print(f"⚠️ Found {len(changes)} sites with changes")
                else:
                    print("✅ All sites stable")
                
                print(f"😴 Sleeping for {check_interval_hours} hours...")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")

def setup_monitoring():
    """Setup monitoring for key flight booking sites"""
    
    # Define sites to monitor (working ones from your log)
    sites_to_monitor = {
        'kayak': 'https://www.kayak.co.uk/flights/LHR-AMS/2025-08-08',
        'momondo': 'https://www.momondo.co.uk/flight-search/LHR-AMS/2025-08-08',
        'booking': 'https://www.booking.com/flights/search.html?origin=LHR&destination=AMS&departure_date=2025-08-08',
        'wizz_air': 'https://wizzair.com/en-gb/flights/select?departureIata=LHR&arrivalIata=AMS&departureDate=2025-08-08',
        'skyscanner': 'https://www.skyscanner.net/transport/flights/lhr/ams/250808/',
        'ryanair': 'https://www.ryanair.com/gb/en/trip/flights/select?adults=1&teens=0&children=0&infants=0&dateOut=2025-08-08&originIata=LHR&destinationIata=AMS'
    }
    
    monitor = SiteChangeMonitor()
    
    print("🔧 Setting up site monitoring...")
    print("Choose an option:")
    print("1. Create new baselines")
    print("2. Check for changes (one-time)")
    print("3. Start continuous monitoring")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == '1':
        monitor.create_baseline(sites_to_monitor)
    elif choice == '2':
        if monitor.load_baselines():
            monitor.check_for_changes()
        else:
            print("No baselines found. Creating them first...")
            monitor.create_baseline(sites_to_monitor)
    elif choice == '3':
        monitor.start_monitoring(sites_to_monitor, check_interval_hours=1)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    setup_monitoring()
