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
MEMORY_FILE = "alert_status_reversal.json"
POSITIONS_FILE = "active_positions_reversal.json"
TRADE_LOG = "weekly_trade_summary.csv"

# --- FULL APRIL 2026 F&O UNIVERSE ---
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "ADANIPOWER.NS", "COCHINSHIP.NS", 
    "FORCEMOT.NS", "GODFRYPHLP.NS", "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", 
    "VMM.NS", "SWIGGY.NS", "JIOFIN.NS", "PAYTM.NS", "ANGELONE.NS", "AARTIIND.NS", 
    "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", 
    "ADANIGREEN.NS", "ADANIPORTS.NS", "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", 
    "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", 
    "AUBANK.NS", "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", 
    "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", "BANKBARODA.NS", 
    "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", 
    "BOSCHLTD.NS", "BPCL.NS", "BRITANNIA.NS", "BSOFT.NS", "CANBK.NS", "CANFINHOME.NS", 
    "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COFORGE.NS", "COLPAL.NS", 
    "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", 
    "DEEPAKNTR.NS", "DELHIVERY.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", 
    "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS", "GLENMARK.NS", 
    "GMRAIRPORT.NS", "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", 
    "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", 
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS", "HINDUNILVR.NS", 
    "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", 
    "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "IOC.NS", 
    "IPCALAB.NS", "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", 
    "JUBLFOOD.NS", "KOTAKBANK.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LT.NS", "LUPIN.NS", 
    "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MCX.NS", 
    "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", 
    "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", 
    "OBEROIRLTY.NS", "ONGC.NS", "PAGEIND.NS", "PEL.NS", "PERSISTENT.NS", "PETRONET.NS", 
    "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", 
    "PVRINOX.NS", "RAMCOCEM.NS", "RECLTD.NS", "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", 
    "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", 
    "SUNPHARMA.NS", "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS", "TATACONSUM.NS", 
    "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", 
    "TECHM.NS", "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS", 
    "ULTRACEMCO.NS", "UPL.NS", "VEDL.NS", "VOLTAS.NS", "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
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

def safe_fetch(symbol, period="10d", interval="15m"):
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
    return (ls > b * 1.3), (us > b * 1.3)

def manage_positions(positions):
    updated = positions.copy()
    for symbol, trade in positions.items():
        df = safe_fetch(symbol, period="2d", interval="15m")
        if df is None: continue
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        curr_price = float(df['Close'].iloc[-1])
        ema_val = float(df['EMA9'].iloc[-1])
        
        if not trade.get('t1_reached', False):
            is_t1 = (trade['Side'] == "🟢 BUY" and curr_price >= trade['T1']) or \
                    (trade['Side'] == "🔴 SELL" and curr_price <= trade['T1'])
            if is_t1:
                send_telegram(f"🎯 **TARGET REACHED: {symbol.replace('.NS','')}**\nPrice: {curr_price:.2f}\nAction: Riding 9 EMA Trend 🚀")
                updated[symbol]['t1_reached'] = True

        exit_sig = (trade['Side'] == "🟢 BUY" and curr_price < ema_val) or \
                   (trade['Side'] == "🔴 SELL" and curr_price > ema_val)
        
        if exit_sig:
            pts = round(curr_price - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr_price, 2)
            pct = round((pts / trade['Entry']) * 100, 2)
            file_exists = os.path.isfile(TRADE_LOG)
            with open(TRADE_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists: writer.writerow(['Date', 'Symbol', 'Side', 'Entry', 'Exit', 'Points', 'Gain_Pct'])
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), symbol, trade['Side'], trade['Entry'], curr_price, pts, pct])
            
            send_telegram(f"🏁 **EXIT: {symbol.replace('.NS','')}**\nReason: 9 EMA Cross\nFinal Pts: {pts:+.2f} ({pct:+.2f}%)")
            del updated[symbol]
    return updated

def process_symbol(symbol, memory, positions):
    df_15m = safe_fetch(symbol, period="5d", interval="15m")
    pivots = get_woodie_pivots(symbol)
    if df_15m is None or pivots is None: return None

    # Intrabar 1H Logic
    df_1h = df_15m.resample('1H').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
    h_curr = df_1h.iloc[-1]
    is_h_ham, is_h_star = is_pa(h_curr)
    
    df_15m['EMA9'] = df_15m['Close'].ewm(span=9).mean()
    m15_look = df_15m.iloc[-5:-1]
    m15_curr = df_15m.iloc[-1]
    curr_close, ts = float(m15_curr['Close']), str(df_15m.index[-1])
    m15_sw_h, m15_sw_l = float(m15_look['High'].max()), float(m15_look['Low'].min())
    
    # Gap Calculation
    prev_close = float(m15_look['Close'].iloc[-1])
    gap_pct = abs((float(m15_curr['Open']) - prev_close) / prev_close) * 100

    # V-Flip Recognition
    is_vflip = False
    if (curr_close > m15_sw_h and float(m15_look.iloc[-1]['Low']) < float(m15_look.iloc[-1]['EMA9'])) or \
       (curr_close < m15_sw_l and float(m15_look.iloc[-1]['High']) > float(m15_look.iloc[-1]['EMA9'])):
        is_vflip = True

    # DYNAMIC GAP FILTER: Allow more room (0.30%) if it's a V-Flip reversal
    max_allowed_gap = 0.30 if is_vflip else 0.15
    if gap_pct > max_allowed_gap: return None

    is_long = (curr_close > m15_sw_h) and is_h_ham
    is_short = (curr_close < m15_sw_l) and is_h_star

    if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
        vol_delta = float(m15_curr['Volume']) / (float(m15_look['Volume'].mean()) + 1e-9)
        
        if vol_delta > 1.1:
            near_s1 = abs(m15_sw_l - pivots['S1']) / pivots['S1'] < 0.0015
            near_r1 = abs(m15_sw_h - pivots['R1']) / pivots['R1'] < 0.0015
            near_pp = abs((m15_sw_l if is_long else m15_sw_h) - pivots['PP']) / pivots['PP'] < 0.0015

            if (is_long and (near_s1 or near_pp or near_r1)) or (is_short and (near_r1 or near_pp or near_s1)):
                pivot_name = "S1" if near_s1 else ("PP" if near_pp else "R1")
                direction = "🟢 BULLISH" if is_long else "🔴 BEARISH"
                trade_side = "🟢 BUY" if is_long else "🔴 SELL"
                pattern = "⚡ V-Flip" if is_vflip else "🔨 Hammer/Star"

                # Directional Targets
                if is_long:
                    t1 = pivots['PP'] if near_s1 else (pivots['R1'] if near_pp else pivots['R2'])
                    sl = m15_sw_l
                else:
                    t1 = pivots['PP'] if near_r1 else (pivots['S1'] if near_pp else pivots['S2'])
                    sl = m15_sw_h

                msg = (f"🚀 **{direction} REVERSAL**\n"
                       f"---------------------------\n"
                       f"📦 **Stock:** {symbol.replace('.NS','')}\n"
                       f"🔍 **Pattern:** {pattern}\n"
                       f"🎯 **Pivot:** {pivot_name} Reversal\n"
                       f"💰 **Entry:** {curr_close:.2f} | **SL:** {sl:.2f}\n"
                       f"🎯 **Target 1:** {t1:.2f}\n"
                       f"📈 **Strategy:** Ride 9 EMA Trend")
                
                return {"symbol_ts": f"{symbol}_{ts}", "symbol": symbol, "msg": msg, 
                        "trade_data": {"Entry": round(curr_close, 2), "Side": trade_side, "T1": t1, "t1_reached": False}}
    return None

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_positions(pos)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, mem, pos): s for s in SYMBOLS}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                send_telegram(res["msg"])
                mem[res["symbol_ts"]] = True
                pos[res["symbol"]] = res["trade_data"]
    save_json(mem, MEMORY_FILE)
    save_json(pos, POSITIONS_FILE)
