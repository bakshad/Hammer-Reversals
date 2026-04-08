import yfinance as yf
import pandas as pd
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status.json"

# Full F&O List (Updated April 2026)
FNO_SYMBOLS = ["RELIANCE.NS", "HDFCBANK.NS", "SBIN.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS", "TATAMOTORS.NS", "ADANIPOWER.NS", "ZOMATO.NS", "HAL.NS", "COCHINSHIP.NS", "HYUNDAI.NS"]

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=4)

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try: requests.get(url, timeout=10)
    except: pass

def get_signal(symbol, memory):
    try:
        # 1. Pivot Calculations (Daily/Weekly)
        d_data = yf.download(symbol, period="5d", interval="1d", progress=False)
        w_data = yf.download(symbol, period="20d", interval="1wk", progress=False)
        if d_data.empty or len(d_data) < 2: return memory

        def woodie(h, l, c):
            pp = (h + l + 2 * c) / 4
            return {"PP": pp, "R1": (2*pp)-l, "R2": pp+(h-l), "S1": (2*pp)-h, "S2": pp-(h-l)}

        dp = woodie(d_data.iloc[-2]['High'], d_data.iloc[-2]['Low'], d_data.iloc[-2]['Close'])
        wp = woodie(w_data.iloc[-2]['High'], w_data.iloc[-2]['Low'], w_data.iloc[-2]['Close'])

        # 2. Intraday Data (15m)
        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 3. Indicators
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        
        delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))

        sig = df.iloc[-2] # Pattern Candle
        curr = df.iloc[-1] # Confirmation Candle
        ts = str(df.index[-2])
        
        # 4. Strict Pattern Logic
        is_hammer = (sig['L_Shadow'] > sig['Body'] * 1.8) and (sig['U_Shadow'] < sig['Body'] * 0.6)
        is_star = (sig['U_Shadow'] > sig['Body'] * 1.8) and (sig['L_Shadow'] < sig['Body'] * 0.6)

        if not (is_hammer or is_star): return memory

        # Determine Probability Rank
        is_extreme = (sig['RSI'] < 25 or sig['RSI'] > 75)
        prob_str = "💎 HIGH PROB" if is_extreme else "⚖️ NORMAL"

        h_key, c_key = f"{symbol}_{ts}_h", f"{symbol}_{ts}_c"

        # --- HEADS-UP ---
        if h_key not in memory:
            trigger = sig['High'] if is_hammer else sig['Low']
            msg = (f"👀 *HEADS-UP: {symbol.split('.')[0]}*\n"
                   f"Rank: {prob_str} | Pattern: {'🔨 Hammer' if is_hammer else '☄️ Star'}\n"
                   f"---------------------------\n"
                   f"📢 *Watch break:* {trigger:.2f}\n"
                   f"🕒 Time: {ts[-8:]}")
            send_alert(msg); memory[h_key] = True

        # --- CONFIRMATION ---
        if c_key not in memory:
            confirmed = (is_hammer and curr['High'] > sig['High']) or (is_star and curr['Low'] < sig['Low'])
            if confirmed:
                entry = curr['Open']
                sl = sig['Low'] if is_hammer else sig['High']
                risk = abs(entry - sl)
                
                # Dynamic Target Selection
                t1, t2 = dp['PP'], wp['PP']
                if is_hammer and entry > dp['PP']: t1, t2 = dp['R1'], dp['R2']
                if is_star and entry < dp['PP']: t1, t2 = dp['S1'], dp['S2']

                pts1, pts2 = abs(t1 - entry), abs(t2 - entry)
                rr1, rr2 = pts1/risk if risk > 0 else 0, pts2/risk if risk > 0 else 0

                msg = (f"✅ *ENTRY CONFIRMED: {symbol.split('.')[0]}*\n"
                       f"Rank: {prob_str}\n"
                       f"---------------------------\n"
                       f"🚀 *Entry:* {entry:.2f} | *SL:* {sl:.2f}\n"
                       f"🛡️ *Risk:* {risk:.2f} pts\n\n"
                       f"🎯 *T1:* {t1:.2f} (+{pts1:.2f} pts)\n"
                       f"📊 *R:R 1:* {rr1:.2f}\n\n"
                       f"🎯 *T2:* {t2:.2f} (+{pts2:.2f} pts)\n"
                       f"📊 *R:R 2:* {rr2:.2f}\n\n"
                       f"🎯 *T3:* Hold for EMA Cross")
                send_alert(msg); memory[c_key] = True

    except Exception: pass
    return memory

if __name__ == "__main__":
    current_mem = load_memory()
    for s in FNO_SYMBOLS: current_mem = get_signal(s, current_mem)
    save_memory(current_mem)

