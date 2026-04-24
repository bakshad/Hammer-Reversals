import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import csv
import logging
from datetime import datetime
import concurrent.futures

# --- Silence Noise ---
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# --- CONFIGURATION ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status_scalp.json"
POSITIONS_FILE = "active_positions_scalp.json"
TRADE_LOG = "scalp_trade_summary.csv"

# --- SYMBOLS LIST (FULL F&O) ---
SYMBOLS = ["^NSEI", "^NSEBANK", "COALINDIA.NS", "NATIONALUM.NS", "RELIANCE.NS", "SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "TCS.NS", "INFY.NS", "TRENT.NS", "HAL.NS"]

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def safe_fetch(symbol, period="5d", interval="5m"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def get_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    
    # MACD
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 9 EMA
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    return df

def manage_positions(positions):
    updated = positions.copy()
    for symbol, trade in positions.items():
        df = yf.download(symbol, period="1d", interval="15m", progress=False)
        if df is None or df.empty: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        curr_price, ema_val = float(df['Close'].iloc[-1]), float(df['EMA9'].iloc[-1])
        
        # Trailing Exit Logic
        exit_sig = (trade['Side'] == "🟢 BUY" and curr_price < ema_val) or \
                   (trade['Side'] == "🔴 SELL" and curr_price > ema_val)
        
        if exit_sig:
            pts = round(curr_price - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr_price, 2)
            pct = round((pts / trade['Entry']) * 100, 2)
            with open(TRADE_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), symbol, trade['Side'], trade['Entry'], curr_price, pts, pct])
            send_telegram(f"🏁 **ELITE EXIT: {symbol.replace('.NS','')}**\nPts: {pts:+.2f} ({pct:+.2f}%)")
            del updated[symbol]
    return updated

def process_symbol(symbol, memory, positions):
    df = safe_fetch(symbol)
    if df is None: return None
    df = get_indicators(df)
    
    curr, prev = df.iloc[-1], df.iloc[-2]
    prev_vol_avg = df['Volume'].iloc[-4:-1].mean()
    vol_surge = curr['Volume'] > (prev_vol_avg * 2.0) # 2x Volume Surge
    
    # ELITE CRITERIA: RSI Extremes + Volume U-Shape
    is_elite_buy = (curr['RSI'] < 30) and (curr['Close'] > prev['High']) and vol_surge
    is_elite_sell = (curr['RSI'] > 70) and (curr['Close'] < prev['Low']) and vol_surge
    
    if (is_elite_buy or is_elite_sell) and str(df.index[-1]) not in memory:
        side = "🟢 BUY" if is_elite_buy else "🔴 SELL"
        msg = (f"💎 **ELITE SNIPER SIGNAL** 💎\n"
               f"---------------------------\n"
               f"📦 **Stock:** {symbol.replace('.NS','')}\n"
               f"🔥 **Action:** {side}\n"
               f"📊 **Volume:** {curr['Volume']/prev_vol_avg:.1f}x Surge\n"
               f"💰 **Entry:** {curr['Close']:.2f} | **RSI:** {curr['RSI']:.1f}\n"
               f"🚀 **Target:** Ride 9 EMA")
        
        send_telegram(msg)
        return {"symbol_ts": str(df.index[-1]), "symbol": symbol, "trade_data": {"Entry": round(curr['Close'], 2), "Side": side, "InitialSL": prev['Low'] if is_elite_buy else prev['High']}}
    return None

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_positions(pos)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, mem, pos): s for s in SYMBOLS}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                mem[res["symbol_ts"]], pos[res["symbol"]] = True, res["trade_data"]
                save_json(mem, MEMORY_FILE); save_json(pos, POSITIONS_FILE)
