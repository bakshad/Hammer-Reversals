import yfinance as yf
import pandas as pd
import requests
import os
import json
import csv
from datetime import datetime, timedelta

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status.json"
WEEKLY_LOG = "weekly_trade_summary.csv"

# Indices & Full F&O List (Updated April 2026)
SYMBOLS = [
    "^NSEI", "^NSEBANK", # Nifty 50 and Bank Nifty
    "ADANIPOWER.NS", "COCHINSHIP.NS", "FORCEMOT.NS", "GODFRYPHLP.NS", 
    "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", "VMM.NS", # New Entrants
    "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS",
    "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS", "BEL.NS", "BHARTIARTL.NS",
    "BPCL.NS", "BRITANNIA.NS", "CANBK.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COFORGE.NS",
    "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "HAL.NS", "HCLTECH.NS", "HDFCBANK.NS", "HINDALCO.NS",
    "HINDUNILVR.NS", "ICICIBANK.NS", "INFY.NS", "IOC.NS", "ITC.NS", "JSWSTEEL.NS", "KOTAKBANK.NS",
    "LT.NS", "LTIM.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "ONGC.NS", "PFC.NS", "RELIANCE.NS",
    "SBIN.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS",
    "TRENT.NS", "WIPRO.NS", "ZOMATO.NS"
]

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=4)

def log_trade(data):
    file_exists = os.path.isfile(WEEKLY_LOG)
    with open(WEEKLY_LOG, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Symbol", "Type", "Entry", "Exit", "Pts", "Percent"])
        if not file_exists: writer.writeheader()
        writer.writerow(data)

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try: requests.get(url, timeout=10)
    except: pass

def get_signal(symbol, memory):
    try:
        # 1. Fetch Pivot Levels (Daily & Weekly)
        d_data = yf.download(symbol, period="5d", interval="1d", progress=False)
        w_data = yf.download(symbol, period="20d", interval="1wk", progress=False)
        if d_data.empty or w_data.empty: return memory

        def woodie(h, l, c):
            pp = (h + l + 2 * c) / 4
            return {"PP": pp, "R1": (2*pp)-l, "R2": pp+(h-l), "S1": (2*pp)-h, "S2": pp-(h-l)}

        dp = woodie(d_data.iloc[-2]['High'], d_data.iloc[-2]['Low'], d_data.iloc[-2]['Close'])
        wp = woodie(w_data.iloc[-2]['High'], w_data.iloc[-2]['Low'], w_data.iloc[-2]['Close'])

        # 2. Intraday Data (15m)
        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 3. Indicators & Trend
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        
        delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))

        sig, curr, ts = df.iloc[-2], df.iloc[-1], str(df.index[-2])
        
        # Pattern Logic (Hybrid)
        l_ratio = sig['L_Shadow'] / sig['Body'] if sig['Body'] > 0 else 2.0
        u_ratio = sig['U_Shadow'] / sig['Body'] if sig['Body'] > 0 else 2.0
        is_hammer = (l_ratio > 1.2) and (u_ratio < 0.9)
        is_star = (u_ratio > 1.2) and (l_ratio < 0.9)

        if not (is_hammer or is_star): return memory

        # Trend & Probability
        rvol = sig['Volume'] / (df['Volume'].rolling(10).mean().iloc[-2]) if df['Volume'].rolling(10).mean().iloc[-2] > 0 else 1
        quality = "💎 HIGH CONV" if (sig['RSI'] < 30 or sig['RSI'] > 70) else "⚖️ BALANCED"
        
        if is_hammer:
            trend_exp = "🔄 Bullish Reversal" if sig['EMA20'] < sig['EMA50'] else "🚀 Uptrend Continuation"
        else:
            trend_exp = "🔄 Bearish Reversal" if sig['EMA20'] > sig['EMA50'] else "🔻 Downtrend Continuation"

        h_key, c_key = f"{symbol}_{ts}_h", f"{symbol}_{ts}_c"

        # --- HEADS-UP ---
        if h_key not in memory:
            msg = (f"👀 *HEADS-UP: {symbol.replace('^', '')}*\n"
                   f"Pattern: {'🔨 Hammer' if is_hammer else '☄️ Star'}\n"
                   f"Quality: {quality} | Vol: {'🔥' if rvol > 1.5 else '⚪'}\n"
                   f"Trend: {trend_exp}\n"
                   f"---------------------------\n"
                   f"📢 *Watch break:* {sig['High'] if is_hammer else sig['Low']:.2f}")
            send_alert(msg); memory[h_key] = True

        # --- CONFIRMATION ---
        if c_key not in memory:
            confirmed = (is_hammer and curr['High'] > sig['High']) or (is_star and curr['Low'] < sig['Low'])
            if confirmed:
                entry, sl = curr['Open'], (sig['Low'] if is_hammer else sig['High'])
                t1, t2 = dp['PP'], wp['PP']
                if is_hammer and entry > dp['PP']: t1 = dp['R1']
                if is_star and entry < dp['PP']: t1 = dp['S1']
                
                risk = abs(entry - sl)
                pts = abs(t1 - entry)
                msg = (f"✅ *ENTRY CONFIRMED: {symbol.replace('^', '')}*\n"
                       f"🚀 *Entry:* {entry:.2f} | *SL:* {sl:.2f}\n"
                       f"🛡️ *Risk:* {risk:.2f} | *R:R T1:* {pts/risk:.2f}\n"
                       f"🎯 *T1 (Daily):* {t1:.2f} (+{pts:.2f})\n"
                       f"🎯 *T2 (Weekly):* {t2:.2f}")
                send_alert(msg); memory[c_key] = True
                
                # Log for Weekly Summary
                log_trade({"Date": ts[:10], "Symbol": symbol, "Type": "BUY" if is_hammer else "SELL", 
                           "Entry": entry, "Exit": t1, "Pts": pts, "Percent": (pts/entry)*100})

    except Exception: pass
    return memory

if __name__ == "__main__":
    current_mem = load_memory()
    for s in SYMBOLS: current_mem = get_signal(s, current_mem)
    save_memory(current_mem)
