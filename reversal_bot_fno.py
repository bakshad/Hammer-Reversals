import yfinance as yf
import pandas as pd
import requests
import os
import json
from datetime import datetime

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_status.json"

# FULL FNO LIST - UPDATED APRIL 7, 2026 (180+ Symbols)
FNO_SYMBOLS = [
    # Newest April 2026 Entrants
    "ADANIPOWER.NS", "COCHINSHIP.NS", "FORCEMOT.NS", "GODFRYPHLP.NS", 
    "HYUNDAI.NS", "MOTILALOFS.NS", "NAM-INDIA.NS", "VMM.NS",
    # Major FNO Stocks
    "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", 
    "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", 
    "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", 
    "BANKBARODA.NS", "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", "BPCL.NS", 
    "BRITANNIA.NS", "BSOFT.NS", "CANBK.NS", "CANFINHOME.NS", "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COFORGE.NS", 
    "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS", "DELHIVERY.NS", 
    "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", "FEDERALBNK.NS", "GAIL.NS", "GLENMARK.NS", 
    "GMRAIRPORT.NS", "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", 
    "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", "HINDPETRO.NS", "HINDUNILVR.NS", 
    "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFC.NS", "IDFCFIRSTB.NS", "IEX.NS", "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", 
    "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IPCALAB.NS", "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", 
    "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "L&TFH.NS", "LALPATHLAB.NS", "LICHSGFIN.NS", "LTIM.NS", "LT.NS", "LUPIN.NS", 
    "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", "MCDOWELL-N.NS", "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", 
    "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", "NESTLEIND.NS", "NIFTYBEES.NS", "NMDC.NS", "NTPC.NS", 
    "OBEROIRLTY.NS", "ONGC.NS", "PAGEIND.NS", "PEL.NS", "PERSISTENT.NS", "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS", 
    "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", "RECLTD.NS", "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", 
    "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS", "TATACONSUM.NS", 
    "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", 
    "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", "UPL.NS", "VEDL.NS", "VOLTAS.NS", "WIPRO.NS", "ZOMATO.NS", "ZYDUSLIFE.NS"
]

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=4)

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try: requests.get(url, timeout=10)
    except: pass

def get_signal(symbol, memory):
    try:
        # Woodie's Pivot Logic (Daily Data)
        d_data = yf.download(symbol, period="5d", interval="1d", progress=False)
        if d_data.empty or len(d_data) < 2: return memory
        prev = d_data.iloc[-2]
        h, l, c = prev['High'], prev['Low'], prev['Close']
        pp = (h + l + 2 * c) / 4
        r1, r2, s1, s2 = (2*pp)-l, pp+(h-l), (2*pp)-h, pp-(h-l)

        # Intraday Logic (15m Data)
        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if df.empty: return memory
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # Indicators
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['Body'] = (df['Open'] - df['Close']).abs()
        df['Min_OC'] = df[['Open', 'Close']].min(axis=1)
        df['Max_OC'] = df[['Open', 'Close']].max(axis=1)
        df['Lower_Shadow'] = df['Min_OC'] - df['Low']
        df['Upper_Shadow'] = df['High'] - df['Max_OC']
        df['Vol_SMA10'] = df['Volume'].rolling(window=10).mean()

        sig_candle = df.iloc[-2]
        conf_candle = df.iloc[-1]
        sig_ts = str(df.index[-2])
        rvol = sig_candle['Volume'] / sig_candle['Vol_SMA10'] if sig_candle['Vol_SMA10'] > 0 else 1
        
        is_hammer = (sig_candle['Lower_Shadow'] > sig_candle['Body'] * 1.5) and (sig_candle['Upper_Shadow'] < sig_candle['Body'] * 0.8)
        is_star = (sig_candle['Upper_Shadow'] > sig_candle['Body'] * 1.5) and (sig_candle['Lower_Shadow'] < sig_candle['Body'] * 0.8)

        # Woodie's Zone Check
        in_bull_zone = sig_candle['Low'] <= (pp * 1.002)
        in_bear_zone = sig_candle['High'] >= (pp * 0.998)

        # Memory Keys
        h_key, c_key, x_key = f"{symbol}_{sig_ts}_h", f"{symbol}_{sig_ts}_c", f"{symbol}_{sig_ts}_x"

        # --- HEADS-UP ---
        if ((is_hammer and in_bull_zone) or (is_star and in_bear_zone)) and h_key not in memory:
            msg = (f"👀 *PIVOT HEADS-UP: {symbol.split('.')[0]}*\n"
                   f"Zone: {'Support/PP' if is_hammer else 'Resistance/PP'}\n"
                   f"Vol: {rvol:.1f}x {'🔥' if rvol > 1.5 else ''}\n"
                   f"📢 *Watch break:* {sig_candle['High'] if is_hammer else sig_candle['Low']:.2f}")
            send_alert(msg); memory[h_key] = True

        # --- CONFIRMATION ---
        if c_key not in memory:
            risk = abs(sig_candle['High'] - sig_candle['Low'])
            if is_hammer and in_bull_zone and (conf_candle['High'] > sig_candle['High']):
                msg = (f"✅ *PIVOT BUY: {symbol.split('.')[0]}*\n"
                       f"🚀 *Entry:* {sig_candle['High']:.2f} | *SL:* {sig_candle['Low']:.2f}\n"
                       f"🎯 *T1 (PP):* {pp:.2f} | *T2 (EMA Cross):* Waiting...")
                send_alert(msg); memory[c_key] = True
            elif is_star and in_bear_zone and (conf_candle['Low'] < sig_candle['Low']):
                msg = (f"✅ *PIVOT SELL: {symbol.split('.')[0]}*\n"
                       f"🔻 *Entry:* {sig_candle['Low']:.2f} | *SL:* {sig_candle['High']:.2f}\n"
                       f"🎯 *T1 (PP):* {pp:.2f} | *T2 (EMA Cross):* Waiting...")
                send_alert(msg); memory[c_key] = True

        # --- EMA CROSSOVER (Exit/Trail) ---
        bull_x = sig_candle['EMA9'] > sig_candle['EMA20'] and df.iloc[-3]['EMA9'] <= df.iloc[-3]['EMA20']
        bear_x = sig_candle['EMA9'] < sig_candle['EMA20'] and df.iloc[-3]['EMA9'] >= df.iloc[-3]['EMA20']
        if (bull_x or bear_x) and x_key not in memory:
            msg = (f"📈 *EMA CROSSOVER: {symbol.split('.')[0]}*\n"
                   f"Type: {'Golden' if bull_x else 'Death'} Cross\n"
                   f"Action: Consider Trailing SL or Booking T2.")
            send_alert(msg); memory[x_key] = True

    except Exception: pass
    return memory

if __name__ == "__main__":
    mem = load_memory()
    for s in FNO_SYMBOLS: mem = get_signal(s, mem)
    save_memory(mem)
