"""
49's Lottery Scraper - JSON-LD Method with Duplicate Removal
Optimized for Render.com Docker environment
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import json
import requests
from datetime import datetime

class Lottery49sScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        self.driver = None
        
    def start(self):
        """Start the browser using webdriver-manager (automatically matches Chrome version)"""
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.options)
        return self
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
    
    def handle_popups(self):
        """Handle age verification and cookie consent popups"""
        try:
            yes_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Yes, I am over 18 years old')]"))
            )
            yes_button.click()
            print("  ✓ Age verified")
            time.sleep(1)
        except:
            print("  ✓ No age verification needed")
        
        try:
            allow_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Allow cookies')]"))
            )
            allow_button.click()
            print("  ✓ Cookies accepted")
            time.sleep(1)
        except:
            print("  ✓ No cookie popup needed")
    
    def wait_for_jsonld(self, timeout=15):
        """Wait for JSON-LD scripts to appear in the page"""
        print(f"  Waiting for JSON-LD data (max {timeout} seconds)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            html = self.driver.page_source
            if 'application/ld+json' in html and 'Draw Results' in html:
                print(f"  ✓ JSON-LD detected after {int(time.time() - start_time)} seconds")
                return True
            time.sleep(0.5)
        
        print(f"  ⚠️ JSON-LD not detected within {timeout} seconds")
        return False
    
    def extract_jsonld_draws(self, html_content: str):
        """Extract lottery draws from JSON-LD structured data and remove duplicates"""
        soup = BeautifulSoup(html_content, 'html.parser')
        draws = []
        seen_draws = set()
        
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                if (data.get('@type') == 'Event' and 
                    'resultNumbers' in data and 
                    'Draw Results' in data.get('name', '')):
                    
                    draw_name = data['name'].replace(' Draw Results', '').strip()
                    numbers_tuple = tuple(data['resultNumbers'])
                    bonus_value = data['bonusNumbers'][0] if data.get('bonusNumbers') else None
                    
                    unique_key = f"{draw_name}_{numbers_tuple}_{bonus_value}"
                    
                    if unique_key not in seen_draws:
                        seen_draws.add(unique_key)
                        
                        draw = {
                            'draw_name': draw_name,
                            'numbers': data['resultNumbers'],
                            'bonus': bonus_value,
                            'date': data.get('startDate', '')[:10] if data.get('startDate') else None,
                        }
                        
                        draws.append(draw)
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"  Error parsing script: {e}")
        
        return draws
    
    def scrape_today(self):
        """Scrape today's lottery results using JSON-LD method"""
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"https://49s.co.uk/49s/results/{today}"
        
        print(f"\n{'='*60}")
        print(f"49's LOTTERY SCRAPER")
        print(f"Date: {today}")
        print(f"Method: JSON-LD Structured Data")
        print(f"URL: {url}")
        print(f"{'='*60}\n")
        
        print("[1/5] Loading page...")
        self.driver.get(url)
        
        print("[2/5] Waiting for initial page load...")
        time.sleep(2)
        
        print("[3/5] Handling popups...")
        self.handle_popups()
        
        print("[4/5] Waiting for structured data...")
        self.wait_for_jsonld(timeout=15)
        
        print("[5/5] Extracting JSON-LD structured data...")
        html_content = self.driver.page_source
        draws = self.extract_jsonld_draws(html_content)
        
        for draw in draws:
            if not draw.get('date'):
                draw['date'] = today
        
        print(f"\n  📊 Found {len(draws)} unique draws (duplicates removed)")
        
        return {
            'date': today,
            'draws': draws,
            'total_draws': len(draws),
            'method': 'JSON-LD Structured Data',
            'scraped_at': datetime.now().isoformat(),
            'source': url
        }
    
    def send_to_api(self, results, api_url="https://uk49s.online/get_results.php"):
        """Send the scraped results to your API endpoint"""
        print(f"\n{'='*60}")
        print(f"SENDING DATA TO API")
        print(f"URL: {api_url}")
        print(f"{'='*60}\n")
        
        payload = {
            'date': results['date'],
            'draws': results['draws'],
            'total_draws': results['total_draws'],
            'scraped_at': results['scraped_at'],
            'source': results['source']
        }
        
        print(f"📦 Payload size: {len(json.dumps(payload))} bytes")
        print(f"🎯 Number of draws: {results['total_draws']}")
        
        for draw in results['draws']:
            print(f"   - {draw['draw_name']}: {draw['numbers']} (Bonus: {draw.get('bonus', 'N/A')})")
        
        try:
            response = requests.post(
                api_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"\n📡 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Data sent successfully!")
                try:
                    response_data = response.json()
                    print(f"📝 Server response: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"📝 Server response: {response.text}")
                return True
            else:
                print(f"❌ Failed to send data. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection error: Could not reach the server")
            return False
        except requests.exceptions.Timeout:
            print("❌ Timeout error: Server did not respond in time")
            return False
        except Exception as e:
            print(f"❌ Error sending data: {e}")
            return False
    
    def save_to_json(self, results):
        """Save local backup"""
        filename = f"49s_{results['date']}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Local backup saved to: {filename}")
        return filename
    
    def print_results(self, results):
        """Pretty print the results"""
        print("\n" + "="*60)
        print(f"SCRAPED RESULTS - {results['date']}")
        print("="*60)
        
        if results['draws']:
            for draw in results['draws']:
                print(f"\n🎯 {draw['draw_name']}")
                print(f"   Numbers: {' '.join(map(str, draw['numbers']))}")
                if draw['bonus']:
                    print(f"   Bonus: {draw['bonus']}")
            
            print("\n" + "="*60)
            print(f"✅ Total unique draws: {results['total_draws']}")


def main():
    """Main execution - scrape and send to API"""
    print("="*60)
    print("49's LOTTERY SCRAPER - with Duplicate Removal")
    print("="*60)
    
    scraper = Lottery49sScraper(headless=True)
    scraper.start()
    
    try:
        print("\n📊 STEP 1: Scraping lottery results...")
        results = scraper.scrape_today()
        
        if results['draws']:
            scraper.print_results(results)
            scraper.save_to_json(results)
            
            print("\n📤 STEP 2: Sending to API...")
            success = scraper.send_to_api(results)
            
            if success:
                print("\n" + "="*60)
                print("🎉 COMPLETE! Data scraped and sent successfully")
                print("="*60)
            else:
                print("\n" + "="*60)
                print("⚠️ Data scraped but failed to send to API")
                print("="*60)
        else:
            print("\n❌ No draws found for today")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()
        print("\n✓ Browser closed")


if __name__ == "__main__":
    main()
