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
MEMORY_FILE = "alert_status_scalp.json"
POSITIONS_FILE = "active_positions_scalp.json"
TRADE_LOG = "scalp_trade_summary.csv"

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

def safe_fetch(symbol, period="5d", interval="5m"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def get_woodie_pivots(symbol):
    try:
        df_d = yf.download(symbol, period="5d", interval="1d", progress=False)
        if df_d is not None and len(df_d) >= 2:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            prev = df_d.iloc[-2]
            h, l, c = float(prev['High']), float(prev['Low']), float(prev['Close'])
            pp = (h + l + 2 * c) / 4
            return {"PP": pp, "R1": (2*pp)-l, "R2": pp+(h-l), "S1": (2*pp)-h, "S2": pp-(h-l)}
    except: pass
    return None

def is_pa(candle):
    b = abs(float(candle['Open']) - float(candle['Close']))
    ls = min(float(candle['Open']), float(candle['Close'])) - float(candle['Low'])
    us = float(candle['High']) - max(float(candle['Open']), float(candle['Close']))
    return (ls > b * 1.5), (us > b * 1.5)

def manage_positions(positions):
    updated = positions.copy()
    for symbol, trade in positions.items():
        df = safe_fetch(symbol, period="1d", interval="5m")
        if df is None: continue
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        curr_price = float(df['Close'].iloc[-1])
        ema_val = float(df['EMA9'].iloc[-1])
        
        # 1. Milestone Check (Target 1)
        if not trade.get('t1_reached', False):
            is_t1 = (trade['Side'] == "🟢 BUY" and curr_price >= trade['T1']) or \
                    (trade['Side'] == "🔴 SELL" and curr_price <= trade['T1'])
            if is_t1:
                send_telegram(f"🎯 **TARGET 1 REACHED: {symbol.replace('.NS','')}**\nPrice: {curr_price:.2f}\nAction: Move SL to Cost & Ride 9 EMA 🚀")
                updated[symbol]['t1_reached'] = True

        # 2. Final Exit (9 EMA Cross)
        exit_sig = (trade['Side'] == "🟢 BUY" and curr_price < ema_val) or \
                   (trade['Side'] == "🔴 SELL" and curr_price > ema_val)
        
        if exit_sig:
            pts = round(curr_price - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr_price, 2)
            pct = round((pts / trade['Entry']) * 100, 2)
            
            # Log to CSV
            file_exists = os.path.isfile(TRADE_LOG)
            with open(TRADE_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists: writer.writerow(['Date', 'Symbol', 'Side', 'Entry', 'Exit', 'Points', 'Gain_Pct'])
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), symbol, trade['Side'], trade['Entry'], curr_price, pts, pct])
            
            send_telegram(f"🏁 **FINAL EXIT: {symbol.replace('.NS','')}**\nReason: 9 EMA Cross\nPrice: {curr_close:.2f}\nPoints: {pts:+.2f} ({pct:+.2f}%)")
            del updated[symbol]
    return updated

def get_signal(symbol, memory, positions):
    df_anchor = safe_fetch(symbol, period="5d", interval="15m")
    df_trigger = safe_fetch(symbol, period="2d", interval="5m")
    pivots = get_woodie_pivots(symbol)
    if df_anchor is None or df_trigger is None or pivots is None: return memory, positions

    df_trigger['EMA9'] = df_trigger['Close'].ewm(span=9).mean()
    t_look, t_curr = df_trigger.iloc[-5:-1], df_trigger.iloc[-1]
    curr_close, ts = float(t_curr['Close']), str(df_trigger.index[-1])
    t_sw_h, t_sw_l = float(t_look['High'].max()), float(t_look['Low'].min())
    
    is_long = (curr_close > t_sw_h) and (is_pa(df_anchor.iloc[-1])[0] or any([is_pa(t_look.iloc[i])[0] for i in range(len(t_look))]))
    is_short = (curr_close < t_sw_l) and (is_pa(df_anchor.iloc[-1])[1] or any([is_pa(t_look.iloc[i])[1] for i in range(len(t_look))]))

    if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
        vol_delta = float(t_curr['Volume']) / (float(t_look['Volume'].mean()) + 1e-9)
        
        if vol_delta > 1.5: 
            near_s1 = abs(t_sw_l - pivots['S1']) / pivots['S1'] < 0.0015
            near_r1 = abs(t_sw_h - pivots['R1']) / pivots['R1'] < 0.0015
            near_pp = abs((t_sw_l if is_long else t_sw_h) - pivots['PP']) / pivots['PP'] < 0.0015

            if (is_long and (near_s1 or near_pp)) or (is_short and (near_r1 or near_pp)):
                pivot_name = "S1" if near_s1 else "R1" if near_r1 else "PP"
                direction = "🟢 BULLISH" if is_long else "🔴 BEARISH"
                
                if is_long:
                    side, sl = "🟢 BUY", t_sw_l
                    t1 = pivots['PP'] if near_s1 else pivots['R1']
                else:
                    side, sl = "🔴 SELL", t_sw_h
                    t1 = pivots['PP'] if near_r1 else pivots['S1']

                msg = (f"🚀 **{direction} REVERSAL**\n"
                       f"---------------------------\n"
                       f"📦 **Stock:** {symbol.replace('.NS','')}\n"
                       f"🎯 **Pivot:** {pivot_name} Reversal\n"
                       f"💰 **Entry:** {curr_close:.2f} | **SL:** {sl:.2f}\n"
                       f"🎯 **Target 1:** {t1:.2f}\n"
                       f"📈 **Strategy:** Ride 9 EMA Trend")
                
                send_telegram(msg)
                memory[f"{symbol}_{ts}"] = True
                positions[symbol] = {"Entry": round(curr_close, 2), "Side": side, "T1": t1, "t1_reached": False}
    return memory, positions

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_positions(pos)
    for s in SYMBOLS: 
        mem, pos = get_signal(s, mem, pos)
    save_json(mem, MEMORY_FILE)
    save_json(pos, POSITIONS_FILE)
