import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import pytz
from datetime import datetime
import concurrent.futures

# --- CONFIG ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status_reversal.json"
POSITIONS_FILE = "active_positions_reversal.json"
IST = pytz.timezone('Asia/Kolkata')

# --- FULL VERIFIED F&O UNIVERSE (MAY 2026) ---
SYMBOLS = [
    "^NSEI", "^NSEBANK", "FINNIFTY.NS", "MIDCPNIFTY.NS", "NIFTYNXT50.NS", "360ONE.NS", "AARTIIND.NS", "ABB.NS", 
    "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENSOL.NS", "ADANIENT.NS", "ADANIGREEN.NS", 
    "ADANIPORTS.NS", "ADANIPOWER.NS", "ALKEM.NS", "AMBER.NS", "AMBUJACEM.NS", "ANGELONE.NS", "APLAPOLLO.NS", 
    "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", 
    "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJAJHLDNG.NS", "BAJFINANCE.NS", 
    "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BANKINDIA.NS", "BDL.NS", "BEL.NS", 
    "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", "BLUESTARCO.NS", "BOSCHLTD.NS", 
    "BPCL.NS", "BRITANNIA.NS", "BSE.NS", "BSOFT.NS", "CAMS.NS", "CANBK.NS", "CANFINHOME.NS", "CESC.NS", 
    "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COCHINSHIP.NS", "COFORGE.NS", "COLPAL.NS", 
    "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS", 
    "DELHIVERY.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", 
    "FEDERALBNK.NS", "FORCEMOT.NS", "GAIL.NS", "GLENMARK.NS", "GMRAIRPORT.NS", "GNFC.NS", "GODFRYPHLP.NS", 
    "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", 
    "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS", 
    "HINDUNILVR.NS", "HUDCO.NS", "HYUNDAI.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS", 
    "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", 
    "INFY.NS", "IOC.NS", "IPCALAB.NS", "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", "JIOFIN.NS", "JKCEMENT.NS", 
    "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LICI.NS", "LT.NS", "LTIM.NS", 
    "LTTS.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MAXHEALTH.NS", 
    "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MOTILALOFS.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", 
    "NAM-INDIA.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", 
    "OFSS.NS", "ONGC.NS", "PAGEIND.NS", "PAYTM.NS", "PEL.NS", "PERSISTENT.NS", "PETRONET.NS", "PFC.NS", 
    "PIDILITIND.NS", "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PREMIERENE.NS", "PVRINOX.NS", 
    "RAMCOCEM.NS", "RECLTD.NS", "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS", 
    "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", "SUNTV.NS", "SWIGGY.NS", "SYNGENE.NS", "TATACOMM.NS", 
    "TATACONSUM.NS", "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", 
    "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", "UNITDSPR.NS", "UPL.NS", 
    "V-GUARD.NS", "VEDL.NS", "VMM.NS", "VOLTAS.NS", "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
]

def load_json(f):
    if not os.path.exists(f): return {}
    with open(f, 'r') as file: return json.load(file)

def save_json(d, f):
    with open(f, 'w') as out: json.dump(d, out, indent=4)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def safe_fetch(s, p, i):
    try:
        df = yf.download(s, period=p, interval=i, progress=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def manage_exits(positions):
    updated = positions.copy()
    for s, data in positions.items():
        df = safe_fetch(s, "1d", "1m")
        if df is None or df.empty: continue
        cp = float(df['Close'].iloc[-1])
        entry, target, sl, side = data['Entry'], data['Target'], data['SL'], data['Side']
        rank = data.get('Rank', 'STANDARD')

        # --- TRAILING STOP LOSS (JACKPOT ONLY) ---
        if rank == "🔥 JACKPOT":
            risk = abs(entry - sl)
            if side == "BUY" and cp >= (entry + 2 * risk) and sl < entry:
                data['SL'] = entry # Trail to Breakeven
            elif side == "SELL" and cp <= (entry - 2 * risk) and sl > entry:
                data['SL'] = entry

        # --- EXIT CHECK ---
        hit_t = (side == "BUY" and cp >= target) or (side == "SELL" and cp <= target)
        hit_s = (side == "BUY" and cp <= sl) or (side == "SELL" and cp >= sl)
        
        if hit_t or hit_s:
            status = "🎯 TARGET HIT" if hit_t else "🛑 STOP LOSS"
            pts = round(cp - entry, 2) if side == "BUY" else round(entry - cp, 2)
            send_telegram(f"{status}: {s.replace('.NS','')}\nExit: {cp:.2f}\nPoints: {pts:+.2f}\nRank: {rank}")
            # Logging to CSV
            with open('trade_performance_log.csv', 'a') as log:
                log.write(f"{datetime.now(IST)},{s},{side},{rank},{entry},{cp},{pts}\n")
            del updated[s]
        else:
            updated[s] = data
    return updated

def is_pa(candle):
    """Detects Rejection Wicks with 1.2x logic"""
    o, c, h, l = float(candle['Open']), float(candle['Close']), float(candle['High']), float(candle['Low'])
    body = abs(o - c) + 1e-9
    return ((min(o, c) - l) > body * 1.2), ((h - max(o, c)) > body * 1.2)

def get_pivots(s):
    df = safe_fetch(s, "2d", "1d")
    if df is not None and len(df) >= 2:
        p = df.iloc[-2]
        h, l, cl = float(p['High']), float(p['Low']), float(p['Close'])
        pp = (h + l + 2 * cl) / 4
        return {"PP": pp, "R1": (2*pp)-l, "R2": pp+(h-l), "R3": pp+2*(h-l), "S1": (2*pp)-h, "S2": pp-(h-l), "S3": pp-2*(h-l)}
    return None

def process_symbol(s, memory, positions):
    df1h, df15m = safe_fetch(s, "5d", "1h"), safe_fetch(s, "2d", "15m")
    pivots = get_pivots(s)
    if df1h is None or df15m is None or pivots is None: return None

    is_ham, is_star = is_pa(df1h.iloc[-1])
    m15, m15p = df15m.iloc[-1], df15m.iloc[-2]
    
    vol_surge = m15['Volume'] / (df15m['Volume'].iloc[-11:-1].mean() + 1e-9)
    if vol_surge < 1.2: return None

    # Near Level Check (0.15% threshold)
    near_buy = next((k for k in ["S1", "S2", "S3", "PP"] if abs(m15['Low'] - pivots[k])/pivots[k] <= 0.0015), None)
    near_sell = next((k for k in ["R1", "R2", "R3", "PP"] if abs(m15['High'] - pivots[k])/pivots[k] <= 0.0015), None)

    is_l = (is_ham and m15['Close'] > m15p['High'] and near_buy)
    is_s = (is_star and m15['Close'] < m15p['Low'] and near_sell)

    if (is_l or is_s) and str(df15m.index[-1]) not in memory and s not in positions:
        level_hit = near_buy if is_l else near_sell
        
        # Classification
        if (is_l and level_hit in ["S2", "S3"]) or (is_s and level_hit in ["R2", "R3"]):
            rank, rr = "🔥 JACKPOT", 4
        elif (vol_surge >= 1.7):
            rank, rr = "💎 ELITE", 2
        else:
            rank, rr = "🥇 STANDARD", 2

        entry, sl_val = float(m15['Close']), float(m15['Low'] if is_l else m15['High'])
        risk = abs(entry - sl_val)
        target = entry + (risk * rr) if is_l else entry - (risk * rr)
        side = "BUY" if is_l else "SELL"

        msg = (f"{rank} ALERT: {s.replace('.NS','')}\n"
               f"📍 Level: {level_hit}\n"
               f"🔥 Action: {side} @ {entry:.2f}\n"
               f"🎯 Target: {target:.2f} | 🛡️ SL: {sl_val:.2f}\n"
               f"📊 Vol Surge: {vol_surge:.1f}x")
        
        send_telegram(msg)
        return {"ts": str(df15m.index[-1]), "s": s, "d": {"Entry": entry, "Target": target, "SL": sl_val, "Side": side, "Rank": rank}}
    return None

if __name__ == "__main__":
    now = datetime.now(IST)
    if now.hour < 9 or (now.hour == 9 and now.minute < 15) or now.hour > 15 or (now.hour == 15 and now.minute > 30):
        exit()

    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    pos = manage_exits(pos)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, mem, pos): s for s in SYMBOLS}
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                mem[res["ts"]] = True
                pos[res["s"]] = res["d"]
                
    save_json(mem, MEMORY_FILE)
    save_json(pos, POSITIONS_FILE)
