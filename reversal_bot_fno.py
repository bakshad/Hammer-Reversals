import yfinance as yf
import pandas as pd
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_memory_fno_15m.json"

# Cleaned FNO List
FNO_SYMBOLS = [
    "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ADANIPOWER.NS", 
    "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", 
    "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", 
    "BANKBARODA.NS", "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", "BPCL.NS", "BRITANNIA.NS", 
    "BSOFT.NS", "CANBK.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COCHINSHIP.NS", "COFORGE.NS", "CUMMINSIND.NS", "DIVISLAB.NS", 
    "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "FEDERALBNK.NS", "HAL.NS", "HCLTECH.NS", "HDFCBANK.NS", "HEROMOTOCO.NS", 
    "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "IDFCFIRSTB.NS", "INFY.NS", "IOC.NS", "IRCTC.NS", "ITC.NS", "JSWSTEEL.NS", 
    "KOTAKBANK.NS", "LTIM.NS", "LT.NS", "LUPIN.NS", "M&M.NS", "MARUTI.NS", "MCX.NS", "MUTHOOTFIN.NS", "NTPC.NS", "ONGC.NS", "PFC.NS", 
    "RELIANCE.NS", "SBIN.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", "TRENT.NS", "WIPRO.NS", "ZOMATO.NS"
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

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try: requests.get(url, timeout=10)
    except: pass

def get_signal(symbol, memory):
    try:
        # Fetching data and flattening the Multi-Index columns
        data = yf.download(symbol, period="3d", interval="15m", progress=False)
        if data.empty or len(data) < 20: return memory
        
        # This fix handles the yfinance Multi-Index issue
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Check second-to-last candle
        last_ts = str(df.index[-2])
        if memory.get(symbol) == last_ts: return memory

        # Logic Calculations
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['Min_OC'] = df[['Open', 'Close']].min(axis=1)
        df['Max_OC'] = df[['Open', 'Close']].max(axis=1)
        df['Lower_Shadow'] = df['Min_OC'] - df['Low']
        df['Upper_Shadow'] = df['High'] - df['Max_OC']
        df['Vol_SMA10'] = df['Volume'].rolling(window=10).mean()
        df['SMA20'] = df['Close'].rolling(window=20).mean()

        # RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))

        row = df.iloc[-2]
        vol_ok = row['Volume'] > (row['Vol_SMA10'] * 0.85)
        rsi_val = row['RSI']
        body = row['Body']
        
        # Reversal Logic
        is_hammer = (row['Lower_Shadow'] > body * 1.5) and (row['Upper_Shadow'] < body * 0.8) and (rsi_val < 50) and (row['Close'] < row['SMA20']) and vol_ok
        is_star = (row['Upper_Shadow'] > body * 1.5) and (row['Lower_Shadow'] < body * 0.8) and (rsi_val > 50) and (row['Close'] > row['SMA20']) and vol_ok

        if is_hammer or is_star:
            direction = "🚀 15M HAMMER (BUY)" if is_hammer else "🔻 15M STAR (SELL)"
            entry = (row['High'] * 1.0005) if is_hammer else (row['Low'] * 0.9995)
            sl = row['Low'] if is_hammer else row['High']
            target = (entry + abs(entry-sl)*2) if is_hammer else (entry - abs(entry-sl)*2)

            msg = (f"🎯 *{direction}*\nStock: `{symbol.split('.')[0]}`\n"
                   f"RSI: {rsi_val:.2f} | Time: {last_ts}\n"
                   f"---------------------------\n"
                   f"🟢 Entry: {entry:.2f} | 🛑 SL: {sl:.2f}\n"
                   f"🎯 Target: {target:.2f} | Pts: {abs(target-entry):.2f}")
            send_alert(msg)
            memory[symbol] = last_ts
    except Exception as e:
        print(f"Error on {symbol}: {e}")
    return memory

if __name__ == "__main__":
    print(f"--- Starting Scan at {datetime.now()} ---")
    mem = load_memory()
    # Scans a targeted FNO list to stay within GitHub Action limits
    for s in FNO_SYMBOLS:
        mem = get_signal(s, mem)
    save_memory(mem)
    print("--- Scan Complete ---")
