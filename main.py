import json
import os
import sys
import pandas as pd
import numpy as np
import requests
import pytz
import threading
import time  
from datetime import datetime, timedelta
import concurrent.futures

# =====================================================================
# 🛠️ CONFIGURATION & CREDENTIALS
# =====================================================================
TOKEN = "7877603565:AAEHDfLHalyRdDM3Let7vMd62VGltgsz33Q"
CHAT_ID = "741983167"

# Directory updated for GitHub Actions (Root folder)
BASE_DIR = "./"
MEMORY_FILE = os.path.join(BASE_DIR, "alert_status_reversal.json")      
POSITIONS_FILE = os.path.join(BASE_DIR, "active_positions_reversal.json") 
LOG_FILE = os.path.join(BASE_DIR, "trade_performance_log.csv")          
SNAPSHOT_FILE = os.path.join(BASE_DIR, "active_pnl_snapshot.csv")       
IST = pytz.timezone('Asia/Kolkata')

# --- SYNTHETIC LOT SIZE CACHE (SEBI 2026 Mandate) ---
SYNTHETIC_LOTS = {
    "NIFTY": 65, "BANKNIFTY": 30, 
    "360ONE": 500, "AARTIIND": 850, "ABB": 125, "ABBOTINDIA": 40, "ABCAPITAL": 3100, 
    "ABFRL": 2600, "ACC": 250, "ADANIENSOL": 675, "ADANIENT": 309, "ADANIGREEN": 600, 
    "ADANIPORTS": 475, "ADANIPOWER": 3550, "ALKEM": 125, "AMBER": 100, "AMBUJACEM": 1200, 
    "ANGELONE": 2500, "APLAPOLLO": 350, "APOLLOHOSP": 125, "APOLLOTYRE": 1700, "ASHOKLEY": 5000, 
    "ASIANPAINT": 250, "ASTRAL": 425, "ATUL": 75, "AUBANK": 1000, "AUROPHARMA": 550, 
    "AXISBANK": 625, "BAJAJ-AUTO": 75, "BAJAJFINSV": 300, "BAJAJHLDNG": 75, "BAJFINANCE": 750, 
    "BALKRISIND": 300, "BALRAMCHIN": 1600, "BANDHANBNK": 3600, "BANKBARODA": 2925, "BANKINDIA": 5200, 
    "BDL": 425, "BEL": 1425, "BERGEPAINT": 1100, "BHARATFORG": 500, "BHARTIARTL": 475, 
    "BHEL": 2625, "BIOCON": 2500, "BLUESTARCO": 325, "BOSCHLTD": 25, "BPCL": 1975, 
    "BRITANNIA": 125, "BSE": 200, "BSOFT": 1300, "CAMS": 825, "CANBK": 2700, 
    "CANFINHOME": 975, "CESC": 3500, "CHAMBLFERT": 1500, "CHOLAFIN": 1250, "CIPLA": 650, 
    "COALINDIA": 4200, "COCHINSHIP": 300, "COFORGE": 150, "COLPAL": 350, "CONCOR": 1000, 
    "COROMANDEL": 700, "CROMPTON": 1500, "CUMMINSIND": 600, "DABUR": 1250, "DALBHARAT": 250, 
    "DEEPAKNTR": 300, "DELHIVERY": 1000, "DIVISLAB": 200, "DIXON": 100, "DLF": 1650, 
    "DRREDDY": 125, "EICHERMOT": 175, "ESCORTS": 275, "EXIDEIND": 3600, "FEDERALBNK": 5000, 
    "FORCEMOT": 100, "GAIL": 9150, "GLENMARK": 575, "GMRAIRPORT": 11250, "GNFC": 1300, 
    "GODFRYPHLP": 150, "GODREJCP": 500, "GODREJPROP": 475, "GRANULES": 2000, "GRASIM": 477, 
    "GUJGASLTD": 1250, "HAL": 300, "HAVELLS": 500, "HCLTECH": 700, "HDFCBANK": 550, 
    "HDFCLIFE": 1100, "HEROMOTOCO": 150, "HINDALCO": 1400, "HINDCOPPER": 4300, "HINDPETRO": 2700, 
    "HINDUNILVR": 300, "HUDCO": 4000, "HYUNDAI": 250, "ICICIBANK": 700, "ICICIGI": 500, 
    "ICICIPRULI": 1500, "IDFCFIRSTB": 7500, "IGL": 1375, "INDHOTEL": 4022, "INDIACEM": 2900, 
    "INDIAMART": 150, "INDIGO": 300, "INDUSINDBK": 450, "INDUSTOWER": 2800, "INFY": 400, 
    "IOC": 9750, "IPCALAB": 650, "IRCTC": 875, "ITC": 1600, "JINDALSTEL": 1250, 
    "JIOFIN": 2000, "JKCEMENT": 250, "JSWSTEEL": 675, "JUBLFOOD": 1250, "KOTAKBANK": 400, 
    "LALPATHLAB": 300, "LICHSGFIN": 1000, "LICI": 500, "LT": 300, "LTIM": 150, 
    "LTTS": 200, "LUPIN": 850, "M&M": 350, "M&MFIN": 2000, "MANAPPURAM": 6000, 
    "MARICO": 1200, "MARUTI": 50, "MAXHEALTH": 500, "MCX": 400, "METROPOLIS": 300, 
    "MFSL": 800, "MGL": 400, "MOTILALOFS": 500, "MPHASIS": 275, "MRF": 5, 
    "MUTHOOTFIN": 400, "NAM-INDIA": 1200, "NATIONALUM": 7500, "NAVINFLUOR": 150, "NESTLEIND": 400, 
    "NMDC": 4500, "NTPC": 3000, "OBEROIRLTY": 350, "OFSS": 100, "ONGC": 3850, 
    "PAGEIND": 15, "PAYTM": 750, "PEL": 500, "PERSISTENT": 100, "PETRONET": 3000, 
    "PFC": 3875, "PIDILITIND": 250, "PIIND": 250, "PNB": 8000, "POLYCAB": 100, 
    "POWERGRID": 3600, "PREMIERENE": 400, "PVRINOX": 407, "RAMCOCEM": 850, "RECLTD": 2000, 
    "RELIANCE": 250, "SAIL": 8000, "SBICARD": 800, "SBILIFE": 750, "SBIN": 750, 
    "SHREECEM": 25, "SHRIRAMFIN": 300, "SIEMENS": 150, "SRF": 375, "SUNPHARMA": 700, 
    "SUNTV": 1500, "SWIGGY": 1000, "SYNGENE": 1000, "TATACOMM": 500, "TATACONSUM": 900, "TATAELXSI": 100, 
    "TATAMOTORS": 1425, "TATAPOWER": 3375, "TATASTEEL": 5500, "TCS": 175, "TECHM": 600, 
    "TITAN": 175, "TORNTPHARM": 500, "TRENT": 400, "TVSMOTOR": 350, "UBL": 400, 
    "ULTRACEMCO": 100, "UNITDSPR": 700, "UPL": 1300, "V-GUARD": 1000, "VEDL": 2000, 
    "VMM": 400, "VOLTAS": 600, "WIPRO": 1500, "ZOMATO": 2500, "ZYDUSLIFE": 900
}

SYMBOLS = list(SYNTHETIC_LOTS.keys())

# =====================================================================
# 🛠️ HELPER FUNCTIONS
# =====================================================================
def load_json(f):
    if not os.path.exists(f) or os.path.getsize(f) == 0: return {}
    with open(f, 'r') as file: return json.load(file)

def save_json(d, f):
    with open(f, 'w') as out: json.dump(d, out, indent=4)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def send_document_telegram(file_path, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f})
    except Exception as e:
        print(f"Failed to send document: {e}")

def get_yf_symbol(symbol):
    if symbol == "NIFTY": return "^NSEI"
    if symbol == "BANKNIFTY": return "^NSEBANK"
    if symbol in ["FINNIFTY", "MIDCPNIFTY"]: return None  
    return f"{symbol}.NS"

def get_synthetic_strike_and_lot(symbol, price):
    lot_size = SYNTHETIC_LOTS.get(symbol, 1)
    if "NIFTY" == symbol: strike = int(round(price / 50) * 50)
    elif "BANKNIFTY" == symbol: strike = int(round(price / 100) * 100)
    elif "FINNIFTY" == symbol: strike = int(round(price / 50) * 50)
    elif "MIDCPNIFTY" == symbol: strike = int(round(price / 25) * 25)
    else:
        step = 100 if price > 5000 else (20 if price > 1000 else (10 if price > 500 else (5 if price > 100 else 1)))
        strike = int(round(price / step) * step)
    return strike, lot_size

def safe_fetch(s, period_days, interval):
    yf_ticker = get_yf_symbol(s)
    if not yf_ticker: return None
    
    yf_range = "5d" if "5d" in period_days else ("3d" if "3d" in period_days else "1d")
    yf_interval = "1d" if interval == "1d" else ("15m" if interval == "15m" else "5m")
    
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{yf_ticker}?interval={yf_interval}&range={yf_range}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return None
        
        data = res.json()
        result = data.get('chart', {}).get('result', [])
        if not result: return None
        
        timestamps = result[0].get('timestamp', [])
        quote = result[0].get('indicators', {}).get('quote', [{}])[0]
        
        if not timestamps or not quote: return None
        
        df = pd.DataFrame({
            'Datetime': pd.to_datetime(timestamps, unit='s', utc=True),
            'open': quote.get('open', []),
            'high': quote.get('high', []),
            'low': quote.get('low', []),
            'close': quote.get('close', []),
            'volume': quote.get('volume', [])
        })
        
        df.dropna(inplace=True)
        df.set_index('Datetime', inplace=True)
        df.index = df.index.tz_convert('Asia/Kolkata').tz_localize(None)
        
        df['ema33'] = df['close'].ewm(span=33, adjust=False).mean()
        hl = df['high'] - df['low']
        hcp = abs(df['high'] - df['close'].shift())
        lcp = abs(df['low'] - df['close'].shift())
        df['atr'] = pd.concat([hl, hcp, lcp], axis=1).max(axis=1).rolling(14).mean()
        
        return df
    except Exception:
        return None

def get_daily_context(s):
    df = safe_fetch(s, "5d", "1d")
    if df is not None and len(df) >= 2:
        prev, curr = df.iloc[-2], df.iloc[-1]
        gap_pct = abs(float(curr['open']) - float(prev['close'])) / float(prev['close'])
        h, l, cl = float(prev['high']), float(prev['low']), float(prev['close'])
        pp = (h + l + 2 * cl) / 4
        return {
            "Gap": gap_pct > 0.005, "PP": pp, 
            "R1": (2*pp)-l, "R2": pp+(h-l), "R3": pp+2*(h-l), 
            "S1": (2*pp)-h, "S2": pp-(h-l), "S3": pp-2*(h-l)
        }
    return None

def is_pa(candle):
    try:
        o, c, h, l = float(candle['open']), float(candle['close']), float(candle['high']), float(candle['low'])
        body = abs(o - c) + 1e-9
        return (min(o, c) - l >= body * 1.2) and (h - max(o, c) <= body), (h - max(o, c) >= body * 1.2) and (min(o, c) - l <= body)
    except: return False, False

def manage_exits(positions):
    updated = positions.copy()
    for s, data in positions.items():
        df = safe_fetch(s, "1d", "5m")
        if df is None or df.empty: continue
        cp = float(df['close'].iloc[-1])
        ema33 = float(df['ema33'].iloc[-1])
        
        entry_stk, targets, sl, side = data['Entry'], data['Targets'], data['SL'], data['Side']
        idx = data.get('T_Idx', 0)
        rank = data.get('Rank', 'STANDARD')
        strike, opt_type = data['Strike'], data['Opt_Type']
        init_opt_p, lot_size = data['Init_Opt_Price'], data['Lot_Size']
        
        stk_change = (cp - entry_stk) if side == "BUY" else (entry_stk - cp)
        opt_ltp = max(0.10, round(init_opt_p + (stk_change * 0.50), 2))
        opt_points = round(opt_ltp - init_opt_p, 2)
        current_pnl = round(opt_points * lot_size, 2)

        # 🛠️ UPDATED CSV COLUMNS: Underlying_LTP, Opt_Entry, Opt_Exit, PnL
        with open(SNAPSHOT_FILE, 'a') as sf:
            sf.write(f"{datetime.now(IST)},{s},RUNNING_PNL,{side},{rank},{strike},{opt_type},{lot_size},{cp},{init_opt_p},{opt_ltp},{current_pnl}\n")

        if idx >= 1:
            sl = max(sl, ema33) if side == "BUY" else min(sl, ema33)

        hit_t = (side == "BUY" and cp >= targets[idx]) or (side == "SELL" and cp <= targets[idx])
        hit_s = (side == "BUY" and cp <= sl) or (side == "SELL" and cp >= sl)

        if hit_t:
            if idx < 3:
                new_sl = entry_stk if idx == 0 else targets[idx - 1]
                send_telegram(f"🎯 *TARGET {idx+1} HIT*: {s}\n📦 Option: {strike} {opt_type} | Lot Size: {lot_size}\n💰 Premium LTP: {opt_ltp:.2f}\n📈 Running PnL: *₹{current_pnl:,.2f}*\n🛡️ Underlying TSL: {new_sl:.2f}")
                with open(LOG_FILE, 'a') as f:
                    f.write(f"{datetime.now(IST)},{s},PARTIAL_TARGET_{idx+1}_HIT,{side},{rank},{strike},{opt_type},{lot_size},{cp},{init_opt_p},{opt_ltp},{current_pnl}\n")
                data['T_Idx'], data['SL'] = idx + 1, new_sl
                updated[s] = data
            else:
                send_telegram(f"🏁 *FINAL TARGET 4 HIT*: {s}\n📦 Option: {strike} {opt_type}\n🔥 Net Profit: *₹{current_pnl:,.2f}*")
                with open(LOG_FILE, 'a') as f: 
                    f.write(f"{datetime.now(IST)},{s},FINAL_TARGET_HIT,{side},{rank},{strike},{opt_type},{lot_size},{cp},{init_opt_p},{opt_ltp},{current_pnl}\n")
                del updated[s]
        elif hit_s:
            status_str = "TSL_HIT" if idx > 0 else "SL_HIT"
            send_telegram(f"🛑 {status_str.replace('_',' ')}: {s}\n📦 Option: {strike} {opt_type}\n💸 Realized PnL: *₹{current_pnl:,.2f}*")
            with open(LOG_FILE, 'a') as f: 
                f.write(f"{datetime.now(IST)},{s},{status_str},{side},{rank},{strike},{opt_type},{lot_size},{cp},{init_opt_p},{opt_ltp},{current_pnl}\n")
            del updated[s]
    return updated

def process_symbol(s, memory, positions):
    df15m, df5m = safe_fetch(s, "5d", "15m"), safe_fetch(s, "3d", "5m")
    daily_context = get_daily_context(s)
    
    if df15m is None or df5m is None or daily_context is None or len(df15m) < 2 or len(df5m) < 2: return None
    
    if daily_context.get("Gap") == True: return None

    trend_15m = float(df15m['ema33'].iloc[-1])
    atr_val = float(df5m['atr'].iloc[-1])
    is_ham, is_star = is_pa(df15m.iloc[-1])
    m5, m5p = df5m.iloc[-1], df5m.iloc[-2]
    
    avg_vol_20 = df5m['volume'].iloc[-21:-1].mean() + 1e-9
    if (m5['volume'] / avg_vol_20) < 1.2: return None

    near_buy = next((k for k in ["S1", "S2", "S3", "PP"] if abs(m5['low'] - daily_context[k])/daily_context[k] <= 0.0030), None)
    near_sell = next((k for k in ["R1", "R2", "R3", "PP"] if abs(m5['high'] - daily_context[k])/daily_context[k] <= 0.0030), None)

    is_l = (is_ham and m5['close'] > m5p['high'] and near_buy and m5['close'] > trend_15m)
    is_s = (is_star and m5['close'] < m5p['low'] and near_sell and m5['close'] < trend_15m)

    if (is_l or is_s) and str(df5m.index[-1]) not in memory and s not in positions:
        level, side = (near_buy if is_l else near_sell), ("BUY" if is_l else "SELL")
        entry = float(m5['close'])
        
        rank = "🔥 JACKPOT" if ((is_l and level in ["S2", "S3"]) or (is_s and level in ["R2", "R3"])) else "💎 ELITE"
        
        opt_type = "CE" if is_l else "PE"
        strike, lot_size = get_synthetic_strike_and_lot(s, entry)
        
        is_index = s in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]
        premium_multiplier = 0.006 if is_index else 0.022 
        init_opt_price = max(2.0, round(entry * premium_multiplier, 2))

        t_buffer, sl_buffer = atr_val * 1.5, atr_val
        targets = [round(entry + (t_buffer * r), 2) for r in [1, 2, 3, 4]] if is_l else [round(entry - (t_buffer * r), 2) for r in [1, 2, 3, 4]]
        sl_val = round(entry - sl_buffer, 2) if is_l else round(entry + sl_buffer, 2)

        opt_targets = [round(init_opt_price + (t_buffer * r * 0.50), 2) for r in [1, 2, 3, 4]]
        opt_sl_val = max(0.10, round(init_opt_price - (sl_buffer * 0.50), 2))
        
        # 💰 Capital Required Calculation
        capital_req = round(init_opt_price * lot_size, 2)

        msg = (f"{rank} REVERSAL SIGNAL ⚡\n"
               f"---------------------------\n"
               f"📌 Stock: {s}\n"
               f"📍 Match: {level} | {side} Underlying @ {entry:.2f}\n"
               f"---------------------------\n"
               f"📦 *Trade Option: {strike} {opt_type}*\n"
               f"🔢 True Lot Size: {lot_size}\n"
               f"💵 Est. Option Entry: *₹{init_opt_price:.2f}*\n"
               f"🏦 Capital Required: *₹{capital_req:,.2f}*\n"
               f"🛑 Option SL: ₹{opt_sl_val:.2f}\n"
               f"🎯 Option Targets: ₹{opt_targets[0]:.2f} | ₹{opt_targets[1]:.2f} | ₹{opt_targets[2]:.2f} | ₹{opt_targets[3]:.2f}")
        
        send_telegram(msg)
        return {
            "ts": str(df5m.index[-1]), "s": s, 
            "d": {
                "Entry": entry, "Targets": targets, "T_Idx": 0, "SL": sl_val, "Side": side, "Rank": rank,
                "Opt_Type": opt_type, "Strike": strike, "Lot_Size": lot_size, "Init_Opt_Price": init_opt_price
            }
        }
    return None

# =====================================================================
# 🚀 CORE ENGINE LOOP
# =====================================================================
if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    
    # 🛠️ UPDATED CSV HEADER
    csv_header = "Timestamp,Symbol,Status,Side,Rank,Strike,Opt_Type,Lot_Size,Underlying_LTP,Opt_Entry,Opt_Exit,PnL\n"
    
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f: f.write(csv_header)
    if not os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, 'w') as f: f.write(csv_header)

    print("🚀 Sniper Engine Core System Initialized. Standing by...")
    send_telegram("🤖 *Cloud Engine Online*\nBroker dependencies removed. Native API tracking loops engaged.")

    while True:
        now = datetime.now(IST)
        
        if now.weekday() >= 5:
            print(f"😴 Weekend Mode ({now.strftime('%A')}). Shutting down GitHub Runner.")
            sys.exit(0)

        if now.hour > 15 or (now.hour == 15 and now.minute >= 31):
            print("🛑 Trading day finished (3:30 PM). Closing positions and saving logs...")
            pos = load_json(POSITIONS_FILE)
            if pos: 
                print("📦 Recording official closing EOD open positions profile...")
                save_json(manage_exits(pos), POSITIONS_FILE)
            
            send_telegram("📊 *EOD Performance Report*\nSniper Engine shutting down. Daily CSV log attached.")
            send_document_telegram(LOG_FILE, caption="Daily Trading Log")
            
            print("👋 System shutting down gracefully. Handing off to GitHub Actions auto-commit.")
            sys.exit(0)
            
        if now.hour == 9 and now.minute < 45:
            print(f"⏳ Pre-market sync ({now.strftime('%H:%M:%S')}). Engine waiting for 09:45 AM boundary...")
            time.sleep(60)
            continue
            
        try:
            requests.get("https://1.1.1.1", timeout=3)
        except requests.exceptions.RequestException:
            print("🔌 Network Drop Detected! Waiting 5 seconds...")
            time.sleep(5)
            continue

        print(f"⏳ [{now.strftime('%H:%M:%S')}] Processing 5-minute candle charts...")
        mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
        pos = manage_exits(pos)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_symbol, s, mem, pos): s for s in SYMBOLS}
            for f in concurrent.futures.as_completed(futures):
                try:
                    res = f.result()
                    if res:
                        mem[res["ts"]] = True
                        pos[res["s"]] = res["d"]
                        d = res["d"]
                        # 🛠️ UPDATED INITIAL LOG ENTRY: Writes Entry Price twice (once for Entry, once for Exit) and 0.00 PnL
                        with open(LOG_FILE, 'a') as f_log:
                            f_log.write(f"{datetime.now(IST)},{res['s']},OPEN,{d['Side']},{d['Rank']},{d['Strike']},{d['Opt_Type']},{d['Lot_Size']},{d['Entry']},{d['Init_Opt_Price']},{d['Init_Opt_Price']},0.00\n")
                except Exception:
                    pass
                    
        save_json(mem, MEMORY_FILE)
        save_json(pos, POSITIONS_FILE)
        
        now = datetime.now(IST)
        remaining_seconds = 300 - ((now.minute % 5) * 60 + now.second)
        sleep_duration = remaining_seconds + 3  
        print(f"😴 Scan completed. Synced to next boundary. Sleeping for {sleep_duration} seconds...\n")
        time.sleep(sleep_duration)
