import os
import time
import threading
import yfinance as yf
from flask import Flask

app = Flask(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "PASTE_YOUR_TELEGRAM_CHAT_ID"

# 50 Stocks Database: {"TICKER": Stop_Loss_Price}
# Add up to 50-100 tickers here. Use space-separated matching strings or suffixes (.NS for NSE India)
ALERTS = {
    "SANDUMA": 255.00,
    "TSLA": 160.00,
    "NVDA": 800.00,
    "MSFT": 390.00,
    "AMZN": 170.00,
    "RELIANCE.NS": 2400.00,
    "TCS.NS": 3800.00,
    "INFY.NS": 1400.00,
    # Add your remaining stocks here seamlessly...
}
# =======================================================

# State Engine: Tracks if you've already been messaged to prevent notification spam
TRIGGERED_ALERTS = {ticker: False for ticker in ALERTS}

@app.route('/')
def home():
    return "Multi-Asset Live Stock Server Running Fine!", 200

def send_telegram(message):
    import requests
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(api_url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def stock_monitor_loop():
    print("Multi-Asset Monitor Initialized Successfully.")
    
    # Create a clean string format of all tickers for the batch request
    ticker_string = " ".join(ALERTS.keys())
    
    while True:
        print(f"\n--- Batch scanning {len(ALERTS)} assets ---")
        try:
            # Crucial: This downloads all 50 stock quotes simultaneously in 1 single web call
            data = yf.download(tickers=ticker_string, period="1d", interval="1m", group_by='ticker', progress=False)
            
            for ticker, stop_loss in ALERTS.items():
                try:
                    # Extract the latest 1-minute close price for the specific stock
                    if len(ALERTS) == 1:
                        current_price = data['Close'].iloc[-1]
                    else:
                        current_price = data[ticker]['Close'].iloc[-1]
                        
                    # Filter out NaN errors from closed markets
                    if str(current_price) == 'nan' or current_price is None:
                        continue
                        
                    print(f"{ticker}: {current_price:.2f} | StopLoss: {stop_loss}")

                    # Check Target Parameters
                    if current_price <= stop_loss:
                        # Only send if we haven't alerted for this breach yet
                        if not TRIGGERED_ALERTS[ticker]:
                            msg = (
                                f"🚨 *CRITICAL TRADING ALERT* 🚨\n\n"
                                f"• *Asset:* `{ticker}`\n"
                                f"• *Breached Level:* {stop_loss}\n"
                                f"• *Current Price:* {current_price:.2f}\n\n"
                                f"⚠️ Position crossed target threshold."
                            )
                            send_telegram(msg)
                            TRIGGERED_ALERTS[ticker] = True # Lock alert out
                            
                    else:
                        # Reset the lock toggle if the price recovers back above stop loss
                        if TRIGGERED_ALERTS[ticker]:
                            print(f"♻️ Resetting alert lock for {ticker} as price recovered.")
                            TRIGGERED_ALERTS[ticker] = False

                except Exception as inner_error:
                    # Individual stock extraction protection loop
                    continue

        except Exception as e:
            print(f"Batch download network execution error: {e}")
            
        time.sleep(300) # Check every 5 minutes safely

# Spin loop execution context on background layer thread
monitor_thread = threading.Thread(target=stock_monitor_loop, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
