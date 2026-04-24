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

# --- Silence Noise ---
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# --- CONFIGURATION ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status_scalp.json"
POSITIONS_FILE = "active_positions_scalp.json"
TRADE_LOG = "scalp_trade_summary.csv"

# --- FULL APRIL 2026 F&O UNIVERSE (200+ SYMBOLS) ---
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "ADANIPOWER.NS", "COCHINSHIP.NS", 
    "FORCEMOT.NS", "GODFRYPHLP.NS", "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", 
    "VMM.NS", "SWIGGY.NS", "JIOFIN.NS", "PAYTM.NS", "ANGELONE.NS", "ABB.NS", "ABCAPITAL.NS", 
    "ADANIENSOL.NS", "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ALKEM.NS", "AMBUJACEM.NS", 
    "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", 
    "BAJFINANCE.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BEL.NS", "BHARTIARTL.NS", "BHEL.NS", 
    "BPCL.NS", "BRITANNIA.NS", "CANBK.NS", "CIPLA.NS", "COALINDIA.NS", "COFORGE.NS", 
    "CONCOR.NS", "DABUR.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", 
    "EICHERMOT.NS", "GAIL.NS", "HAL.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", 
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "INDIGO.NS", 
    "INDUSINDBK.NS", "INFY.NS", "ITC.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS", 
    "LTIM.NS", "LUPIN.NS", "M&M.NS", "MARICO.NS", "MARUTI.NS", "NTPC.NS", "ONGC.NS", 
    "POWERGRID.NS", "RELIANCE.NS", "SBIN.NS", "SUNPHARMA.NS", "TATACONSUM.NS", 
    "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", "TRENT.NS", 
    "ULTRACEMCO.NS", "WIPRO.NS", "ZOMATO.NS" 
    # [Rest of F&O list truncated for brevity; ensure your local copy is full]
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
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
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
            return {"PP": pp, "R1": (2*pp)-l, "S1": (2*pp)-h}
    except: pass
    return None

def manage_positions(positions):
    updated = positions.copy()
    for symbol, trade in positions.items():
        # TREND RIDING ON 15 MIN CHART
        df_15m = yf.download(symbol, period="1d", interval="15m", progress=False, threads=False)
        if df_15m is None or df_15m.empty: continue
        if isinstance(df_15m.columns, pd.MultiIndex): df_15m.columns = df_15m.columns.get_level_values(0)
        
        df_15m['EMA9'] = df_15m['Close'].ewm(span=9).mean()
        curr_price, ema_val = float(df_15m['Close'].iloc[-1]), float(df_15m['EMA9'].iloc[-1])
        
        # Alert: Milestone
        if not trade.get('t1_reached', False):
            if (trade['Side'] == "🟢 BUY" and curr_price >= trade['T1']) or \
               (trade['Side'] == "🔴 SELL" and curr_price <= trade['T1']):
                send_telegram(f"🎯 **TARGET 1 REACHED: {symbol.replace('.NS','')}**\nPrice: {curr_price:.2f}\nAction: SL at Cost. Riding Trend 🚀")
                updated[symbol]['t1_reached'] = True

        # Exit on Trend Reversal
        exit_sig = (trade['Side'] == "🟢 BUY" and curr_price < ema_val) or \
                   (trade['Side'] == "🔴 SELL" and curr_price > ema_val)
        
        if exit_sig:
            pts = round(curr_price - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr_price, 2)
            pct = round((pts / trade['Entry']) * 100, 2)
            with open(TRADE_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), symbol, trade['Side'], trade['Entry'], curr_price, pts, pct])
            send_telegram(f"🏁 **ELITE EXIT: {symbol.replace('.NS','')}**\nFinal Pts: {pts:+.2f} ({pct:+.2f}%)")
            del updated[symbol]
    return updated

def process_symbol(symbol, memory, positions):
    df_5m = safe_fetch(symbol, period="5d", interval="5m")
    pivots = get_woodie_pivots(symbol)
    if df_5m is None or pivots is None: return None

    # INDICATORS
    delta = df_5m['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df_5m['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    df_5m['EMA9'] = df_5m['Close'].ewm(span=9).mean()
    
    curr, prev = df_5m.iloc[-1], df_5m.iloc[-2]
    curr_rsi, ts = float(curr['RSI']), str(df_5m.index[-1])
    
    # 5m PA DETECTION (Hammer, Engulfing, V-Flip)
    b = abs(curr['Open'] - curr['Close'])
    is_wick = (min(curr['Open'], curr['Close']) - curr['Low'] > b * 1.5) or (curr['High'] - max(curr['Open'], curr['Close']) > b * 1.5)
    is_engulf = (curr['Close'] > prev['Open'] and prev['Close'] < prev['Open']) or (curr['Close'] < prev['Open'] and prev['Close'] > prev['Open'])
    
    # LEVEL AWARENESS (Near Woodie Pivots)
    at_support = abs(curr['Low'] - pivots['S1'])/pivots['S1'] < 0.002 or abs(curr['Low'] - pivots['PP'])/pivots['PP'] < 0.002
    at_resistance = abs(curr['High'] - pivots['R1'])/pivots['R1'] < 0.002 or abs(curr['High'] - pivots['PP'])/pivots['PP'] < 0.002

    # VOLUME SLOPE (1.5x Multiplier for Conviction)
    vol_ratio = float(curr['Volume']) / (df_5m['Volume'].iloc[-5:-1].mean() + 1e-9)
    is_conviction = vol_ratio > 1.5
    is_elite = vol_ratio > 2.0 and (curr_rsi < 30 or curr_rsi > 70)

    # ENTRY LOGIC
    is_long = at_support and (is_wick or is_engulf) and (curr['Close'] > prev['High']) and is_conviction and (curr_rsi < 45)
    is_short = at_resistance and (is_wick or is_engulf) and (curr['Close'] < prev['Low']) and is_conviction and (curr_rsi > 55)

    if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
        t1 = (pivots['PP'] if at_support and curr['Close'] < pivots['PP'] else pivots['R1']) if is_long else \
             (pivots['PP'] if at_resistance and curr['Close'] > pivots['PP'] else pivots['S1'])
        
        prefix = "💎 **ELITE SIGNAL**" if is_elite else "🚀 **SNIPER ALERT**"
        msg = (f"{prefix}: {symbol.replace('.NS','')}\n"
               f"---------------------------\n"
               f"🔥 **Action:** {'🟢 BUY' if is_long else '🔴 SELL'}\n"
               f"📊 **Vol Surge:** {vol_ratio:.1f}x\n"
               f"💰 **Entry:** {curr['Close']:.2f} | **T1:** {t1:.2f}\n"
               f"📉 **RSI:** {curr_rsi:.1f}")
        
        send_telegram(msg)
        return {"symbol_ts": f"{symbol}_{ts}", "symbol": symbol, "trade_data": {"Entry": round(curr['Close'], 2), "Side": "🟢 BUY" if is_long else "🔴 SELL", "T1": t1, "t1_reached": False}}
    return None

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_positions(pos)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, mem, pos): s for s in SYMBOLS}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                mem[res["symbol_ts"]], pos[res["symbol"]] = True, res["trade_data"]
                save_json(mem, MEMORY_FILE); save_json(pos, POSITIONS_FILE)
