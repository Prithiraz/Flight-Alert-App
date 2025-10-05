
#!/usr/bin/env python3
"""
Automatic Selector Updater
Updates CSS selectors and regex patterns when sites change their HTML structure
"""

import json
import os
from bs4 import BeautifulSoup
import re

class SelectorUpdater:
    """Updates selectors based on analysis of debug files"""
    
    def __init__(self):
        self.updated_selectors = {}
        
    def update_site_selectors(self, source_name, debug_file_path):
        """Update selectors for a specific site based on its debug file"""
        print(f"🔧 Updating selectors for {source_name}...")
        
        try:
            with open(debug_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Analyze HTML for new price patterns
            new_selectors = self.find_price_selectors(html_content, source_name)
            new_patterns = self.find_price_patterns(html_content, source_name)
            
            if new_selectors or new_patterns:
                self.updated_selectors[source_name] = {
                    'css_selectors': new_selectors,
                    'price_patterns': new_patterns,
                    'last_updated': os.path.getmtime(debug_file_path)
                }
                
                print(f"  ✅ Updated {source_name}: {len(new_selectors)} selectors, {len(new_patterns)} patterns")
                return True
            else:
                print(f"  ⚠️ No new patterns found for {source_name}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error updating {source_name}: {e}")
            return False
    
    def find_price_selectors(self, html_content, source_name):
        """Find CSS selectors that contain price information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        price_selectors = []
        
        # Price pattern to match
        price_pattern = re.compile(r'[£$€]\s*\d{1,4}|\d{1,4}\s*[£$€]')
        
        # Check various selector types
        selector_patterns = [
            # Class-based selectors
            lambda: soup.find_all(attrs={'class': re.compile(r'price', re.I)}),
            lambda: soup.find_all(attrs={'class': re.compile(r'fare', re.I)}),
            lambda: soup.find_all(attrs={'class': re.compile(r'cost', re.I)}),
            lambda: soup.find_all(attrs={'class': re.compile(r'amount', re.I)}),
            
            # Data attribute selectors
            lambda: soup.find_all(attrs={re.compile(r'data-.*price', re.I): True}),
            lambda: soup.find_all(attrs={re.compile(r'data-.*fare', re.I): True}),
            
            # ID-based selectors
            lambda: soup.find_all(attrs={'id': re.compile(r'price', re.I)}),
            
            # Aria label selectors
            lambda: soup.find_all(attrs={'aria-label': re.compile(r'price|fare|cost', re.I)})
        ]
        
        for pattern_func in selector_patterns:
            try:
                elements = pattern_func()
                for element in elements:
                    text = element.get_text(strip=True)
                    if price_pattern.search(text):
                        selector = self.generate_selector(element)
                        if selector and selector not in price_selectors:
                            price_selectors.append(selector)
            except:
                continue
        
        return price_selectors[:10]  # Return top 10 candidates
    
    def find_price_patterns(self, html_content, source_name):
        """Find regex patterns that match prices in the HTML"""
        new_patterns = []
        
        # Extract all price-like strings
        price_matches = re.findall(r'["\'].*?[£$€]\s*\d{1,4}.*?["\']|["\'].*?\d{1,4}\s*[£$€].*?["\']', html_content)
        
        # Analyze patterns
        for match in price_matches[:20]:  # Limit to first 20 matches
            # Create regex pattern from match
            pattern = self.create_pattern_from_match(match)
            if pattern and pattern not in new_patterns:
                new_patterns.append(pattern)
        
        # Add common JSON patterns
        json_patterns = [
            r'"price":\s*"?[£$€]?(\d{1,4})"?',
            r'"fare":\s*"?[£$€]?(\d{1,4})"?',
            r'"amount":\s*"?[£$€]?(\d{1,4})"?',
            r'"total":\s*"?[£$€]?(\d{1,4})"?',
            r'"value":\s*(\d{1,4})',
            r'price["\s]*:["\s]*(\d{1,4})',
            r'fare["\s]*:["\s]*(\d{1,4})'
        ]
        
        for pattern in json_patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                if pattern not in new_patterns:
                    new_patterns.append(pattern)
        
        return new_patterns[:15]  # Return top 15 patterns
    
    def generate_selector(self, element):
        """Generate CSS selector for element"""
        try:
            # Priority 1: Use class if it contains price-related terms
            classes = element.get('class', [])
            price_classes = [c for c in classes if any(term in c.lower() for term in ['price', 'fare', 'cost', 'amount'])]
            if price_classes:
                return f".{price_classes[0]}"
            
            # Priority 2: Use data attributes
            for attr in element.attrs:
                if attr.startswith('data-') and any(term in attr.lower() for term in ['price', 'fare', 'cost']):
                    return f"[{attr}]"
            
            # Priority 3: Use ID
            element_id = element.get('id')
            if element_id and any(term in element_id.lower() for term in ['price', 'fare', 'cost']):
                return f"#{element_id}"
            
            # Priority 4: Use first class
            if classes:
                return f".{classes[0]}"
            
            # Priority 5: Use tag with attributes
            if element.attrs:
                return f"{element.name}[{list(element.attrs.keys())[0]}]"
            
            return element.name
            
        except:
            return None
    
    def create_pattern_from_match(self, match_text):
        """Create regex pattern from a price match"""
        # Clean the match
        clean_match = match_text.strip('"\'')
        
        # Create pattern by replacing the actual number with a capture group
        pattern = re.sub(r'\d{1,4}', r'(\\d{1,4})', clean_match)
        
        # Escape special regex characters
        pattern = re.escape(pattern).replace(r'\(\\d\{1,4\}\)', r'(\d{1,4})')
        
        return pattern
    
    def save_updated_selectors(self):
        """Save updated selectors to file"""
        if self.updated_selectors:
            filename = f"updated_selectors_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(self.updated_selectors, f, indent=2)
            
            print(f"\n💾 Updated selectors saved to: {filename}")
            return filename
        else:
            print("📭 No selector updates to save")
            return None
    
    def generate_code_updates(self):
        """Generate Python code with updated selectors"""
        if not self.updated_selectors:
            return None
        
        code_lines = []
        code_lines.append("# Updated selectors based on site analysis")
        code_lines.append("UPDATED_SITE_CONFIGS = {")
        
        for source_name, config in self.updated_selectors.items():
            code_lines.append(f"    '{source_name}': {{")
            
            if config['css_selectors']:
                code_lines.append("        'css_selectors': [")
                for selector in config['css_selectors']:
                    code_lines.append(f"            '{selector}',")
                code_lines.append("        ],")
            
            if config['price_patterns']:
                code_lines.append("        'price_patterns': [")
                for pattern in config['price_patterns']:
                    code_lines.append(f"            r'{pattern}',")
                code_lines.append("        ],")
            
            code_lines.append("    },")
        
        code_lines.append("}")
        
        return "\n".join(code_lines)

def update_all_scrapers():
    """Update selectors for all sites with debug files"""
    print("🔄 UPDATING ALL SCRAPERS BASED ON DEBUG FILES")
    print("=" * 50)
    
    updater = SelectorUpdater()
    
    # Find all debug files
    debug_files = [f for f in os.listdir('.') if f.startswith('debug_') and f.endswith('.html')]
    
    if not debug_files:
        print("❌ No debug files found")
        return
    
    updated_count = 0
    
    for debug_file in debug_files:
        # Extract source name
        source_name = debug_file.replace('debug_', '').replace('.html', '').split('_')[0]
        
        # Skip if file is very old (older than 1 day)
        if os.path.getmtime(debug_file) < time.time() - 86400:
            continue
        
        if updater.update_site_selectors(source_name, debug_file):
            updated_count += 1
    
    print(f"\n📊 SUMMARY: Updated {updated_count} sources")
    
    # Save results
    saved_file = updater.save_updated_selectors()
    
    # Generate code
    code_updates = updater.generate_code_updates()
    if code_updates:
        with open('selector_updates.py', 'w') as f:
            f.write(code_updates)
        print("🐍 Generated selector_updates.py with new configurations")
        print("\n📋 TO APPLY UPDATES:")
        print("1. Review selector_updates.py")
        print("2. Merge selectors into main.py site configurations")
        print("3. Test updated scrapers")

if __name__ == "__main__":
    import time
    update_all_scrapers()
