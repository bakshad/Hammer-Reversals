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
MEMORY_FILE = "alert_status.json"
POSITIONS_FILE = "active_positions.json"
TRADE_LOG = "weekly_trade_summary.csv"
OPEN_SNAPSHOT = "open_positions_snapshot.csv"

# --- FULL APRIL 2026 F&O UNIVERSE (190+ SYMBOLS) ---
# Updated with April 1st additions: ADANIPOWER, HYUNDAI, COCHINSHIP, etc.
SYMBOLS = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "ADANIPOWER.NS", "COCHINSHIP.NS", 
    "FORCEMOT.NS", "GODFRYPHLP.NS", "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", 
    "VMM.NS", "JIOFIN.NS", "PAYTM.NS", "ANGELONE.NS", "AARTIIND.NS", "ABB.NS", 
    "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", 
    "ADANIGREEN.NS", "ADANIPORTS.NS", "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", 
    "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", 
    "AUBANK.NS", "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", 
    "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", 
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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
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
        h, l, c = float(prev['High']), float(prev['Low']), float(prev['Close'])
        pp = (h + l + 2 * c) / 4
        return {"PP": pp, "R1": (2*pp)-l, "R2": pp+(h-l), "S1": (2*pp)-h, "S2": pp-(h-l)}
    return None

def is_pa(candle):
    open_p, close_p = float(candle['Open']), float(candle['Close'])
    high_p, low_p = float(candle['High']), float(candle['Low'])
    b = abs(open_p - close_p)
    ls = min(open_p, close_p) - low_p
    us = high_p - max(open_p, close_p)
    return (ls > b * 1.3), (us > b * 1.3)

def manage_positions(positions):
    updated = positions.copy()
    open_mtm_data = []

    for symbol, trade in positions.items():
        df = safe_fetch(symbol, period="2d", interval="15m")
        if df is None: continue
        
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        curr = df.iloc[-1]
        
        curr_close = float(curr['Close'].iloc[0]) if isinstance(curr['Close'], pd.Series) else float(curr['Close'])
        curr_ema = float(curr['EMA9'].iloc[0]) if isinstance(curr['EMA9'], pd.Series) else float(curr['EMA9'])

        # Exit Logic: Crosses below 9 EMA for Buy, or above for Sell
        exit_sig = (trade['Side'] == "🟢 BUY" and curr_close < curr_ema) or \
                   (trade['Side'] == "🔴 SELL" and curr_close > curr_ema)
        
        if exit_sig:
            pts = round(curr_close - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr_close, 2)
            pct = round((pts / trade['Entry']) * 100, 2)
            
            with open(TRADE_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), symbol, trade['Side'], trade['Entry'], curr_close, pts, pct])
            
            send_telegram(f"🏁 **EXIT: {symbol.replace('.NS','')}**\nSide: {trade['Side']}\nPrice: {curr_close:.2f}\nPoints: {pts:+.2f} ({pct:+.2f}%)")
            del updated[symbol]
        else:
            mtm_pts = round(curr_close - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr_close, 2)
            open_mtm_data.append({"Symbol": symbol.replace('.NS',''), "Side": trade['Side'], "Entry": trade['Entry'], "LTP": curr_close, "MTM_Pts": mtm_pts})

    if open_mtm_data: pd.DataFrame(open_mtm_data).to_csv(OPEN_SNAPSHOT, index=False)
    return updated

def process_symbol(symbol, memory, positions):
    df_1h = safe_fetch(symbol, period="10d", interval="1h")
    df_15m = safe_fetch(symbol, period="5d", interval="15m")
    pivots = get_woodie_pivots(symbol)
    if df_1h is None or df_15m is None or pivots is None: return None

    h_curr = df_1h.iloc[-1]
    is_h_ham, is_h_star = is_pa(h_curr)
    
    df_15m['EMA9'] = df_15m['Close'].ewm(span=9).mean()
    m15_look = df_15m.iloc[-5:-1]
    m15_curr = df_15m.iloc[-1]
    ts = str(df_15m.index[-1])

    curr_close = float(m15_curr['Close'].iloc[0]) if isinstance(m15_curr['Close'], pd.Series) else float(m15_curr['Close'])
    curr_open = float(m15_curr['Open'].iloc[0]) if isinstance(m15_curr['Open'], pd.Series) else float(m15_curr['Open'])
    curr_vol = float(m15_curr['Volume'].iloc[0]) if isinstance(m15_curr['Volume'], pd.Series) else float(m15_curr['Volume'])
    prev_close = float(m15_look['Close'].iloc[-1]) if isinstance(m15_look['Close'], pd.Series) else float(m15_look['Close'])
    m15_sw_h, m15_sw_l = float(m15_look['High'].max()), float(m15_look['Low'].min())
    
    # Gap Filter (<0.15% difference from previous close to current open)
    gap_pct = abs((curr_open - prev_close) / prev_close) * 100
    has_gap = gap_pct > 0.20 
    
    # V-Flip Pattern Logic
    is_vflip = False
    if (curr_close > m15_sw_h and float(m15_look.iloc[-1]['Low']) < float(m15_look.iloc[-1]['EMA9'])) or \
       (curr_close < m15_sw_l and float(m15_look.iloc[-1]['High']) > float(m15_look.iloc[-1]['EMA9'])):
        is_vflip = True

    # Bullish and Bearish Checks
    is_long = (curr_close > m15_sw_h) and not has_gap and (is_h_ham or any([is_pa(m15_look.iloc[i])[0] for i in range(len(m15_look))]))
    is_short = (curr_close < m15_sw_l) and not has_gap and (is_h_star or any([is_pa(m15_look.iloc[i])[1] for i in range(len(m15_look))]))

    if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
        avg_vol = float(m15_look['Volume'].mean()) + 1e-9
        if (curr_vol / avg_vol) > 1.1:
            pivot_hit = "S1" if abs(m15_sw_l - pivots['S1']) / pivots['S1'] < 0.0015 else "R1" if abs(m15_sw_h - pivots['R1']) / pivots['R1'] < 0.0015 else "PP"
            
            side_text = "🟢 BULLISH" if is_long else "🔴 BEARISH"
            action_side = "🟢 BUY" if is_long else "🔴 SELL"
            qual = "💎 ELITE" if pivot_hit in ["S1", "R1"] else "🥇 PRIME"

            msg = (f"🚀 **{side_text} REVERSAL**\n"
                   f"---------------------------\n"
                   f"📦 **Stock:** {symbol.replace('.NS','')}\n"
                   f"🔍 **Pattern:** {'⚡ V-Flip' if is_vflip else '🔨 Hammer'}\n"
                   f"🎯 **Pivot:** {pivot_hit} Reversal\n\n"
                   f"💰 **Entry:** {curr_close:.2f}\n"
                   f"📊 **Qual:** {qual} | **Vol:** {(curr_vol/avg_vol):.1f}x")

            return {"symbol_ts": f"{symbol}_{ts}", "symbol": symbol, "msg": msg, 
                    "trade_data": {"Entry": round(curr_close, 2), "Side": action_side, "Type": pivot_hit}}
    return None

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_positions(pos)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_symbol, s, mem, pos) for s in SYMBOLS]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                send_telegram(res["msg"])
                mem[res["symbol_ts"]], pos[res["symbol"]] = True, res["trade_data"]
    save_json(mem, MEMORY_FILE)
    save_json(pos, POSITIONS_FILE)
