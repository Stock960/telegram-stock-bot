import os
import time
import csv
import threading
import yfinance as yf
from flask import Flask

app = Flask(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "PASTE_YOUR_TELEGRAM_CHAT_ID"
# =======================================================

TRIGGERED_ALERTS = {}

@app.route('/')
def home():
    return "Excel-Synced Live Monitor Active with Blank-Cell Filtering!", 200

def send_telegram(message):
    import requests
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(api_url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def parse_watchlist():
    stocks_data = {}
    try:
        with open("watchlist.txt", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                ticker = row.get("Stock", "").strip()
                if not ticker:
                    continue
                
                try:
                    # Strip spaces and map fields. If cell is empty, it saves as None or empty string.
                    stocks_data[ticker] = {
                        "elliot": row.get("Elliot position", "").strip(),
                        "price_breakout": row.get("Price Breakout", "").strip(),
                        "rsi_breakout": row.get("RSI Breakout", "").strip(),
                        "buying_zone": row.get("Buying zone", "").strip(),
                        "stop_loss": float(row.get("Stop Loss", 0)) if row.get("Stop Loss", "").strip() else None,
                        "target": float(row.get("Target", 0)) if row.get("Target", "").strip() else None,
                        "remarks": row.get("Remarks", "").strip()
                    }
                except ValueError:
                    print(f"Skipping row formatting error for ticker: {ticker}")
                    continue
    except Exception as e:
        print(f"Error reading watchlist.txt: {e}")
    return stocks_data

def stock_monitor_loop():
    print("Initializing Dynamic Custom Monitor Engine...")
    
    while True:
        watchlist = parse_watchlist()
        
        if not watchlist:
            print("Watchlist empty or file formatting incorrect. Sleeping...")
            time.sleep(60)
            continue
            
        tickers_string = " ".join(watchlist.keys())
        print(f"\n--- Batch scanning {len(watchlist)} Excel stocks ---")
        
        try:
            data = yf.download(tickers=tickers_string, period="1d", interval="1m", group_by='ticker', progress=False)
            
            for ticker, config in watchlist.items():
                try:
                    if len(watchlist) == 1:
                        current_price = data['Close'].iloc[-1]
                    else:
                        current_price = data[ticker]['Close'].iloc[-1]
                        
                    if str(current_price) == 'nan' or current_price is None:
                        continue
                    
                    if ticker not in TRIGGERED_ALERTS:
                        TRIGGERED_ALERTS[ticker] = {"sl_hit": False, "tg_hit": False}
                    
                    stop_loss = config["stop_loss"]
                    target = config["target"]
                    
                    sl_triggered = stop_loss and (current_price <= stop_loss)
                    tg_triggered = target and (current_price >= target)
                    
                    if (sl_triggered and not TRIGGERED_ALERTS[ticker]["sl_hit"]) or \
                       (tg_triggered and not TRIGGERED_ALERTS[ticker]["tg_hit"]):
                        
                        status_headline = "🚨 *STOP LOSS BREACHED* 🚨" if sl_triggered else "🎯 *TARGET ACHIEVED* 🎯"
                        
                        # --- DYNAMIC MESSAGE BUILDING ---
                        # Start with the core lines that will always be there
                        lines = [
                            status_headline,
                            "",
                            f"• *Stock:* `{ticker}`",
                            f"• *Current Price:* {current_price:.2f}"
                        ]
                        
                        # Only append these optional lines if they actually contain data in Excel
                        if config['elliot']: 
                            lines.append(f"• *Elliot Position:* {config['elliot']}")
                        if config['price_breakout']: 
                            lines.append(f"• *Price Breakout:* {config['price_breakout']}")
                        if config['rsi_breakout']: 
                            lines.append(f"• *RSI Breakout:* {config['rsi_breakout']}")
                        if config['buying_zone']: 
                            lines.append(f"• *Buying Zone:* {config['buying_zone']}")
                        if stop_loss: 
                            lines.append(f"• *Stop Loss:* {stop_loss}")
                        if target: 
                            lines.append(f"• *Target:* {target}")
                        if config['remarks']: 
                            lines.append(f"• *Remarks:* {config['remarks']}")
                        
                        # Join all valid lines together with newlines
                        custom_msg = "\n".join(lines)
                        
                        send_telegram(custom_msg)
                        
                        if sl_triggered: TRIGGERED_ALERTS[ticker]["sl_hit"] = True
                        if tg_triggered: TRIGGERED_ALERTS[ticker]["tg_hit"] = True
                        
                    if stop_loss and current_price > stop_loss:
                        TRIGGERED_ALERTS[ticker]["sl_hit"] = False
                    if target and current_price < target:
                        TRIGGERED_ALERTS[ticker]["tg_hit"] = False

                except Exception as cell_err:
                    print(f"Error checking {ticker}: {cell_err}")
                    continue
                    
        except Exception as e:
            print(f"Network error: {e}")
            
        time.sleep(300)

monitor_thread = threading.Thread(target=stock_monitor_loop, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
