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
MEMORY_FILE = "alert_memory_fno_15m.json"
WEEKLY_LOG = "weekly_trade_summary.csv"

# Updated April 2026 F&O List (Indices + 180+ Stocks)
SYMBOLS = [
    "^NSEI", "^NSEBANK",  # Indices
    "ADANIPOWER.NS", "COCHINSHIP.NS", "HYUNDAI.NS", "MOTILALOFS.NS", 
    "NAM-INDIA.NS", "VMM.NS", "FORCEMOT.NS", "GODFRYPHLP.NS", # New April 2026 Inclusions
    "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS",
    "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS",
    "BAJAJFINSV.NS", "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS",
    "BANKBARODA.NS", "BATAINDIA.NS", "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS",
    "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", "BPCL.NS", "BRITANNIA.NS", "BSOFT.NS", "CANBK.NS",
    "CANFINHOME.NS", "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COFORGE.NS",
    "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS",
    "DALBHARAT.NS", "DEEPAKNTR.NS", "DELHIVERY.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS",
    "DRREDDY.NS", "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS",
    "GLENMARK.NS", "GMRAIRPORT.NS", "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS",
    "GRASIM.NS", "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFCBANK.NS",
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS",
    "HINDUNILVR.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFC.NS", "IDFCFIRSTB.NS",
    "IEX.NS", "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS",
    "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IPCALAB.NS", "IRCTC.NS",
    "ITC.NS", "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS",
    "L&TFH.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LTIM.NS", "LT.NS", "LUPIN.NS", "M&M.NS",
    "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MCDOWELL-N.NS", "MCX.NS",
    "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS",
    "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS",
    "ONGC.NS", "PAGEIND.NS", "PEL.NS", "PERSISTENT.NS", "PETRONET.NS", "PFC.NS",
    "PIDILITIND.NS", "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS",
    "RAMCOCEM.NS", "RECLTD.NS", "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS",
    "SBIN.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS",
    "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAELXSI.NS",
    "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS",
    "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", "UPL.NS",
    "VEDL.NS", "VOLTAS.NS", "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
]

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_memory(mem):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f, indent=4)

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try: requests.get(url, timeout=10)
    except: pass

def get_signal(symbol, memory):
    try:
        # 1. Fetch Data
        df = yf.download(symbol, period="3d", interval="15m", progress=False)
        if df.empty: return memory
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 2. Daily Pivots (Woodie)
        d_data = yf.download(symbol, period="2d", interval="1d", progress=False)
        h, l, c = d_data.iloc[-1]['High'], d_data.iloc[-1]['Low'], d_data.iloc[-1]['Close']
        pp = (h + l + 2*c)/4
        
        # 3. Indicator Math
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        df['Vol_Avg'] = df['Volume'].rolling(10).mean()
        
        sig = df.iloc[-1] # The latest closed 15m candle
        
        # --- PHASE 1: WATCHLIST CONFIRMATION ---
        if symbol in memory:
            watch = memory[symbol]
            # Timeout after 60 mins (4 candles)
            if (datetime.now() - datetime.fromisoformat(watch['time'])) < timedelta(minutes=60):
                # Bullish Breakout
                if watch['type'] == 'Hammer' and sig['High'] > watch['trigger']:
                    send_alert(f"✅ *ENTRY CONFIRMED: {symbol.replace('.NS','')}*\n🚀 *Entry:* {sig['High']:.2f} | *SL:* {watch['sl']:.2f}\n🎯 *T1 (PP):* {pp:.2f}")
                    del memory[symbol]
                    return memory
                # Bearish Breakdown
                elif watch['type'] == 'Star' and sig['Low'] < watch['trigger']:
                    send_alert(f"✅ *ENTRY CONFIRMED: {symbol.replace('.NS','')}*\n🚀 *Entry:* {sig['Low']:.2f} | *SL:* {watch['sl']:.2f}\n🎯 *T1 (PP):* {pp:.2f}")
                    del memory[symbol]
                    return memory
            else:
                del memory[symbol] # Expired

        # --- PHASE 2: NEW PATTERN SEARCH ---
        # Volume Filter: Only look at patterns with volume > 1.2x of average
        if sig['Volume'] > (sig['Vol_Avg'] * 1.2):
            l_ratio = sig['L_Shadow'] / sig['Body'] if sig['Body'] > 0 else 2.0
            u_ratio = sig['U_Shadow'] / sig['Body'] if sig['Body'] > 0 else 2.0
            
            is_hammer = (l_ratio > 1.8) and (u_ratio < 0.6)
            is_star = (u_ratio > 1.8) and (l_ratio < 0.6)

            if is_hammer:
                memory[symbol] = {"type": "Hammer", "trigger": float(sig['High']), "sl": float(sig['Low']), "time": datetime.now().isoformat()}
                send_alert(f"👀 *HEADS-UP: {symbol.replace('.NS','')}*\nPattern: 🔨 Hammer | Watch: {sig['High']:.2f}")
            elif is_star:
                memory[symbol] = {"type": "Star", "trigger": float(sig['Low']), "sl": float(sig['High']), "time": datetime.now().isoformat()}
                send_alert(f"👀 *HEADS-UP: {symbol.replace('.NS','')}*\nPattern: ☄️ Star | Watch: {sig['Low']:.2f}")

    except Exception: pass
    return memory

if __name__ == "__main__":
    mem = load_memory()
    for s in SYMBOLS: mem = get_signal(s, mem)
    save_memory(mem)
