import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import pytz
from datetime import datetime
import concurrent.futures

# --- CONFIGURATION ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status_reversal.json"
POSITIONS_FILE = "active_positions_reversal.json"
IST = pytz.timezone('Asia/Kolkata')

# --- FULL SYMBOLS LIST ---
SYMBOLS = [
    "^NSEI", "^NSEBANK", "FINNIFTY.NS", "MIDCPNIFTY.NS", "NIFTYNXT50.NS", "360ONE.NS", "AARTIIND.NS", "ABB.NS", 
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

def manage_exits(positions):
    """Monitors open trades for Target/SL hits"""
    updated_positions = positions.copy()
    for symbol, data in positions.items():
        df = safe_fetch(symbol, "1d", "1m")
        if df is None or df.empty: continue
        
        curr_price = float(df['Close'].iloc[-1])
        entry, target, sl, side = data['Entry'], data['Target'], data['SL'], data['Side']
        
        hit_target = (side == "BUY" and curr_price >= target) or (side == "SELL" and curr_price <= target)
        hit_sl = (side == "BUY" and curr_price <= sl) or (side == "SELL" and curr_price >= sl)
        
        if hit_target or hit_sl:
            status = "🎯 TARGET REACHED" if hit_target else "🛑 STOP LOSS HIT"
            pnl = curr_price - entry if side == "BUY" else entry - curr_price
            msg = (f"{status}: {symbol.replace('.NS','')}\n"
                   f"Exit: {curr_price:.2f} | PnL: {pnl:+.2f}")
            send_telegram(msg)
            del updated_positions[symbol]
    return updated_positions

def get_woodie_pivots(symbol):
    df_d = safe_fetch(symbol, "2d", "1d")
    if df_d is not None and len(df_d) >= 2:
        prev = df_d.iloc[-2]
        h, l, c = float(prev['High']), float(prev['Low']), float(prev['Close'])
        pp = (h + l + 2 * c) / 4
        return {"PP": pp, "R1": (2*pp)-l, "R2": pp+(h-l), "S1": (2*pp)-h, "S2": pp-(h-l)}
    return None

def is_near_level(price, levels, threshold=0.0015):
    for name, val in levels.items():
        if abs(price - val) / val <= threshold:
            return name
    return None

def is_pa(candle):
    open_p, close_p = float(candle['Open']), float(candle['Close'])
    high_p, low_p = float(candle['High']), float(candle['Low'])
    body = abs(open_p - close_p)
    lower_wick = min(open_p, close_p) - low_p
    upper_wick = high_p - max(open_p, close_p)
    return (lower_wick > body * 1.5), (upper_wick > body * 1.5)

def process_symbol(symbol, memory, positions):
    df_1h = safe_fetch(symbol, "5d", "1h")
    df_15m = safe_fetch(symbol, "2d", "15m")
    pivots = get_woodie_pivots(symbol)
    
    if df_1h is None or df_15m is None or pivots is None: return None

    curr_h = df_1h.iloc[-1]
    is_h_hammer, is_h_star = is_pa(curr_h)
    
    m15_curr, m15_prev = df_15m.iloc[-1], df_15m.iloc[-2]
    ts_15m = str(df_15m.index[-1])
    
    avg_vol = df_15m['Volume'].iloc[-11:-1].mean() + 1e-9
    vol_surge = m15_curr['Volume'] / avg_vol
    if vol_surge < 1.2: return None 

    level_buy = is_near_level(float(m15_curr['Low']), {k: pivots[k] for k in ["S1", "S2", "PP"]})
    level_sell = is_near_level(float(m15_curr['High']), {k: pivots[k] for k in ["R1", "R2", "PP"]})

    is_long = is_h_hammer and (m15_curr['Close'] > m15_prev['High']) and level_buy
    is_short = is_h_star and (m15_curr['Close'] < m15_prev['Low']) and level_sell

    if (is_long or is_short) and f"{symbol}_{ts_15m}" not in memory and symbol not in positions:
        is_major = (level_buy in ["S1", "PP"]) or (level_sell in ["R1", "PP"])
        rank = "💎 ELITE" if (vol_surge >= 1.7 and is_major) else "🥇 STANDARD"
        side = "BUY" if is_long else "SELL"
        level_name = level_buy if is_long else level_sell
        
        entry = float(m15_curr['Close'])
        stop_loss = float(m15_curr['Low'] if is_long else m15_curr['High'])
        risk = abs(entry - stop_loss)
        t1 = entry + (risk * 2) if is_long else entry - (risk * 2)
        
        msg = (f"{rank} REVERSAL AT {level_name}\n"
               f"---------------------------\n"
               f"📦 Stock: {symbol.replace('.NS','')}\n"
               f"🔥 Action: {'🟢' if is_long else '🔴'} {side}\n"
               f"📊 Vol Surge: {vol_surge:.1f}x\n"
               f"💰 Entry: {entry:.2f}\n"
               f"🛡️ SL: {stop_loss:.2f} | 🎯 T1: {t1:.2f}\n"
               f"🕒 {ts_15m}")
        
        return {"msg": msg, "symbol_ts": f"{symbol}_{ts_15m}", "symbol": symbol, "data": {"Entry": round(entry, 2), "Side": side, "Target": round(t1, 2), "SL": round(stop_loss, 2)}}
    return None

if __name__ == "__main__":
    now_ist = datetime.now(IST)
    
    # --- MARKET HOURS CHECK (9:15 AM - 3:30 PM) ---
    if now_ist.hour < 9 or (now_ist.hour == 9 and now_ist.minute < 15) or now_ist.hour > 15 or (now_ist.hour == 15 and now_ist.minute > 30):
        print(f"Market Closed at {now_ist.strftime('%H:%M')}. Exiting.")
        exit()

    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    
    # 1. Manage Exits First
    pos = manage_exits(pos)
    
    # 2. Scan for New Signals
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, mem, pos): s for s in SYMBOLS}
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                send_telegram(res["msg"])
                mem[res["symbol_ts"]] = True
                pos[res["symbol"]] = res["data"]
                
    save_json(mem, MEMORY_FILE)
    save_json(pos, POSITIONS_FILE)
