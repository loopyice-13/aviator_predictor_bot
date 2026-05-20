import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
DATABASE_PATH = "aviator_data.db"
SCRAPE_INTERVAL_SECONDS = 30
DEFAULT_PLATFORM = "1win"
TARGET_MIN_MULTIPLIER = 1.1
TARGET_MAX_MULTIPLIER = 2.7
MIN_DATA_POINTS = 30
ONEWIN_URL = "https://1win.com/en/crash-aviator"
SPORTYBET_URL = "https://www.sportybet.com.gh/casino/aviator"