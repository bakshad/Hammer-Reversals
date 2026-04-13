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
ML_LOG = "ml_training_data.csv"

# Updated April 2026 F&O Universe (Indices + ~200 Stocks)
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", 
    # New April 2026 Entrants
    "ADANIPOWER.NS", "COCHINSHIP.NS", "FORCEMOT.NS", "GODFRYPHLP.NS", 
    "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", "VMM.NS", "SWIGGY.NS",
    # Core F&O List
    "AARTIIND.NS", "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", 
    "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ALKEM.NS", "AMBUJACEM.NS", 
    "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", 
    "ATUL.NS", "AUBANK.NS", "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", 
    "BAJAJFINSV.NS", "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", 
    "BANKBARODA.NS", "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", 
    "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", "BPCL.NS", "BRITANNIA.NS", "BSOFT.NS", 
    "CANBK.NS", "CANFINHOME.NS", "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS", 
    "COALINDIA.NS", "COFORGE.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", 
    "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS", 
    "DELHIVERY.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", 
    "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS", "GLENMARK.NS", 
    "GMRAIRPORT.NS", "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", 
    "GRASIM.NS", "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFCBANK.NS", 
    "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS", 
    "HINDUNILVR.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFC.NS", 
    "IDFCFIRSTB.NS", "IEX.NS", "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", 
    "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IPCALAB.NS", 
    "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", 
    "KOTAKBANK.NS", "L&TFH.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LTIM.NS", "LT.NS", 
    "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", 
    "MCDOWELL-N.NS", "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MPHASIS.NS", 
    "MRF.NS", "MUTHOOTFIN.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", 
    "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", "ONGC.NS", "PAGEIND.NS", "PEL.NS", 
    "PERSISTENT.NS", "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS", 
    "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", "RECLTD.NS", 
    "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS", 
    "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", "SUNTV.NS", "SYNGENE.NS", 
    "TATACOMM.NS", "TATACONSUM.NS", "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", 
    "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", 
    "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", "UPL.NS", "VEDL.NS", "VOLTAS.NS", 
    "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
]

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

def get_signal(symbol, memory):
    try:
        df = yf.download(symbol, period="15d", interval="15m", progress=False)
        pivots = calculate_woodie_pivots(symbol)
        if df.empty or not pivots: return memory
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        
        lookback = df.iloc[-5:-1] 
        sig, curr = df.iloc[-2], df.iloc[-1]
        ts = str(df.index[-2])
        
        # 1. Price Action Base (Hammer/Star in last 4 candles)
        has_hammer_base = any([is_hammer_star(lookback.iloc[i])[0] for i in range(len(lookback))])
        has_star_base = any([is_hammer_star(lookback.iloc[i])[1] for i in range(len(lookback))])

        # 2. V-Flip Structure
        prior_swing_high, prior_swing_low = lookback['High'].max(), lookback['Low'].min()
        is_bull_vflip = (lookback['Low'].iloc[-1] < lookback['Low'].iloc[0]) and (curr['Close'] > prior_swing_high) and has_hammer_base
        is_bear_vflip = (lookback['High'].iloc[-1] > lookback['High'].iloc[0]) and (curr['Close'] < prior_swing_low) and has_star_base

        if (is_bull_vflip or is_bear_vflip) and f"{symbol}_{ts}" not in memory:
            # Pivot Confluence
            near_s1 = abs(lookback['Low'].min() - pivots['S1']) / pivots['S1'] < 0.0015
            near_r1 = abs(lookback['High'].max() - pivots['R1']) / pivots['R1'] < 0.0015
            
            quality = "💎 ELITE (Pivot + PA)" if (near_s1 or near_r1) else "🚀 HIGH (V-PA Confirmed)"
            side = "🟢 BUY" if is_bull_vflip else "🔴 SELL"
            
            # ML Logging
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
            
            requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown")
            memory[f"{symbol}_{ts}"] = True

    except Exception: pass
    return memory

if __name__ == "__main__":
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f: mem = json.load(f)
    else: mem = {}
    for s in SYMBOLS: mem = get_signal(s, mem)
    with open(MEMORY_FILE, 'w') as f: json.dump(mem, f, indent=4)
 
