import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import csv
import logging
from datetime import datetime
import concurrent.futures
from nsepython import nse_fno

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# --- CONFIGURATION ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status_st.json"
POSITIONS_FILE = "active_positions_st.json"
TRADE_LOG = "supertrend_trade_summary.csv" 

# --- FULL APRIL 2026 F&O UNIVERSE (190+ SYMBOLS) ---
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "MIDCPNIFTY.NS", "NIFTYNXT50.NS", "360ONE.NS", "AARTIIND.NS", "ABB.NS", 
    "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENSOL.NS", "ADANIENT.NS", "ADANIGREEN.NS", 
    "ADANIPORTS.NS", "ADANIPOWER.NS", "ALKEM.NS", "AMBER.NS", "AMBUJACEM.NS", "ANGELONE.NS", "APLAPOLLO.NS", 
    "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", 
    "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJAJHLDNG.NS", "BAJFINANCE.NS", 
    "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BANKINDIA.NS", "BDL.NS", "BEL.NS", 
    "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", "BPCL.NS", 
    "BRITANNIA.NS", "BSE.NS", "BSOFT.NS", "CANBK.NS", "CANFINHOME.NS", "CHAMBLFERT.NS", "CHOLAFIN.NS", 
    "CIPLA.NS", "COALINDIA.NS", "COCHINSHIP.NS", "COFORGE.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", 
    "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS", "DELHIVERY.NS", "DIVISLAB.NS", 
    "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", 
    "FORCEMOT.NS", "GAIL.NS", "GLENMARK.NS", "GMRAIRPORT.NS", "GNFC.NS", "GODFRYPHLP.NS", "GODREJCP.NS", 
    "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", 
    "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS", 
    "HINDUNILVR.NS", "HUDCO.NS", "HYUNDAI.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS", 
    "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", 
    "INFY.NS", "IOC.NS", "IPCALAB.NS", "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", "JIOFIN.NS", "JKCEMENT.NS", 
    "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LT.NS", "LTIM.NS", 
    "LTTS.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MAXHEALTH.NS", 
    "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MOTILALOFS.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", 
    "NAM-INDIA.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", 
    "OFSS.NS", "ONGC.NS", "PAGEIND.NS", "PAYTM.NS", "PEL.NS", "PERSISTENT.NS", "PETRONET.NS", "PFC.NS", 
    "PIDILITIND.NS", "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", 
    "RECLTD.NS", "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", 
    "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", "SUNTV.NS", "SWIGGY.NS", "SYNGENE.NS", "TATACOMM.NS", "TATACONSUM.NS", 
    "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", 
    "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", "UNITDSPR.NS", "UPL.NS", "V-GUARD.NS", 
    "VEDL.NS", "VMM.NS", "VOLTAS.NS", "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
]

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def safe_fetch(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def get_oi_data(symbol):
    try:
        nse_symbol = symbol.replace(".NS", "")
        data = nse_fno(nse_symbol)
        stocks_list = data.get('stocks', [])
        if not stocks_list: return 0.0
        trade_info = stocks_list[0].get('marketDeptOrderBook', {}).get('tradeInfo', {})
        curr_oi = float(trade_info.get('openInterest', 0))
        prev_oi = float(trade_info.get('prevCloseOI', 0))
        if prev_oi > 0:
            return round(((curr_oi - prev_oi) / prev_oi) * 100, 2)
        return 0.0
    except: return 0.0

def calculate_supertrend(df, length=7, multiplier=2.0):
    hl2 = (df['High'] + df['Low']) / 2
    df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(window=length).mean()
    df['Basic_UB'] = hl2 + (multiplier * df['ATR'])
    df['Basic_LB'] = hl2 - (multiplier * df['ATR'])
    df['Final_UB'], df['Final_LB'] = 0.0, 0.0
    for i in range(length, len(df)):
        df.loc[df.index[i], 'Final_UB'] = df['Basic_UB'].iloc[i] if df['Basic_UB'].iloc[i] < df['Final_UB'].iloc[i-1] or df['Close'].iloc[i-1] > df['Final_UB'].iloc[i-1] else df['Final_UB'].iloc[i-1]
        df.loc[df.index[i], 'Final_LB'] = df['Basic_LB'].iloc[i] if df['Basic_LB'].iloc[i] > df['Final_LB'].iloc[i-1] or df['Close'].iloc[i-1] < df['Final_LB'].iloc[i-1] else df['Final_LB'].iloc[i-1]
    df['Supertrend'] = 0.0
    for i in range(length, len(df)):
        if df['Supertrend'].iloc[i-1] == df['Final_UB'].iloc[i-1] and df['Close'].iloc[i] <= df['Final_UB'].iloc[i]:
            df.loc[df.index[i], 'Supertrend'] = df['Final_UB'].iloc[i]
        elif df['Supertrend'].iloc[i-1] == df['Final_UB'].iloc[i-1] and df['Close'].iloc[i] > df['Final_UB'].iloc[i]:
            df.loc[df.index[i], 'Supertrend'] = df['Final_LB'].iloc[i]
        elif df['Supertrend'].iloc[i-1] == df['Final_LB'].iloc[i-1] and df['Close'].iloc[i] >= df['Final_LB'].iloc[i]:
            df.loc[df.index[i], 'Supertrend'] = df['Final_LB'].iloc[i]
        else:
            df.loc[df.index[i], 'Supertrend'] = df['Final_UB'].iloc[i]
    return df['Supertrend']

def get_market_mood():
    df = safe_fetch("^NSEI", "1mo", "1h")
    if df is None: return "⚪ NEUTRAL"
    df['EMA9'] = df['Close'].ewm(span=9).mean()
    return "🟢 BULLISH" if df['Close'].iloc[-1] > df['EMA9'].iloc[-1] else "🔴 BEARISH"

def process_symbol(symbol, memory, positions, mood):
    if symbol in ["^NSEI", "^NSEBANK"]: return None
    df_15m = safe_fetch(symbol, "5d", "15m")
    if df_15m is None or len(df_15m) < 21: return None
    
    df_15m['EMA20'] = df_15m['Close'].ewm(span=20, adjust=False).mean()
    df_15m['Supertrend'] = calculate_supertrend(df_15m)
    
    curr, prev = df_15m.iloc[-1], df_15m.iloc[-2]
    ts = str(df_15m.index[-1])
    
    avg_vol = df_15m['Volume'].iloc[-20:-1].mean() + 1e-9
    vol_surge = curr['Volume'] / avg_vol
    oi_pct = get_oi_data(symbol)

    # 15m Chartink Translation
    is_long = (curr['Close'] > curr['EMA20']) and (curr['Close'] > curr['Supertrend']) and \
              (prev['Close'] <= prev['Supertrend']) and (curr['Volume'] > 100000) and (mood != "🔴 BEARISH")
              
    is_short = (curr['Close'] < curr['EMA20']) and (curr['Close'] < curr['Supertrend']) and \
               (prev['Close'] >= prev['Supertrend']) and (curr['Close'] < curr['Open']) and (mood != "🟢 BULLISH")

    if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
        rank = "💎 ELITE" if (vol_surge >= 1.5 and abs(oi_pct) >= 2.0) else "🥇 STANDARD"
        side = "🟢 BUY" if is_long else "🔴 SELL"
        risk = abs(curr['Close'] - curr['Supertrend'])
        t1 = curr['Close'] + (risk * 2) if is_long else curr['Close'] - (risk * 2)
        
        msg = (f"{rank} SUPERTREND BREAKOUT\n"
               f"---------------------------\n"
               f"📦 **Stock:** {symbol.replace('.NS','')}\n"
               f"🔥 **Action:** {side}\n"
               f"📊 **Vol Surge:** {vol_surge:.1f}x | **OI Change:** {oi_pct:+.2f}%\n"
               f"💰 **Entry:** {curr['Close']:.2f}\n"
               f"🎯 **Target 1:** {t1:.2f}\n"
               f"🛡️ **SL:** {curr['Supertrend']:.2f}")
        
        send_telegram(msg)
        return {"symbol_ts": f"{symbol}_{ts}", "symbol": symbol, "data": {"Entry": round(curr['Close'], 2), "Side": side, "T1": round(t1, 2), "t1_reached": False}}
    return None

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    mood = get_market_mood()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, mem, pos, mood): s for s in SYMBOLS}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                mem[res["symbol_ts"]] = True
                pos[res["symbol"]] = res["data"]
                
    save_json(mem, MEMORY_FILE)
    save_json(pos, POSITIONS_FILE)
