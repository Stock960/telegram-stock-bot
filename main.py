import os
import time
import threading
import requests
from flask import Flask

# Initialize Flask so Render sees a live web service port
app = Flask(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "PASTE_YOUR_TELEGRAM_CHAT_ID"

# Your Watchlist
ALERTS = {
    "AAPL": 175.00,
    "RELIANCE.NS": 2400.00
}
# =======================================================

@app.route('/')
def home():
    return "Stock Tracker Server is Active and Running!", 200

def get_live_price(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except Exception as e:
        print(f"Error reading {ticker}: {e}")
        return None

def send_telegram(message):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(api_url, json=payload)

def stock_monitor_loop():
    """Background loop tracking prices independently of the web traffic."""
    print("Background Monitoring Thread Initialized.")
    while True:
        print("\n--- Running stock validation check ---")
        for ticker, stop_loss in ALERTS.items():
            current_price = get_live_price(ticker)
            if current_price:
                print(f"{ticker}: {current_price} (Target: {stop_loss})")
                if current_price <= stop_loss:
                    msg = f"🚨 *TRIGGER ALERT* 🚨\n\n• *Ticker:* {ticker}\n• *Trigger:* {stop_loss}\n• *Live Price:* {current_price}"
                    send_telegram(msg)
        
        time.sleep(300) # Wait exactly 5 minutes (300 seconds)

# Start the tracker loop on an independent thread before running the web app
monitor_thread = threading.Thread(target=stock_monitor_loop, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    # Render binds dynamic port assignments via env variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
