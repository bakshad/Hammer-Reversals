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
WEEKLY_LOG = "weekly_trade_summary.csv"

# Updated April 2026 F&O Universe (Indices + ~200 Stocks)
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", 
    # New April 2026 Entrants
    "ADANIPOWER.NS", "COCHINSHIP.NS", "FORCEMOT.NS", "GODFRYPHLP.NS", 
    "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", "VMM.NS",
    # Major F&O Stocks
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
    "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS", "SWIGGY.NS"
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
        # Increase period to ensure indicators have enough warm-up data
        df = yf.download(symbol, period="15d", interval="15m", progress=False)
        if df.empty: return memory
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 1. Indicators
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        
        sig, curr, ts = df.iloc[-2], df.iloc[-1], str(df.index[-2])
        
        # 2. Pattern Logic
        l_ratio = sig['L_Shadow'] / (sig['Body'] + 1e-9)
        u_ratio = sig['U_Shadow'] / (sig['Body'] + 1e-9)
        
        is_hammer = (l_ratio > 1.3) and (u_ratio < 0.8)
        is_bull_vflip = (sig['Close'] < sig['Open']) and (curr['Close'] > sig['High'])
        is_star = (u_ratio > 1.3) and (l_ratio < 0.8)
        is_bear_vflip = (sig['Close'] > sig['Open']) and (curr['Close'] < sig['Low'])

        if not (is_hammer or is_star or is_bull_vflip or is_bear_vflip): return memory

        # 3. Ride Strategy (Trend Aligned?)
        is_long = is_hammer or is_bull_vflip
        is_aligned = (curr['Close'] > sig['EMA50']) if is_long else (curr['Close'] < sig['EMA50'])
        conviction = "🚀 TREND RIDER" if is_aligned else "🔄 REVERSAL"

        c_key = f"{symbol}_{ts}_confirmed"

        if c_key not in memory:
            confirmed = (is_long and curr['Close'] > sig['High']) or (not is_long and curr['Close'] < sig['Low'])
            
            if confirmed:
                side = "🟢 BUY" if is_long else "🔴 SELL"
                pattern = "Hammer/V-Flip" if is_long else "Star/V-Flip"
                
                msg = (f"🎯 **{side} CONFIRMED: {symbol.replace('.NS', '')}**\n"
                       f"Mode: {conviction}\n"
                       f"Pattern: {pattern}\n"
                       f"---------------------------\n"
                       f"💰 **Entry:** {curr['Close']:.2f}\n"
                       f"🛡️ **Initial SL:** {sig['Low'] if is_long else sig['High']:.2f}\n"
                       f"📈 **Trail SL (EMA9):** {curr['EMA9']:.2f}\n\n"
                       f"⚡ *Plan:* Ride the trend! Exit only when price closes back across EMA9.")
                
                send_alert(msg)
                memory[c_key] = True

    except Exception: pass
    return memory

if __name__ == "__main__":
    current_mem = load_memory()
    for s in SYMBOLS:
        current_mem = get_signal(s, current_mem)
    save_memory(current_mem)
