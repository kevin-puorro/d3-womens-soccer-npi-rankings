# Daily Rolling NCAA Scraper - Perfect for GitHub Actions
# Scrapes only the previous 3 days, merges with existing data

import time
import os
import json
import pandas as pd
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class DailyRollingNCAAScraper:
    def __init__(self, headless=True, delay_between_requests=2):
        """
        Daily rolling scraper for GitHub Actions
        
        Args:
            headless (bool): Run browser in headless mode (True for GitHub Actions)
            delay_between_requests (int): Seconds to wait between page requests
        """
        self.headless = headless
        self.delay = delay_between_requests
        self.data_dir = "data"
        self.games_file = os.path.join(self.data_dir, "all_season_games.json")
        self.log_file = os.path.join(self.data_dir, "scraping_log.json")
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
    def setup_driver(self):
        """Set up Chrome WebDriver optimized for GitHub Actions"""
        chrome_options = Options()
        
        # Required for GitHub Actions
        if self.headless:
            chrome_options.add_argument("--headless")
            
        # GitHub Actions optimized options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # GitHub Actions provides chromedriver automatically, but use webdriver-manager as fallback
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Remove automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver

    def get_target_dates(self, days_back=3, reference_date=None):
        """
        Get the target dates to scrape (previous N days)
        
        Args:
            days_back (int): How many days back to scrape (default 3)
            reference_date (datetime): Date to calculate from (default: today)
            
        Returns:
            list: List of datetime objects to scrape
        """
        if reference_date is None:
            reference_date = datetime.now()
            
        target_dates = []
        for i in range(days_back):
            date = reference_date - timedelta(days=i+1)  # Yesterday, day before, etc.
            target_dates.append(date)
            
        return sorted(target_dates)  # Oldest first

    def create_scoreboard_url(self, date):
        """Create NCAA scoreboard URL for a specific date"""
        return f"https://www.ncaa.com/scoreboard/soccer-women/d3/{date.year}/{date.month:02d}/{date.day:02d}/all-conf"

    def extract_date_from_url(self, url):
        """Extract date from NCAA scoreboard URL"""
        date_pattern = r'/(\d{4})/(\d{2})/(\d{2})/'
        match = re.search(date_pattern, url)
        
        if match:
            year, month, day = match.groups()
            try:
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                return None
        return None

    def scrape_single_date(self, url):
        """
        Scrape games for a single date (streamlined version)
        
        Args:
            url (str): NCAA scoreboard URL for specific date
            
        Returns:
            tuple: (games_list, success_boolean, error_message)
        """
        game_date = self.extract_date_from_url(url)
        if not game_date:
            return [], False, "Could not extract date from URL"
        
        driver = self.setup_driver()
        
        try:
            print(f"📅 Scraping: {game_date}")
            
            driver.get(url)
            time.sleep(self.delay)
            
            # Wait for page load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for blocking
            page_title = driver.title.lower()
            if "403" in page_title or "forbidden" in page_title:
                return [], False, f"Access blocked for {game_date}"
            
            time.sleep(2)  # Let page render
            
            # Find games
            games_data = []
            try:
                status_elements = driver.find_elements(By.CSS_SELECTOR, ".status-final")
                
                if not status_elements:
                    print(f"   ℹ️  No games found for {game_date}")
                    return [], True, "No games found (not an error)"
                
                # Get meaningful content
                game_elements = [elem for elem in status_elements 
                               if elem.text.strip() or elem.find_element(By.XPATH, "..").text.strip()]
                
                if not game_elements:
                    return [], True, "No meaningful game content"
                
                # Parse games (simplified version of your logic)
                combined_text = game_elements[0].find_element(By.XPATH, "..").text.strip()
                lines = combined_text.split('\n')
                
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    if line.startswith("FINAL"):
                        if i + 4 < len(lines):
                            try:
                                team1 = lines[i + 1].strip()
                                score1 = int(lines[i + 2].strip())
                                team2 = lines[i + 3].strip()
                                score2 = int(lines[i + 4].strip())
                                
                                game_data = {
                                    'game_date': game_date,
                                    'status': line,
                                    'away_team': team1,
                                    'away_team_score': score1,
                                    'home_team': team2,
                                    'home_team_score': score2,
                                    'scraped_at': datetime.now().isoformat(),
                                    'source_url': url
                                }
                                games_data.append(game_data)
                                i += 5
                                continue
                                
                            except (ValueError, IndexError):
                                pass
                        i += 1
                    else:
                        i += 1
                
                print(f"   ✅ Found {len(games_data)} games")
                return games_data, True, None
                
            except Exception as e:
                return [], False, f"Parsing error: {str(e)}"
            
        except TimeoutException:
            return [], False, f"Timeout loading {game_date}"
        except Exception as e:
            return [], False, f"Scraping error: {str(e)}"
        finally:
            driver.quit()

    def load_existing_games(self):
        """Load existing games from previous runs"""
        if os.path.exists(self.games_file):
            try:
                with open(self.games_file, 'r') as f:
                    games = json.load(f)
                print(f"📂 Loaded {len(games)} existing games")
                return games
            except Exception as e:
                print(f"⚠️  Error loading existing games: {e}")
                return []
        else:
            print("📂 No existing games file found - starting fresh")
            return []

    def merge_games(self, existing_games, new_games):
        """
        Merge new games with existing games, avoiding duplicates
        
        Args:
            existing_games (list): Previously scraped games
            new_games (list): Newly scraped games
            
        Returns:
            tuple: (merged_games, new_games_added, duplicates_skipped)
        """
        # Create a set of existing game signatures for fast lookup
        existing_signatures = set()
        for game in existing_games:
            signature = f"{game['game_date']}_{game['home_team']}_{game['away_team']}_{game['home_team_score']}_{game['away_team_score']}"
            existing_signatures.add(signature)
        
        # Merge new games, skipping duplicates
        merged_games = existing_games.copy()
        new_count = 0
        duplicate_count = 0
        
        for game in new_games:
            signature = f"{game['game_date']}_{game['home_team']}_{game['away_team']}_{game['home_team_score']}_{game['away_team_score']}"
            
            if signature in existing_signatures:
                duplicate_count += 1
            else:
                merged_games.append(game)
                existing_signatures.add(signature)
                new_count += 1
        
        return merged_games, new_count, duplicate_count

    def save_games(self, games):
        """Save games to JSON and CSV files"""
        # Save JSON
        with open(self.games_file, 'w') as f:
            json.dump(games, f, indent=2)
        
        # Save CSV for easy viewing
        csv_file = os.path.join(self.data_dir, "all_season_games.csv")
        df = pd.DataFrame(games)
        df.to_csv(csv_file, index=False)
        
        print(f"💾 Saved {len(games)} total games to files")

    def update_log(self, run_info):
        """Update the scraping log"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'run_info': run_info
        }
        
        # Load existing log
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    log = json.load(f)
            except:
                log = []
        else:
            log = []
        
        # Add new entry
        log.append(log_entry)
        
        # Keep only last 30 runs
        log = log[-30:]
        
        # Save log
        with open(self.log_file, 'w') as f:
            json.dump(log, f, indent=2)

    def run_daily_scrape(self, days_back=3):
        """
        Main function for daily scraping (perfect for GitHub Actions)
        
        Args:
            days_back (int): How many days back to scrape (default 3)
            
        Returns:
            dict: Summary of the scraping run
        """
        print(f"🚀 DAILY NCAA ROLLING SCRAPER")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Scraping previous {days_back} days")
        print("=" * 50)
        
        # Get target dates
        target_dates = self.get_target_dates(days_back)
        print(f"🎯 Target dates: {[d.strftime('%Y-%m-%d') for d in target_dates]}")
        
        # Load existing games
        existing_games = self.load_existing_games()
        
        # Scrape each target date
        all_new_games = []
        run_summary = {
            'dates_attempted': len(target_dates),
            'dates_successful': 0,
            'dates_failed': 0,
            'total_new_games': 0,
            'errors': []
        }
        
        for date in target_dates:
            url = self.create_scoreboard_url(date)
            games, success, error = self.scrape_single_date(url)
            
            if success:
                run_summary['dates_successful'] += 1
                all_new_games.extend(games)
            else:
                run_summary['dates_failed'] += 1
                run_summary['errors'].append(f"{date.strftime('%Y-%m-%d')}: {error}")
                print(f"   ❌ Failed: {error}")
            
            # Small delay between dates
            time.sleep(1)
        
        # Merge with existing games
        if all_new_games:
            merged_games, new_count, duplicate_count = self.merge_games(existing_games, all_new_games)
            
            print(f"\n📊 MERGE RESULTS:")
            print(f"   New games found: {len(all_new_games)}")
            print(f"   Actually new (not duplicates): {new_count}")
            print(f"   Duplicates skipped: {duplicate_count}")
            print(f"   Total games in database: {len(merged_games)}")
            
            # Save updated games
            self.save_games(merged_games)
            
            run_summary['total_new_games'] = new_count
            run_summary['duplicates_skipped'] = duplicate_count
            run_summary['total_games_in_db'] = len(merged_games)
            
        else:
            print(f"\n📊 No new games found")
            run_summary['total_new_games'] = 0
            run_summary['total_games_in_db'] = len(existing_games)
        
        # Update log
        self.update_log(run_summary)
        
        # Summary
        print(f"\n✅ DAILY SCRAPE COMPLETE")
        print(f"   Successful dates: {run_summary['dates_successful']}/{run_summary['dates_attempted']}")
        print(f"   New games added: {run_summary['total_new_games']}")
        print(f"   Total games in database: {run_summary['total_games_in_db']}")
        
        if run_summary['errors']:
            print(f"   Errors: {len(run_summary['errors'])}")
            for error in run_summary['errors']:
                print(f"     - {error}")
        
        return run_summary


def main():
    """Main function for command line usage"""
    print("🔄 Daily Rolling NCAA Scraper")
    
    # Create scraper
    scraper = DailyRollingNCAAScraper(
        headless=False,  # Set to True for GitHub Actions
        delay_between_requests=2
    )
    
    # Run daily scrape
    summary = scraper.run_daily_scrape(days_back=3)
    
    return summary


if __name__ == "__main__":
    summary = main()
