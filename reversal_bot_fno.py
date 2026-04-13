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

# Comprehensive April 2026 F&O Universe
SYMBOLS = [
    "^NSEI", "^NSEBANK", "ADANIENT.NS", "ADANIPORTS.NS", "ADANIPOWER.NS", "ABB.NS", "ABCAPITAL.NS", "ABFRL.NS", 
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
        nifty = yf.download("^NSEI", period="5d", interval="1h", progress=False, multi_level_index=False)
        nifty.columns = [str(c).capitalize() for c in nifty.columns]
        ema9 = nifty['Close'].ewm(span=9).mean().iloc[-1]
        return "🟢 BULLISH" if nifty['Close'].iloc[-1] > ema9 else "🔴 BEARISH"
    except: return "⚪ NEUTRAL"

def calculate_indicators(df):
    n = 14
    df = df.copy()
    # Shadow/Body for Patterns
    df['Body'] = (df['Open'] - df['Close']).abs()
    df['L_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['U_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    # ADX/DI for V-Flip
    df['up'] = df['High'] - df['High'].shift(1)
    df['dn'] = df['Low'].shift(1) - df['Low']
    df['+dm'] = np.where((df['up'] > df['dn']) & (df['up'] > 0), df['up'], 0)
    df['-dm'] = np.where((df['dn'] > df['up']) & (df['dn'] > 0), df['dn'], 0)
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(n).mean()
    df['+DI'] = 100 * (df['+dm'].rolling(n).mean() / (atr + 1e-9))
    df['-DI'] = 100 * (df['-dm'].rolling(n).mean() / (atr + 1e-9))
    # Fib & Volume
    df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    rh, rl = df['High'].rolling(40).max(), df['Low'].rolling(40).min()
    df['Fib_618'] = rh - (0.618 * (rh - rl))
    return df

def get_signal(symbol, memory, mood):
    try:
        df_1h = yf.download(symbol, period="1mo", interval="1h", progress=False, multi_level_index=False)
        df_15m = yf.download(symbol, period="5d", interval="15m", progress=False, multi_level_index=False)
        if df_1h.empty or df_15m.empty: return memory
        for d in [df_1h, df_15m]: d.columns = [str(c).capitalize() for c in d.columns]

        df_1h = calculate_indicators(df_1h)
        sig, curr = df_1h.iloc[-2], df_1h.iloc[-1]
        
        # 15M Momentum Check
        ema9_15m = df_15m['Close'].ewm(span=9).mean()
        m_arrow = "📈" if ema9_15m.iloc[-1] > ema9_15m.iloc[-2] else "📉"
        is_15m_bullish = df_15m['Close'].iloc[-1] > ema9_15m.iloc[-1]

        # Pattern Logic
        is_hammer = (sig['L_Shadow'] > sig['Body'] * 1.5) and (sig['U_Shadow'] < sig['Body'] * 0.7)
        is_v_flip = (df_1h['-DI'].iloc[-3:-1].mean() > 25) and (curr['Close'] > sig['High'])
        is_fibo = abs(curr['Low'] - sig['Fib_618']) / sig['Fib_618'] < 0.006

        # --- STEP 1: HEADS-UP (Mid-Candle) ---
        if symbol not in memory and (is_hammer or (sig['-DI'] > 25)):
            pattern = "🔨 HAMMER" if is_hammer else "🔄 POTENTIAL V-FLIP"
            msg = (f"👀 **HEADS-UP: {symbol.replace('.NS','')}**\n"
                   f"Pattern: {pattern}\n"
                   f"Context: {'📐 Fibonacci' if is_fibo else '🧱 Support'}\n"
                   f"📢 Watch for break of: {sig['High']:.2f}")
            requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown")
            memory[symbol] = {"trigger": float(sig['High']), "sl": float(sig['Low']), "type": pattern, "active": False}

        # --- STEP 2: CONFIRMATION (Price Break + 15M Trend) ---
        elif symbol in memory and not memory[symbol]["active"]:
            if curr['Close'] > memory[symbol]["trigger"] and is_15m_bullish:
                # Scoring
                score = 30 if is_fibo else 10
                score += 40 if curr['Vol_Ratio'] > 1.8 else 10
                score += 30 if mood == "🟢 BULLISH" else 10
                rank = "💎 ELITE" if score >= 80 else "🥇 HIGH" if score >= 60 else "🥈 MED"

                risk = max(memory[symbol]["trigger"] - memory[symbol]["sl"], curr['Close'] * 0.005)
                t1, t2 = curr['Close'] + (risk * 2.5), curr['Close'] + (risk * 4.5)
                
                alert = (f"Market: {mood}\n✅ **CONFIRMED: {symbol.replace('.NS','')}**\n"
                         f"Rank: {rank} ({score}/100)\n"
                         f"---------------------------\n"
                         f"🟢 **ENTRY:** {curr['Close']:.2f} {m_arrow}\n"
                         f"🔴 **SL:** {memory[symbol]['sl']:.2f}\n"
                         f"🎯 **T1:** {t1:.2f} | 🚀 **T2:** {t2:.2f}")
                requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={alert}&parse_mode=Markdown")
                memory[symbol]["active"] = True

    except Exception: pass
    return memory

if __name__ == "__main__":
    mood = get_market_mood()
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f: mem = json.load(f)
    else: mem = {}
    for s in [s for s in SYMBOLS if s != "^NSEI"]: mem = get_signal(s, mem, mood)
    with open(MEMORY_FILE, 'w') as f: json.dump(mem, f, indent=4)
