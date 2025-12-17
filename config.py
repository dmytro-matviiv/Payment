import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8456055614:AAFeuIrPgQKDdfl_e9ULHi1oAJimxkaeLWM")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@payment_trc20_001")  # Username каналу

# Tronscan API Configuration
TRONSCAN_API_TOKEN = os.getenv("TRONSCAN_API_TOKEN", "3bfa787b-22a1-4c79-a2f5-b46dc062ee9f")
TRON_ADDRESS = os.getenv("TRON_ADDRESS", "TCKV8GCJcEzQWYi8c3yFGPvMa1UkUDYZ57")

# Monitoring Configuration
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))  # секунди між перевірками

