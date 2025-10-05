
#!/usr/bin/env python3
"""
Production Health Monitoring for FlightAlert Pro
Monitors scraper performance and automatically adjusts configurations
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sqlite3
from typing import Dict, List
import aiohttp

class ProductionHealthMonitor:
    """Advanced health monitoring for production scraper"""
    
    def __init__(self, db_path='scraper_health.db'):
        self.db_path = db_path
        self.init_database()
        self.performance_metrics = defaultdict(list)
        self.site_configs = self.load_site_configs()
    
    def init_database(self):
        """Initialize health monitoring database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                site_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                success_rate REAL,
                flights_found INTEGER,
                error_message TEXT,
                strategy_used TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS selector_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                site_name TEXT NOT NULL,
                selector_type TEXT NOT NULL,
                selector TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_success TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                site_name TEXT NOT NULL,
                change_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                confidence REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_site_configs(self):
        """Load site configurations"""
        try:
            with open('site_configs.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    async def run_comprehensive_health_check(self):
        """Run comprehensive health check on all sites"""
        print("🏥 Starting Comprehensive Health Check...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'sites_tested': 0,
            'sites_working': 0,
            'sites_degraded': 0,
            'sites_broken': 0,
            'overall_health': 'unknown',
            'recommendations': []
        }
        
        # Test each configured site
        for site_name, config in self.site_configs.items():
            try:
                site_health = await self._test_site_health(site_name, config)
                results['sites_tested'] += 1
                
                if site_health['status'] == 'healthy':
                    results['sites_working'] += 1
                elif site_health['status'] == 'degraded':
                    results['sites_degraded'] += 1
                else:
                    results['sites_broken'] += 1
                
                # Log to database
                self._log_health_check(site_health)
                
            except Exception as e:
                print(f"❌ Health check failed for {site_name}: {e}")
                results['sites_broken'] += 1
        
        # Calculate overall health
        if results['sites_tested'] > 0:
            working_rate = results['sites_working'] / results['sites_tested']
            if working_rate >= 0.8:
                results['overall_health'] = 'healthy'
            elif working_rate >= 0.5:
                results['overall_health'] = 'degraded'
            else:
                results['overall_health'] = 'critical'
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results)
        
        print(f"📊 Health Check Complete:")
        print(f"   ✅ Working: {results['sites_working']}")
        print(f"   ⚠️ Degraded: {results['sites_degraded']}")
        print(f"   ❌ Broken: {results['sites_broken']}")
        print(f"   🎯 Overall: {results['overall_health'].upper()}")
        
        return results
    
    async def _test_site_health(self, site_name, config):
        """Test health of a specific site"""
        start_time = time.time()
        
        health_result = {
            'site_name': site_name,
            'status': 'broken',
            'response_time': 0,
            'flights_found': 0,
            'error_message': None,
            'strategy_used': 'health_check',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Test basic connectivity
            url = config['urls'][0].format(
                origin='LHR', dest='AMS', 
                origin_lower='lhr', dest_lower='ams',
                date='2025-08-08', date_compact='250808',
                date_slash='08/08/2025'
            )
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=self._get_test_headers()) as response:
                    health_result['response_time'] = time.time() - start_time
                    
                    if response.status == 200:
                        content = await response.text()
                        
                        # Check for bot detection
                        bot_indicators = config.get('anti_bot_indicators', [])
                        if any(indicator in content.lower() for indicator in bot_indicators):
                            health_result['status'] = 'degraded'
                            health_result['error_message'] = 'Bot detection triggered'
                        else:
                            # Test selector health
                            selector_health = self._test_selector_health(content, config)
                            health_result['flights_found'] = selector_health['estimated_results']
                            
                            if selector_health['healthy_selectors'] >= 0.7:
                                health_result['status'] = 'healthy'
                            elif selector_health['healthy_selectors'] >= 0.3:
                                health_result['status'] = 'degraded'
                            else:
                                health_result['status'] = 'broken'
                                health_result['error_message'] = 'Selectors not working'
                    else:
                        health_result['error_message'] = f'HTTP {response.status}'
                        
        except Exception as e:
            health_result['error_message'] = str(e)
            health_result['response_time'] = time.time() - start_time
        
        return health_result
    
    def _test_selector_health(self, html_content, config):
        """Test if selectors are still working"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        selectors = config.get('selectors', {})
        
        working_selectors = 0
        total_selectors = len(selectors)
        estimated_results = 0
        
        for selector_name, selector_value in selectors.items():
            try:
                if ',' in selector_value:
                    # Multiple selectors - test each
                    sub_selectors = [s.strip() for s in selector_value.split(',')]
                    found = False
                    for sub_sel in sub_selectors:
                        if soup.select_one(sub_sel):
                            found = True
                            break
                    if found:
                        working_selectors += 1
                else:
                    # Single selector
                    elements = soup.select(selector_value)
                    if elements:
                        working_selectors += 1
                        if selector_name == 'flight_cards':
                            estimated_results = len(elements)
            except:
                continue
        
        healthy_ratio = working_selectors / total_selectors if total_selectors > 0 else 0
        
        return {
            'healthy_selectors': healthy_ratio,
            'working_count': working_selectors,
            'total_count': total_selectors,
            'estimated_results': estimated_results
        }
    
    def _get_test_headers(self):
        """Get headers for health check requests"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def _log_health_check(self, health_data):
        """Log health check results to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO health_checks 
            (timestamp, site_name, status, response_time, flights_found, error_message, strategy_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            health_data['timestamp'],
            health_data['site_name'],
            health_data['status'],
            health_data['response_time'],
            health_data['flights_found'],
            health_data.get('error_message'),
            health_data.get('strategy_used', 'unknown')
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_recommendations(self, results):
        """Generate actionable recommendations"""
        recommendations = []
        
        if results['sites_broken'] > 0:
            recommendations.append({
                'priority': 'high',
                'action': f'Fix {results["sites_broken"]} broken sites',
                'description': 'Update selectors or handle bot detection'
            })
        
        if results['sites_degraded'] > 0:
            recommendations.append({
                'priority': 'medium',
                'action': f'Optimize {results["sites_degraded"]} degraded sites',
                'description': 'Improve selector reliability or add fallbacks'
            })
        
        working_rate = results['sites_working'] / results['sites_tested'] if results['sites_tested'] > 0 else 0
        if working_rate < 0.5:
            recommendations.append({
                'priority': 'critical',
                'action': 'System reliability below 50%',
                'description': 'Immediate attention required - consider fallback data sources'
            })
        
        return recommendations
    
    def get_health_report(self, days=7):
        """Get health report for last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT site_name, status, COUNT(*) as count, 
                   AVG(response_time) as avg_response_time,
                   AVG(flights_found) as avg_flights_found
            FROM health_checks 
            WHERE timestamp > ?
            GROUP BY site_name, status
            ORDER BY site_name, status
        ''', (cutoff_date,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Process results into report format
        report = defaultdict(dict)
        for row in results:
            site_name, status, count, avg_response, avg_flights = row
            report[site_name][status] = {
                'count': count,
                'avg_response_time': round(avg_response, 2) if avg_response else 0,
                'avg_flights_found': round(avg_flights, 2) if avg_flights else 0
            }
        
        return dict(report)
    
    async def continuous_monitoring(self, interval_minutes=60):
        """Run continuous health monitoring"""
        print(f"🔄 Starting continuous monitoring (every {interval_minutes} minutes)")
        
        while True:
            try:
                await self.run_comprehensive_health_check()
                await asyncio.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped")
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry

async def main():
    """Main function for running health monitoring"""
    monitor = ProductionHealthMonitor()
    
    # Run single health check
    results = await monitor.run_comprehensive_health_check()
    
    # Show recent report
    report = monitor.get_health_report(days=1)
    if report:
        print("\n📊 Recent Health Report:")
        for site_name, status_data in report.items():
            print(f"   🔍 {site_name}:")
            for status, metrics in status_data.items():
                print(f"      {status}: {metrics['count']} checks, {metrics['avg_response_time']}s avg")

if __name__ == "__main__":
    asyncio.run(main())
