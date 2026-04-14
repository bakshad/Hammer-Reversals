import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import csv
import logging
from datetime import datetime

# --- Silence Noise ---
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# --- CONFIGURATION ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status.json"
POSITIONS_FILE = "active_positions.json"
TRADE_LOG = "weekly_trade_summary.csv"

# --- FULL APRIL 2026 F&O UNIVERSE ---
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "ADANIPOWER.NS", "COCHINSHIP.NS", 
    "FORCEMOT.NS", "GODFRYPHLP.NS", "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", 
    "VMM.NS", "SWIGGY.NS", "LTF.NS", "UNITDSPR.NS", "IDFCFIRSTB.NS", "LTIM.NS",
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
    "HINDUNILVR.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IGL.NS", 
    "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", 
    "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IPCALAB.NS", "IRCTC.NS", "ITC.NS", 
    "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", 
    "LALPATHLAB.NS", "LICHSGFIN.NS", "LT.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", 
    "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MCX.NS", "METROPOLIS.NS", "MFSL.NS", 
    "MGL.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", 
    "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", "ONGC.NS", "PAGEIND.NS", 
    "PEL.NS", "PERSISTENT.NS", "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", "PIIND.NS", 
    "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", "RECLTD.NS", 
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

def safe_fetch(symbol, period="10d", interval="15m"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        if df is None or df.empty or len(df) < 5: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def get_woodie_pivots(symbol):
    df_d = safe_fetch(symbol, period="2d", interval="1d")
    if df_d is not None and len(df_d) >= 2:
        prev = df_d.iloc[-2]
        h, l, c = prev['High'], prev['Low'], prev['Close']
        pp = (h + l + 2 * c) / 4
        return {"PP": pp, "R1": (2*pp)-l, "R2": pp+(h-l), "S1": (2*pp)-h, "S2": pp-(h-l)}
    return None

def is_pa(candle):
    b = abs(candle['Open'] - candle['Close'])
    ls = candle[['Open', 'Close']].min() - candle['Low']
    us = candle['High'] - candle[['Open', 'Close']].max()
    return (ls > b * 1.3), (us > b * 1.3)

def manage_positions(positions):
    updated = positions.copy()
    for symbol, trade in positions.items():
        df = safe_fetch(symbol, period="2d", interval="15m")
        if df is None: continue
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        curr = df.iloc[-1]
        exit_sig = (trade['Side'] == "🟢 BUY" and curr['Close'] < curr['EMA9']) or \
                   (trade['Side'] == "🔴 SELL" and curr['Close'] > curr['EMA9'])
        if exit_sig:
            pts = round(curr['Close'] - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr['Close'], 2)
            pct = round((pts / trade['Entry']) * 100, 2)
            msg = f"🏁 **EXIT: {symbol.replace('.NS','')}**\nEntry: {trade['Entry']} | Exit: {curr['Close']:.2f}\n**Pts: {pts} ({pct}%)**"
            send_telegram(msg)
            with open(TRADE_LOG, 'a', newline='') as f:
                csv.writer(f).writerow([datetime.now(), symbol, trade['Side'], trade['Entry'], curr['Close'], pts, pct])
            del updated[symbol]
    return updated

def get_signal(symbol, memory, positions):
    df_1h = safe_fetch(symbol, period="10d", interval="1h")
    df_15m = safe_fetch(symbol, period="5d", interval="15m")
    pivots = get_woodie_pivots(symbol)
    if df_1h is None or df_15m is None or pivots is None: return memory, positions

    h_curr = df_1h.iloc[-1]
    is_h_ham, is_h_star = is_pa(h_curr)
    
    df_15m['EMA9'] = df_15m['Close'].ewm(span=9).mean()
    m15_look = df_15m.iloc[-5:-1]
    m15_curr = df_15m.iloc[-1]
    ts = str(df_15m.index[-1])

    m15_sw_h, m15_sw_l = m15_look['High'].max(), m15_look['Low'].min()
    is_long = (m15_curr['Close'] > m15_sw_h) and (is_h_ham or any([is_pa(m15_look.iloc[i])[0] for i in range(len(m15_look))]))
    is_short = (m15_curr['Close'] < m15_sw_l) and (is_h_star or any([is_pa(m15_look.iloc[i])[1] for i in range(len(m15_look))]))

    if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
        vol_delta = m15_curr['Volume'] / (m15_look['Volume'].mean() + 1e-9)
        if vol_delta > 1.1:
            near_s1 = abs(m15_sw_l - pivots['S1']) / pivots['S1'] < 0.0015
            near_r1 = abs(m15_sw_h - pivots['R1']) / pivots['R1'] < 0.0015
            near_pp = abs((m15_sw_l if is_long else m15_sw_h) - pivots['PP']) / pivots['PP'] < 0.0015

            if is_long:
                side, sl = "🟢 BUY", m15_sw_l
                t1, t2 = (pivots['PP'], pivots['R1']) if near_s1 else (pivots['R1'], pivots['R2'])
                qual = "💎 ELITE" if near_s1 else ("🥇 PRIME" if near_pp else "🚀 HIGH")
            else:
                side, sl = "🔴 SELL", m15_sw_h
                t1, t2 = (pivots['PP'], pivots['S1']) if near_r1 else (pivots['S1'], pivots['S2'])
                qual = "💎 ELITE" if near_r1 else ("🥇 PRIME" if near_pp else "🚀 HIGH")

            msg = (f"🎯 **{side}: {symbol.replace('.NS','')}**\n"
                   f"---------------------------\n"
                   f"📊 **Qual:** {qual} | **Anchor:** 1-Hour Reversal\n"
                   f"💰 **Entry:** {m15_curr['Close']:.2f} | **SL:** {sl:.2f}\n"
                   f"🎯 **T1:** {t1:.2f} | **T2:** {t2:.2f}\n"
                   f"📈 **Trail:** 9 EMA ({m15_curr['EMA9']:.2f})")
            send_telegram(msg)
            memory[f"{symbol}_{ts}"] = True
            positions[symbol] = {"Entry": round(m15_curr['Close'], 2), "Side": side, "Time": ts}
    return memory, positions

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_positions(pos)
    for s in SYMBOLS: mem, pos = get_signal(s, mem, pos)
    save_json(mem, MEMORY_FILE); save_json(pos, POSITIONS_FILE)
