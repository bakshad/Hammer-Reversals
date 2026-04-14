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
POSITIONS_FILE = "active_positions.json"
ML_LOG = "ml_training_data.csv"
TRADE_LOG = "weekly_trade_summary.csv"

# Updated April 2026 F&O Universe (~200 Symbols)
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", 
    "ADANIPOWER.NS", "COCHINSHIP.NS", "FORCEMOT.NS", "GODFRYPHLP.NS", 
    "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", "VMM.NS", "SWIGGY.NS",
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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try: requests.get(url, timeout=10)
    except: pass

def get_woodie_pivots(symbol):
    try:
        df_d = yf.download(symbol, period="2d", interval="1d", progress=False)
        if len(df_d) < 2: return None
        prev = df_d.iloc[-2]
        h, l, c = prev['High'], prev['Low'], prev['Close']
        pp = (h + l + 2 * c) / 4
        return {"R1": (2 * pp) - l, "S1": (2 * pp) - h}
    except: return None

def manage_positions(positions):
    updated = positions.copy()
    for symbol, trade in positions.items():
        try:
            df = yf.download(symbol, period="2d", interval="15m", progress=False, multi_level_index=False)
            df['EMA9'] = df['Close'].ewm(span=9).mean()
            curr = df.iloc[-1]
            
            exit_sig = (trade['Side'] == "🟢 BUY" and curr['Close'] < curr['EMA9']) or \
                       (trade['Side'] == "🔴 SELL" and curr['Close'] > curr['EMA9'])
            
            if exit_sig:
                pts = round(curr['Close'] - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr['Close'], 2)
                pct = round((pts / trade['Entry']) * 100, 2)
                msg = (f"{'💰' if pts > 0 else '🛑'} **EXIT: {symbol.replace('.NS','')}**\n"
                       f"Entry: {trade['Entry']:.2f} | Exit: {curr['Close']:.2f}\n"
                       f"**Points: {pts} ({pct}%)**")
                send_telegram(msg)
                
                with open(TRADE_LOG, 'a', newline='') as f:
                    csv.writer(f).writerow([datetime.now(), symbol, trade['Side'], trade['Entry'], curr['Close'], pts, pct])
                del updated[symbol]
        except: pass
    return updated

def get_signal(symbol, memory, positions):
    try:
        df = yf.download(symbol, period="10d", interval="15m", progress=False, multi_level_index=False)
        pivots = get_woodie_pivots(symbol)
        if df.empty or not pivots: return memory, positions

        df['EMA9'] = df['Close'].ewm(span=9).mean()
        lookback = df.iloc[-5:-1] 
        curr = df.iloc[-1]
        ts = str(df.index[-2])

        # Pattern Check
        def is_pa(candle):
            b = abs(candle['Open'] - candle['Close'])
            ls = candle[['Open', 'Close']].min() - candle['Low']
            us = candle['High'] - candle[['Open', 'Close']].max()
            return (ls > b * 1.3), (us > b * 1.3)

        has_ham = any([is_pa(lookback.iloc[i])[0] for i in range(len(lookback))])
        has_star = any([is_pa(lookback.iloc[i])[1] for i in range(len(lookback))])

        swing_h, swing_l = lookback['High'].max(), lookback['Low'].min()
        is_long = (lookback['Low'].iloc[-1] < lookback['Low'].iloc[0]) and (curr['Close'] > swing_h) and has_ham
        is_short = (lookback['High'].iloc[-1] > lookback['High'].iloc[0]) and (curr['Close'] < swing_l) and has_star

        if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
            vol_delta = curr['Volume'] / (lookback['Volume'].mean() + 1e-9)
            
            if vol_delta > 1.1:
                near_s1 = abs(swing_l - pivots['S1']) / pivots['S1'] < 0.0015
                near_r1 = abs(swing_h - pivots['R1']) / pivots['R1'] < 0.0015
                
                quality = "💎 ELITE (Level Rev)" if (near_s1 if is_long else near_r1) else "🚀 HIGH"
                side = "🟢 BUY" if is_long else "🔴 SELL"
                zone = "S1 Support" if near_s1 else "R1 Resistance" if near_r1 else "Price Action"

                # ML Logging
                with open(ML_LOG, 'a', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=["Date", "Symbol", "Side", "VolDelta", "Zone", "Result"])
                    if os.path.getsize(ML_LOG) == 0: writer.writeheader()
                    writer.writerow({"Date": ts, "Symbol": symbol, "Side": side, "VolDelta": round(vol_delta, 2), "Zone": zone, "Result": "PENDING"})

                msg = (f"🎯 **{side}: {symbol.replace('.NS', '')}**\n"
                       f"---------------------------\n"
                       f"📊 **Quality:** {quality}\n"
                       f"📍 **Zone:** {zone}\n"
                       f"🔥 **Vol Δ:** {vol_delta:.2f}x\n"
                       f"💰 **Entry:** {curr['Close']:.2f}\n"
                       f"🛡️ **SL:** {swing_l if is_long else swing_h:.2f}\n"
                       f"📈 **Ride (9 EMA):** {curr['EMA9']:.2f}")
                
                send_telegram(msg)
                memory[f"{symbol}_{ts}"] = True
                positions[symbol] = {"Entry": curr['Close'], "Side": side, "Time": ts}

    except Exception: pass
    return memory, positions

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_positions(pos)
    for s in SYMBOLS: mem, pos = get_signal(s, mem, pos)
    save_json(mem, MEMORY_FILE); save_json(pos, POSITIONS_FILE)
