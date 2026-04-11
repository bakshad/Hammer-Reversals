import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_memory_fno_mtf.json"

# Full April 2026 F&O Universe (220+ Stocks)
SYMBOLS = [
    "^NSEI", "^NSEBANK", "ADANIPOWER.NS", "COCHINSHIP.NS", "HYUNDAI.NS", 
    "MOTILALOFS.NS", "NAM-INDIA.NS", "VMM.NS", "FORCEMOT.NS", "GODFRYPHLP.NS",
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "INFY.NS", "TCS.NS",
    "TATAMOTORS.NS", "AXISBANK.NS", "BHARTIARTL.NS", "BAJFINANCE.NS", "LT.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "ADANIENT.NS",
    "ZOMATO.NS", "HAL.NS", "BEL.NS", "TRENT.NS", "JSWSTEEL.NS", "ITC.NS",
    "ASHOKLEY.NS", "EICHERMOT.NS", "ASIANPAINT.NS", "COALINDIA.NS", "ONGC.NS",
    "ABB.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIPORTS.NS", "ALKEM.NS", 
    "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "AUBANK.NS", "AUROPHARMA.NS",
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

def calculate_indicators(df):
    # ADX and DI Calculation
    n = 14
    df = df.copy()
    df['up'] = df['High'] - df['High'].shift(1)
    df['dn'] = df['Low'].shift(1) - df['Low']
    df['+dm'] = np.where((df['up'] > df['dn']) & (df['up'] > 0), df['up'], 0)
    df['-dm'] = np.where((df['dn'] > df['up']) & (df['dn'] > 0), df['dn'], 0)
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(n).mean()
    df['ADX'] = (100 * (df['+dm'].rolling(n).mean() / (atr + 1e-9) - df['-dm'].rolling(n).mean() / (atr + 1e-9)).abs() / 
                (df['+dm'].rolling(n).mean() / (atr + 1e-9) + df['-dm'].rolling(n).mean() / (atr + 1e-9) + 1e-9)).rolling(n).mean()
    df['+DI'] = 100 * (df['+dm'].rolling(n).mean() / (atr + 1e-9))
    df['-DI'] = 100 * (df['-dm'].rolling(n).mean() / (atr + 1e-9))
    
    # Shadow Logic
    df['Body'] = (df['Open'] - df['Close']).abs()
    df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    return df

def get_signal(symbol, memory):
    try:
        # Multi-Timeframe Fetch
        df_1h = yf.download(symbol, period="1mo", interval="1h", progress=False, multi_level_index=False)
        df_15m = yf.download(symbol, period="5d", interval="15m", progress=False, multi_level_index=False)
        if df_1h.empty or df_15m.empty: return memory
        for d in [df_1h, df_15m]: d.columns = [str(c).capitalize() for c in d.columns]

        # 1H Metrics
        df_1h = calculate_indicators(df_1h)
        sig = df_1h.iloc[-2]  # Pattern
        curr = df_1h.iloc[-1] # Confirmation
        
        # 15M Filter (EMA9)
        df_15m['EMA9'] = df_15m['Close'].ewm(span=9, adjust=False).mean()
        is_15m_bullish = df_15m['Close'].iloc[-1] > df_15m['EMA9'].iloc[-1]

        # REVERSAL LOGIC
        # Loosened to 1.5x shadow for higher practicality
        is_hammer = (sig['L_Shadow'] > sig['Body'] * 1.5) and (sig['U_Shadow'] < sig['Body'] * 0.7)
        was_falling = df_1h['-DI'].iloc[-3:-1].mean() > 22
        is_v_flip = was_falling and (curr['Close'] > sig['High'])

        if symbol not in memory and is_15m_bullish:
            msg = ""
            risk = max(sig['High'] - sig['Low'], curr['Close'] * 0.005) # Min risk 0.5%
            t1, t2 = curr['Close'] + (risk * 2.0), curr['Close'] + (risk * 4.0)

            if is_hammer:
                quality = "💎 ELITE" if sig['L_Shadow'] > sig['Body'] * 2.2 else "⚖️ REGULAR"
                msg = f"🔨 *HOURLY HAMMER: {symbol.replace('.NS','')}*\nQuality: {quality}"
            elif is_v_flip:
                msg = f"🔄 *HOURLY TREND FLIP: {symbol.replace('.NS','')}*"

            if msg:
                alert = (f"{msg}\n✅ *MTF Filter:* 15M Bullish\n---------------------------\n"
                         f"🟢 **ENTRY:** {curr['Close']:.2f}\n"
                         f"🔴 **SL:** {sig['Low']:.2f}\n"
                         f"🎯 **T1 (2R):** {t1:.2f}\n"
                         f"🚀 **T2 (4R):** {t2:.2f}")
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={alert}&parse_mode=Markdown")
                memory[symbol] = {"time": datetime.now().isoformat()}

    except Exception: pass
    return memory

if __name__ == "__main__":
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f: mem = json.load(f)
    else: mem = {}
    for s in SYMBOLS: mem = get_signal(s, mem)
    with open(MEMORY_FILE, 'w') as f: json.dump(mem, f, indent=4)
