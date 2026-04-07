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

# Full 182 F&O Stock List (Updated for April 2026)
FNO_SYMBOLS = [
    "ADANIPOWER.NS", "COCHINSHIP.NS", "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", "VISHALMEGA.NS",
    "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS",
    "AUBANK.NS", "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS",
    "BEL.NS", "BHARTIARTL.NS", "BPCL.NS", "BRITANNIA.NS", "CANBK.NS", "CHOLAFIN.NS", "CIPLA.NS",
    "COALINDIA.NS", "COFORGE.NS", "CONCOR.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "HAL.NS",
    "HCLTECH.NS", "HDFCBANK.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "INFY.NS", "IOC.NS",
    "ITC.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS", "LTIM.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS",
    "ONGC.NS", "PFC.NS", "RELIANCE.NS", "SBIN.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "TCS.NS", "TECHM.NS", "TITAN.NS", "TRENT.NS", "WIPRO.NS", "ZOMATO.NS"
] # Note: Reduced for readability; use the full list in your final file.

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
        data = yf.download(symbol, period="5d", interval="15m", progress=False)
        if data.empty or len(data) < 20: return memory
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Logic Calculations
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['Min_OC'] = df[['Open', 'Close']].min(axis=1)
        df['Max_OC'] = df[['Open', 'Close']].max(axis=1)
        df['Lower_Shadow'] = df['Min_OC'] - df['Low']
        df['Upper_Shadow'] = df['High'] - df['Max_OC']
        
        # RVOL Calculation (Current Volume vs 10-period Avg)
        df['Vol_SMA10'] = df['Volume'].rolling(window=10).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))

        sig_candle = df.iloc[-2] # Confirmed Candle
        conf_candle = df.iloc[-1] # Current Trigger Candle
        sig_ts = str(df.index[-2])
        
        rsi_val = sig_candle['RSI']
        rvol = sig_candle['Volume'] / sig_candle['Vol_SMA10'] if sig_candle['Vol_SMA10'] > 0 else 1
        
        # Pattern Flags
        is_hammer = (sig_candle['Lower_Shadow'] > sig_candle['Body'] * 1.5) and (sig_candle['Upper_Shadow'] < sig_candle['Body'] * 0.8)
        is_star = (sig_candle['Upper_Shadow'] > sig_candle['Body'] * 1.5) and (sig_candle['Lower_Shadow'] < sig_candle['Body'] * 0.8)

        # Status Meta
        quality = "💎 HIGH CONVICTION" if (rsi_val < 35 or rsi_val > 65) else "⚖️ BALANCED"
        vol_status = "🔥 HIGH VOL (RVOL: {:.1f}x)".format(rvol) if rvol > 1.5 else "⚪ Normal Vol"

        headsup_key = f"{symbol}_{sig_ts}_heads"
        confirm_key = f"{symbol}_{sig_ts}_conf"
        tsl_key = f"{symbol}_{sig_ts}_tsl"

        # 1. HEADS-UP
        if (is_hammer or is_star) and memory.get(headsup_key) is None:
            trigger = sig_candle['High'] if is_hammer else sig_candle['Low']
            msg = (f"👀 *HEADS-UP: {symbol.split('.')[0]}*\n"
                   f"Pattern: {'🔨 HAMMER' if is_hammer else '☄️ STAR'}\n"
                   f"Quality: {quality}\n"
                   f"Volume: {vol_status}\n"
                   f"---------------------------\n"
                   f"📢 *Watch for break of:* {trigger:.2f}")
            send_alert(msg)
            memory[headsup_key] = True

        # 2. CONFIRMATION & TRAILING STOP
        if is_hammer and (conf_candle['High'] > sig_candle['High']):
            if memory.get(confirm_key) is None:
                risk = sig_candle['High'] - sig_candle['Low']
                msg = (f"✅ *BUY CONFIRMED: {symbol.split('.')[0]}*\n"
                       f"🚀 *Entry:* {sig_candle['High']:.2f}\n"
                       f"🛑 *Stop Loss:* {sig_candle['Low']:.2f}\n"
                       f"🎯 *T1 (1.5R):* {sig_candle['High'] + risk*1.5:.2f}\n"
                       f"🎯 *T2 (2.5R):* {sig_candle['High'] + risk*2.5:.2f}")
                send_alert(msg)
                memory[confirm_key] = True

            # 3. TRAILING STOP LOSS ALERT (Triggered if price hits T1)
            elif memory.get(tsl_key) is None and conf_candle['Close'] > (sig_candle['High'] + (sig_candle['High'] - sig_candle['Low']) * 1.5):
                msg = (f"🛡️ *TSL ALERT: {symbol.split('.')[0]}*\n"
                       f"Target 1 Hit! Move Stop Loss to Entry: *{sig_candle['High']:.2f}*")
                send_alert(msg)
                memory[tsl_key] = True

        elif is_star and (conf_candle['Low'] < sig_candle['Low']):
            if memory.get(confirm_key) is None:
                risk = sig_candle['High'] - sig_candle['Low']
                msg = (f"✅ *SELL CONFIRMED: {symbol.split('.')[0]}*\n"
                       f"🔻 *Entry:* {sig_candle['Low']:.2f}\n"
                       f"🛑 *Stop Loss:* {sig_candle['High']:.2f}\n"
                       f"🎯 *T1 (1.5R):* {sig_candle['Low'] - risk*1.5:.2f}\n"
                       f"🎯 *T2 (2.5R):* {sig_candle['Low'] - risk*2.5:.2f}")
                send_alert(msg)
                memory[confirm_key] = True

            # 3. TRAILING STOP LOSS ALERT (Sell Side)
            elif memory.get(tsl_key) is None and conf_candle['Close'] < (sig_candle['Low'] - (sig_candle['High'] - sig_candle['Low']) * 1.5):
                msg = (f"🛡️ *TSL ALERT: {symbol.split('.')[0]}*\n"
                       f"Target 1 Hit! Move Stop Loss to Entry: *{sig_candle['Low']:.2f}*")
                send_alert(msg)
                memory[tsl_key] = True

    except Exception: pass
    return memory

if __name__ == "__main__":
    mem = load_memory()
    for s in FNO_SYMBOLS:
        mem = get_signal(s, mem)
    save_memory(mem)
