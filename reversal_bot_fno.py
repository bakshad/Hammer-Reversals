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
MEMORY_FILE = "alert_memory_fno_mtf.json"
ML_LOG = "ml_training_data.csv"

# Sector Mapping for Ranking
SECTOR_MAP = {
    "HDFCBANK.NS": "BANKING", "ICICIBANK.NS": "BANKING", "SBIN.NS": "BANKING", "AXISBANK.NS": "BANKING",
    "KOTAKBANK.NS": "BANKING", "PNB.NS": "BANKING", "CANBK.NS": "BANKING", "IDFCFIRSTB.NS": "BANKING",
    "BAJFINANCE.NS": "FIN_SERVICES", "CHOLAFIN.NS": "FIN_SERVICES", "RECLTD.NS": "FIN_SERVICES", 
    "PFC.NS": "FIN_SERVICES", "MARUTI.NS": "AUTO", "TATAMOTORS.NS": "AUTO", "M&M.NS": "AUTO", 
    "ASHOKLEY.NS": "AUTO", "HYUNDAI.NS": "AUTO", "BHARATFORG.NS": "AUTO", "TCS.NS": "IT", 
    "INFY.NS": "IT", "HCLTECH.NS": "IT", "WIPRO.NS": "IT", "RELIANCE.NS": "ENERGY", 
    "ONGC.NS": "ENERGY", "ADANIPOWER.NS": "ENERGY", "TATASTEEL.NS": "METAL", "JSWSTEEL.NS": "METAL",
    "SUNPHARMA.NS": "PHARMA", "CIPLA.NS": "PHARMA", "HAL.NS": "DEFENCE", "COCHINSHIP.NS": "DEFENCE"
}

SYMBOLS = [
    "ADANIENT.NS", "ADANIPORTS.NS", "ADANIPOWER.NS", "ABB.NS", "ABCAPITAL.NS", "ABFRL.NS", 
    "ACC.NS", "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", 
    "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", 
    "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BATAINDIA.NS", 
    "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", "BPCL.NS", "BRITANNIA.NS", 
    "BSOFT.NS", "CANBK.NS", "CANFINHOME.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COCHINSHIP.NS", 
    "COFORGE.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", 
    "DALBHARAT.NS", "DEEPAKNTR.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", 
    "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "FORCEMOT.NS", "GAIL.NS", "GLENMARK.NS", "GMRAIRPORT.NS", 
    "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", 
    "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS", 
    "HINDUNILVR.NS", "HYUNDAI.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS", "IEX.NS", 
    "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", 
    "INFY.NS", "IPCALAB.NS", "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", 
    "KOTAKBANK.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LT.NS", "LTIM.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", 
    "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MCDOWELL-N.NS", "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", 
    "MOTILALOFS.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NAM-INDIA.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", 
    "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", "ONGC.NS", "PAGEIND.NS", "PEL.NS", "PERSISTENT.NS", 
    "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", 
    "RAMCOCEM.NS", "RECLTD.NS", "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS", 
    "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS", 
    "TATACONSUM.NS", "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", 
    "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", "UPL.NS", "VEDL.NS", 
    "VOLTAS.NS", "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
]

def get_market_mood():
    try:
        nifty = yf.download("^NSEI", period="5d", interval="1h", progress=False)
        ema9 = nifty['Close'].ewm(span=9).mean().iloc[-1]
        return "🟢 BULLISH" if nifty['Close'].iloc[-1] > ema9 else "🔴 BEARISH"
    except: return "⚪ NEUTRAL"

def calculate_indicators(df):
    df = df.copy()
    df['Body'] = (df['Open'] - df['Close']).abs()
    df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    rh, rl = df['High'].rolling(40).max(), df['Low'].rolling(40).min()
    df['Fib_618'] = rh - (0.618 * (rh - rl))
    return df

def get_signal(symbol, memory, mood):
    try:
        df_1h = yf.download(symbol, period="1mo", interval="1h", progress=False)
        df_15m = yf.download(symbol, period="5d", interval="15m", progress=False)
        if df_1h.empty or df_15m.empty: return memory
        
        df_1h = calculate_indicators(df_1h)
        sig, curr = df_1h.iloc[-2], df_1h.iloc[-1]
        
        # MTF & Breakout Checks
        ema9_15m = df_15m['Close'].ewm(span=9).mean()
        is_15m_bullish = df_15m['Close'].iloc[-1] > ema9_15m.iloc[-1]
        m_arrow = "📈" if ema9_15m.iloc[-1] > ema9_15m.iloc[-2] else "📉"
        is_breakout = curr['Close'] > sig['High']

        # Pattern Check
        is_hammer = (sig['L_Shadow'] > sig['Body'] * 1.5)
        is_v_flip = (curr['Close'] > sig['High']) and (sig['Close'] < sig['Open'])
        is_fibo = abs(curr['Low'] - sig['Fib_618']) / sig['Fib_618'] < 0.006
        vol_ratio = curr['Volume'] / sig['Vol_Avg']

        # --- FINAL ENTRY ALERT GATE ---
        if symbol not in memory and is_breakout and is_15m_bullish and (is_hammer or is_v_flip):
            sector = SECTOR_MAP.get(symbol, "OTHERS")
            
            # Scoring
            score = 30 if is_fibo else 10
            score += 40 if vol_ratio > 1.8 else 15
            score += 30 if mood == "🟢 BULLISH" else 10
            rank = "💎 ELITE" if score >= 85 else "🥇 HIGH"

            risk = max(sig['High'] - sig['Low'], curr['Close'] * 0.005)
            t1, t2 = curr['Close'] + (risk * 2.5), curr['Close'] + (risk * 4.5)
            
            alert = (f"✅ **CONFIRMED ENTRY: {symbol.replace('.NS','')}**\n"
                     f"Market: {mood} | Sector: {sector}\n"
                     f"Rank: {rank} ({score}/100)\n"
                     f"---------------------------\n"
                     f"🟢 **ENTRY:** {curr['Close']:.2f} {m_arrow}\n"
                     f"🔴 **SL:** {sig['Low']:.2f}\n"
                     f"🎯 **T1:** {t1:.2f} | 🚀 **T2:** {t2:.2f}\n"
                     f"🔥 Vol Ratio: {vol_ratio:.2f}x")
            
            requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={alert}&parse_mode=Markdown")
            memory[symbol] = {"time": datetime.now().isoformat()}

    except Exception: pass
    return memory

if __name__ == "__main__":
    mood = get_market_mood()
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f: mem = json.load(f)
    else: mem = {}
    for s in SYMBOLS: mem = get_signal(s, mem, mood)
    with open(MEMORY_FILE, 'w') as f: json.dump(mem, f, indent=4)
