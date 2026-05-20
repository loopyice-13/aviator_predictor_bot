"""
Auto-Scraper for Aviator - Fetches live rounds automatically
"""

import time
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutoAviatorScraper:
    def __init__(self, platform: str = "1win", db_path: str = "aviator_data.db", headless: bool = True):
        self.platform = platform
        self.db_path = db_path
        self.headless = headless
        self.driver = None
        self.last_crash_point = None
        self.urls = {
            "1win": "https://1win.com/en/crash-aviator",
            "sportybet": "https://www.sportybet.com.gh/casino/aviator"
        }
        
        self.setup_driver()
        self._init_database()
        logger.info(f"✅ Scraper ready for {platform}")
    
    def setup_driver(self):
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.driver.set_page_load_timeout(30)
        logger.info("✅ Chrome driver initialized")
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crash_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crash_point REAL NOT NULL,
                platform TEXT DEFAULT '1win',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
    
    def navigate(self) -> bool:
        try:
            url = self.urls.get(self.platform)
            logger.info(f"🌐 Navigating to {self.platform}...")
            self.driver.get(url)
            time.sleep(5)
            logger.info(f"✅ Navigated to {self.platform}")
            return True
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False
    
    def get_latest_crash_point(self) -> Optional[float]:
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 
                    ".history-item, .multiplier, [data-multiplier], .aviator-history span"
                ))
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            selectors = [
                ".history-item:first-child span",
                ".history-item:first-child",
                ".multiplier:first-child",
                "[data-multiplier]:first-child",
                ".aviator-history span:first-child"
            ]
            
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        crash_point = self._parse_crash_point(text)
                        if crash_point:
                            return crash_point
                except:
                    continue
            
            patterns = soup.find_all(string=re.compile(r'd+.d+x', re.IGNORECASE))
            if patterns:
                return self._parse_crash_point(patterns[0].strip())
            
            return None
            
        except TimeoutException:
            logger.warning("⏱️ Timeout waiting for crash element")
            return None
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return None
    
    def _parse_crash_point(self, text: str) -> Optional[float]:
        try:
            match = re.search(r'(d+.?d*)s*x', text, re.IGNORECASE)
            if match:
                return float(match.group(1))
            return None
        except:
            return None
    
    def scrape_round(self) -> Optional[Dict]:
        crash_point = self.get_latest_crash_point()
        
        if crash_point and crash_point != self.last_crash_point:
            self.last_crash_point = crash_point
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO crash_data (crash_point, platform, timestamp) VALUES (?, ?, ?)",
                (crash_point, self.platform, datetime.now())
            )
            conn.commit()
            conn.close()
            
            round_data = {
                'crash_point': crash_point,
                'platform': self.platform,
                'timestamp': datetime.now()
            }
            
            logger.info(f"✈️ New round: {crash_point:.2f}x (Total: {self.get_total_rounds()})")
            return round_data
        
        return None
    
    def get_recent_crashes(self, limit: int = 100) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT crash_point, platform, timestamp FROM crash_data "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'crash_point': row[0],
                'platform': row[1],
                'timestamp': datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
            }
            for row in rows
        ]
    
    def get_total_rounds(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crash_data")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def close(self):
        if self.driver:
            self.driver.quit()
            logger.info("✅ Browser closed")


scraper_instance = None

def get_scraper(platform: str = "1win") -> AutoAviatorScraper:
    global scraper_instance
    if scraper_instance is None or scraper_instance.platform != platform:
        scraper_instance = AutoAviatorScraper(platform=platform)
    return scraper_instance