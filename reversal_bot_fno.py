import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import csv
from datetime import datetime

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status.json"
POSITIONS_FILE = "active_positions.json" # Tracks open trades
ML_LOG = "ml_training_data.csv"
TRADE_LOG = "weekly_trade_summary.csv" # Logs finished trades

# April 2026 F&O Universe (Keep your full list here)
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "ADANIPOWER.NS", "COCHINSHIP.NS", 
    "FORCEMOT.NS", "GODFRYPHLP.NS", "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", 
    "VMM.NS", "SWIGGY.NS", "RELIANCE.NS", "HDFCBANK.NS", "SBIN.NS", "ICICIBANK.NS"
    # ... rest of your symbols
]

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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try: requests.get(url, timeout=10)
    except: pass

def log_ml_data(data):
    file_exists = os.path.isfile(ML_LOG)
    with open(ML_LOG, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists: writer.writeheader()
        writer.writerow(data)

def calculate_woodie_pivots(symbol):
    try:
        df_daily = yf.download(symbol, period="2d", interval="1d", progress=False)
        if len(df_daily) < 2: return None
        prev = df_daily.iloc[-2]
        h, l, c = prev['High'], prev['Low'], prev['Close']
        pp = (h + l + 2 * c) / 4
        return {"R1": (2 * pp) - l, "PP": pp, "S1": (2 * pp) - h}
    except: return None

def is_hammer_star(candle):
    body = abs(candle['Open'] - candle['Close'])
    l_shadow = min(candle['Open'], candle['Close']) - candle['Low']
    u_shadow = candle['High'] - max(candle['Open'], candle['Close'])
    hammer = (l_shadow > body * 1.3 and u_shadow < body * 0.8)
    star = (u_shadow > body * 1.3 and l_shadow < body * 0.8)
    return hammer, star

def manage_positions(positions):
    """Monitors active trades for EMA9 crossover exit."""
    updated_positions = positions.copy()
    
    for symbol, trade in positions.items():
        try:
            df = yf.download(symbol, period="2d", interval="15m", progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['EMA9'] = df['Close'].ewm(span=9).mean()
            curr = df.iloc[-1]
            
            exit_triggered = False
            if trade['Side'] == "🟢 BUY" and curr['Close'] < curr['EMA9']:
                exit_triggered = True
            elif trade['Side'] == "🔴 SELL" and curr['Close'] > curr['EMA9']:
                exit_triggered = True
            
            if exit_triggered:
                points = round(curr['Close'] - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr['Close'], 2)
                pct = round((points / trade['Entry']) * 100, 2)
                emoji = "💰" if points > 0 else "🛑"
                
                msg = (f"{emoji} **EXIT ALERT: {symbol.replace('.NS','')}**\n"
                       f"Side: {trade['Side']}\n"
                       f"Entry: {trade['Entry']:.2f} | Exit: {curr['Close']:.2f}\n"
                       f"**Captured: {points} pts ({pct}%)**")
                
                send_telegram(msg)
                
                # Log to Weekly CSV
                file_exists = os.path.isfile(TRADE_LOG)
                with open(TRADE_LOG, 'a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists: writer.writerow(["Date", "Symbol", "Side", "Entry", "Exit", "Pts", "Pct"])
                    writer.writerow([datetime.now().strftime("%Y-%m-%d"), symbol, trade['Side'], trade['Entry'], curr['Close'], points, pct])
                
                del updated_positions[symbol]
        except Exception as e:
            print(f"Error managing {symbol}: {e}")
            
    return updated_positions

def get_signal(symbol, memory, positions):
    try:
        df = yf.download(symbol, period="15d", interval="15m", progress=False)
        pivots = calculate_woodie_pivots(symbol)
        if df.empty or not pivots: return memory, positions
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        
        lookback = df.iloc[-5:-1] 
        sig, curr = df.iloc[-2], df.iloc[-1]
        ts = str(df.index[-2])
        
        has_hammer_base = any([is_hammer_star(lookback.iloc[i])[0] for i in range(len(lookback))])
        has_star_base = any([is_hammer_star(lookback.iloc[i])[1] for i in range(len(lookback))])

        prior_swing_high, prior_swing_low = lookback['High'].max(), lookback['Low'].min()
        is_bull_vflip = (lookback['Low'].iloc[-1] < lookback['Low'].iloc[0]) and (curr['Close'] > prior_swing_high) and has_hammer_base
        is_bear_vflip = (lookback['High'].iloc[-1] > lookback['High'].iloc[0]) and (curr['Close'] < prior_swing_low) and has_star_base

        # Only signal if not already in memory AND not already in an active position
        if (is_bull_vflip or is_bear_vflip) and f"{symbol}_{ts}" not in memory and symbol not in positions:
            near_s1 = abs(lookback['Low'].min() - pivots['S1']) / pivots['S1'] < 0.0015
            near_r1 = abs(lookback['High'].max() - pivots['R1']) / pivots['R1'] < 0.0015
            
            quality = "💎 ELITE (Pivot + PA)" if (near_s1 or near_r1) else "🚀 HIGH (V-PA Confirmed)"
            side = "🟢 BUY" if is_bull_vflip else "🔴 SELL"
            
            log_ml_data({
                "Timestamp": ts, "Symbol": symbol, "Side": side, "Quality": quality,
                "Entry": round(curr['Close'], 2), "EMA9": round(curr['EMA9'], 2)
            })

            msg = (f"🎯 **{side}: {symbol.replace('.NS', '')}**\n"
                   f"---------------------------\n"
                   f"📊 **Quality:** {quality}\n"
                   f"🧩 **Logic:** Hammer-Base V-Flip\n"
                   f"💰 **Entry:** {curr['Close']:.2f}\n"
                   f"🛡️ **SL:** {lookback['Low'].min() if is_bull_vflip else lookback['High'].max():.2f}\n"
                   f"📈 **Trail SL (EMA9):** {curr['EMA9']:.2f}\n"
                   f"---------------------------\n"
                   f"🎯 **T1 (Woodie PP):** {pivots['PP']:.2f}")
            
            send_telegram(msg)
            memory[f"{symbol}_{ts}"] = True
            positions[symbol] = {"Entry": curr['Close'], "Side": side, "Time": datetime.now().isoformat()}

    except Exception: pass
    return memory, positions

if __name__ == "__main__":
    mem = load_json(MEMORY_FILE)
    positions = load_json(POSITIONS_FILE)
    
    # 1. First, check and exit old trades
    positions = manage_positions(positions)
    
    # 2. Then, scan for new entries
    for s in SYMBOLS:
        mem, positions = get_signal(s, mem, positions)
        
    save_json(mem, MEMORY_FILE)
    save_json(positions, POSITIONS_FILE)
