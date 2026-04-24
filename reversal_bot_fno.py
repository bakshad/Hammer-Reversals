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
from nsepython import nse_quote_derivative

logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# --- CONFIGURATION ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status_scalp.json"
POSITIONS_FILE = "active_positions_scalp.json"
TRADE_LOG = "weekly_trade_summary.csv" 

# --- FULL APRIL 2026 F&O UNIVERSE ---
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
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)

def safe_fetch(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def get_oi_data(symbol):
    try:
        data = nse_quote_derivative(symbol.replace(".NS", ""))
        curr_oi = data['latestData'][0]['openInterest']
        prev_oi = data['latestData'][0]['prevCloseOI']
        return round(((curr_oi - prev_oi) / (prev_oi + 1e-9)) * 100, 2)
    except: return 0.0

def analyze_1h_context(df_1h):
    df_1h['EMA9'] = df_1h['Close'].ewm(span=9).mean()
    rh, rl = df_1h['High'].rolling(40).max(), df_1h['Low'].rolling(40).min()
    df_1h['Fib_618'] = rh - (0.618 * (rh - rl))
    curr = df_1h.iloc[-1]
    trend = "🟢 BULLISH" if curr['Close'] > curr['EMA9'] else "🔴 BEARISH"
    return trend, curr['Fib_618'], curr['EMA9']

def manage_positions(positions):
    updated = positions.copy()
    for symbol, trade in positions.items():
        df_15m = safe_fetch(symbol, period="1d", interval="15m")
        if df_15m is None: continue
        
        df_15m['EMA9'] = df_15m['Close'].ewm(span=9).mean()
        curr_price = float(df_15m['Close'].iloc[-1])
        ema_val = float(df_15m['EMA9'].iloc[-1])
        
        if not trade.get('t1_reached', False):
            is_t1 = (trade['Side'] == "🟢 BUY" and curr_price >= trade['T1']) or \
                    (trade['Side'] == "🔴 SELL" and curr_price <= trade['T1'])
            if is_t1:
                send_telegram(f"🎯 **TARGET 1 REACHED: {symbol.replace('.NS','')}**\nAction: SL moved to Cost. Riding 15m Trend 🚀")
                updated[symbol]['t1_reached'] = True

        exit_sig = (trade['Side'] == "🟢 BUY" and curr_price < ema_val) or \
                   (trade['Side'] == "🔴 SELL" and curr_price > ema_val)
        
        if exit_sig:
            pts = round(curr_price - trade['Entry'] if trade['Side'] == "🟢 BUY" else trade['Entry'] - curr_price, 2)
            pct = round((pts / trade['Entry']) * 100, 2)
            
            with open(TRADE_LOG, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), symbol, trade['Side'], trade['Entry'], curr_price, pts, pct])
            
            send_telegram(f"🏁 **TREND EXIT: {symbol.replace('.NS','')}**\nFinal Pts: {pts:+.2f} ({pct:+.2f}%)")
            del updated[symbol] 
            
    return updated

def process_symbol(symbol, memory, positions):
    df_1h = safe_fetch(symbol, "1mo", "1h")
    df_15m = safe_fetch(symbol, "5d", "15m")
    if df_1h is None or df_15m is None: return None

    macro_trend, fib_618, ema9_1h = analyze_1h_context(df_1h)
    
    df_15m['EMA9'] = df_15m['Close'].ewm(span=9).mean()
    delta = df_15m['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df_15m['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    
    curr, prev = df_15m.iloc[-1], df_15m.iloc[-2]
    ts = str(df_15m.index[-1])
    
    b = abs(curr['Open'] - curr['Close'])
    is_hammer = (min(curr['Open'], curr['Close']) - curr['Low']) > b * 1.5
    is_star = (curr['High'] - max(curr['Open'], curr['Close'])) > b * 1.5
    is_vflip_bull = (curr['Close'] > prev['High']) and (curr['Low'] < curr['EMA9']) and (curr['Close'] > curr['EMA9'])
    is_vflip_bear = (curr['Close'] < prev['Low']) and (curr['High'] > curr['EMA9']) and (curr['Close'] < curr['EMA9'])

    vol_surge = float(curr['Volume']) / (df_15m['Volume'].iloc[-5:-1].mean() + 1e-9)
    oi_change = get_oi_data(symbol)

    is_long = macro_trend == "🟢 BULLISH" and (is_hammer or is_vflip_bull) and (curr['Close'] > prev['High'])
    is_short = macro_trend == "🔴 BEARISH" and (is_star or is_vflip_bear) and (curr['Close'] < prev['Low'])

    if (is_long or is_short) and f"{symbol}_{ts}" not in memory and symbol not in positions:
        
        score = 20 
        if vol_surge > 1.5: score += 25
        if (is_long and oi_change > 1.0) or (is_short and oi_change > 1.0): score += 30
        if (is_long and curr['RSI'] < 40) or (is_short and curr['RSI'] > 60): score += 15
        if abs(curr['Close'] - fib_618) / fib_618 < 0.005: score += 10
        
        if score < 60: return None
        
        rank = "💎 ELITE" if score >= 85 else "🥇 HIGH"
        side = "🟢 BUY" if is_long else "🔴 SELL"
        pattern = "🔨 Hammer" if is_hammer else ("🌟 Star" if is_star else "🔄 V-Flip")
        
        risk = abs(curr['Close'] - (curr['Low'] if is_long else curr['High']))
        t1 = curr['Close'] + (risk * 2.5) if is_long else curr['Close'] - (risk * 2.5)
        
        msg = (f"{rank} SNIPER ({score}/100)\n"
               f"---------------------------\n"
               f"📦 **Stock:** {symbol.replace('.NS','')}\n"
               f"🔥 **Action:** {side} ({pattern})\n"
               f"🧭 **1H Trend:** {macro_trend}\n"
               f"📊 **Vol Surge:** {vol_surge:.1f}x | **OI:** {oi_change:+.2f}%\n"
               f"💰 **Entry:** {curr['Close']:.2f}\n"
               f"🎯 **Target 1:** {t1:.2f}\n"
               f"🛡️ **Trail:** 15m 9 EMA")
        
        send_telegram(msg)
        return {"symbol_ts": f"{symbol}_{ts}", "symbol": symbol, "trade_data": {"Entry": round(curr['Close'], 2), "Side": side, "T1": t1, "t1_reached": False}}
    return None

if __name__ == "__main__":
    mem, pos = load_json(MEMORY_FILE), load_json(POSITIONS_FILE)
    
    pos = manage_positions(pos)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, s, mem, pos): s for s in SYMBOLS}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                mem[res["symbol_ts"]] = True
                pos[res["symbol"]] = res["trade_data"]
                
    save_json(mem, MEMORY_FILE)
    save_json(pos, POSITIONS_FILE)
