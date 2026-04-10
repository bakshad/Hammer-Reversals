import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import csv
from datetime import datetime, timedelta

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_memory_fno_15m.json"
ML_LOG = "ml_training_data.csv"

# April 2026 F&O Universe (Indices + 185+ Stocks)
SYMBOLS = [
    "^NSEI", "^NSEBANK", "ADANIPOWER.NS", "COCHINSHIP.NS", "HYUNDAI.NS", 
    "MOTILALOFS.NS", "NAM-INDIA.NS", "VMM.NS", "GODFRYPHLP.NS", "RELIANCE.NS", 
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "INFY.NS", "TCS.NS", "TATAMOTORS.NS", 
    "AXISBANK.NS", "BHARTIARTL.NS", "BAJFINANCE.NS", "LT.NS", "MARUTI.NS", 
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "ADANIENT.NS", "ZOMATO.NS", 
    "HAL.NS", "BEL.NS", "TRENT.NS", "JSWSTEEL.NS", "ITC.NS", "ASHOKLEY.NS", 
    "EICHERMOT.NS", "ASIANPAINT.NS", "COALINDIA.NS", "ONGC.NS", "ABB.NS",
    "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIPORTS.NS", "ALKEM.NS", "AMBUJACEM.NS",
    "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "AUBANK.NS", "AUROPHARMA.NS",
    "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS",
    "BANKBARODA.NS", "BATAINDIA.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHEL.NS",
    "BIOCON.NS", "BPCL.NS", "BRITANNIA.NS", "BSOFT.NS", "CANBK.NS", "CANFINHOME.NS",
    "CHOLAFIN.NS", "CIPLA.NS", "COFORGE.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS",
    "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS",
    "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "ESCORTS.NS", "EXIDEIND.NS",
    "FEDERALBNK.NS", "GAIL.NS", "GLENMARK.NS", "GMRAIRPORT.NS", "GODREJCP.NS",
    "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", "GUJGASLTD.NS", "HAVELLS.NS",
    "HCLTECH.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS",
    "HINDPETRO.NS", "HINDUNILVR.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS",
    "IEX.NS", "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS",
    "INDUSINDBK.NS", "INDUSTOWER.NS", "IPCALAB.NS", "IRCTC.NS", "JINDALSTEL.NS",
    "JKCEMENT.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "L&TFH.NS", "LALPATHLAB.NS",
    "LICHSGFIN.NS", "LTIM.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS",
    "MARICO.NS", "MCDOWELL-N.NS", "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS",
    "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NATIONALUM.NS", "NAVINFLUOR.NS",
    "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", "PAGEIND.NS", "PEL.NS",
    "PERSISTENT.NS", "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS",
    "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", "RECLTD.NS", "SAIL.NS",
    "SBICARD.NS", "SBILIFE.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS",
    "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAELXSI.NS",
    "TATAPOWER.NS", "TATASTEEL.NS", "TECHM.NS", "TORNTPHARM.NS", "TVSMOTOR.NS",
    "UBL.NS", "UPL.NS", "VEDL.NS", "VOLTAS.NS", "WIPRO.NS", "ZYDUSLIFE.NS"
]

def calculate_adx(df, n=14):
    df = df.copy()
    df['up'] = df['High'] - df['High'].shift(1)
    df['dn'] = df['Low'].shift(1) - df['Low']
    df['+dm'] = np.where((df['up'] > df['dn']) & (df['up'] > 0), df['up'], 0)
    df['-dm'] = np.where((df['dn'] > df['up']) & (df['dn'] > 0), df['dn'], 0)
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(n).mean()
    plus_di = 100 * (df['+dm'].rolling(n).mean() / atr)
    minus_di = 100 * (df['-dm'].rolling(n).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(n).mean(), plus_di, minus_di

def get_signal(symbol, memory):
    try:
        df = yf.download(symbol, period="5d", interval="15m", progress=False, multi_level_index=False)
        if df.empty: return memory
        df.columns = [c.capitalize() for c in df.columns]

        # Indicators
        df['ADX'], df['+DI'], df['-DI'] = calculate_adx(df)
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        
        # Woodie Pivots
        d_df = yf.download(symbol, period="2d", interval="1d", progress=False, multi_level_index=False)
        h, l, c = d_df.iloc[-1]['High'], d_df.iloc[-1]['Low'], d_df.iloc[-1]['Close']
        pp = (h + l + 2*c)/4

        sig = df.iloc[-2]  # Pattern Candle
        curr = df.iloc[-1] # Confirmation Candle
        adx_val = df['ADX'].iloc[-1]
        trend_arrow = "🔼" if adx_val > df['ADX'].iloc[-2] else "🔽"

        # --- CORE A: HAMMER (Reversal) ---
        is_hammer = (sig['L_Shadow'] > sig['Body'] * 1.5) and (sig['U_Shadow'] < sig['Body'] * 0.6)
        
        # --- CORE B: TREND-FLIP (Ashok Leyland) ---
        was_falling = df['-DI'].iloc[-2] > df['+DI'].iloc[-2]
        is_v_reversal = was_falling and (curr['Close'] > sig['High']) and (sig['Low'] < pp * 1.003)

        if symbol not in memory:
            msg = ""
            if is_hammer:
                msg = f"🔨 *HAMMER: {symbol.replace('.NS','')}*\nStr: {adx_val:.1f} {trend_arrow}\n📍 *Level:* Pivot Zone"
            elif is_v_reversal:
                msg = f"🔄 *TREND FLIP: {symbol.replace('.NS','')}*\n📉 Exhaustion {trend_arrow}\n🚀 *Flip:* {curr['Close']:.2f} > {sig['High']:.2f}"

            if msg:
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown", timeout=10)
                memory[symbol] = {"time": datetime.now().isoformat()}

    except Exception: pass
    return memory

if __name__ == "__main__":
    if not all([TOKEN, CHAT_ID]): exit("Missing Secrets")
    
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f: mem = json.load(f)
    else: mem = {}

    for s in SYMBOLS: mem = get_signal(s, mem)

    with open(MEMORY_FILE, 'w') as f: json.dump(mem, f, indent=4)
