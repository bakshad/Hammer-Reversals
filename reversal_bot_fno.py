import yfinance as yf
import pandas as pd
import requests
import os
import json

# --- Configuration ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MEMORY_FILE = "alert_memory_fno_1h.json"

# Full 182 F&O Stock List (Updated April 2026)
FNO_SYMBOLS = [
    "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS", "ACC.NS", "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ADANIPOWER.NS", 
    "ALKEM.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS", "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", 
    "AUROPHARMA.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS", "BALKRISIND.NS", "BALRAMCHIN.NS", "BANDHANBNK.NS", 
    "BANKBARODA.NS", "BANKBEES.NS", "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS", "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", 
    "BPCL.NS", "BRITANNIA.NS", "BSOFT.NS", "CANBK.NS", "CANFINHOME.NS", "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", 
    "COCHINSHIP.NS", "COFORGE.NS", "COLPAL.NS", "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS", "DABUR.NS", "DALBHARAT.NS", 
    "DEEPAKNTR.NS", "DELHIVERY.NS", "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS", "EICHERMOT.NS", "ESCORTS.NS", "EXIDEIND.NS", 
    "FEDERALBNK.NS", "GAIL.NS", "GLENMARK.NS", "GMRINFRA.NS", "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", 
    "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", 
    "HINDPETRO.NS", "HINDUNILVR.NS", "HYUNDAI.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS", "IEX.NS", 
    "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IPCALAB.NS", 
    "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "L&TFH.NS", "LALPATHLAB.NS", 
    "LICHSGFIN.NS", "LT.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", 
    "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MOTILALOFS.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NAM-INDIA.NS", "NATIONALUM.NS", 
    "NAVINFLUOR.NS", "NESTLEIND.NS", "NIFTYBEES.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", "ONGC.NS", "PAGEIND.NS", "PEL.NS", "PERSISTENT.NS", 
    "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", "RECLTD.NS", 
    "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", 
    "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAELXSI.NS", "TATAMOTORS.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", 
    "TECHM.NS", "TITAN.NS", "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS", "UBL.NS", "ULTRACEMCO.NS", "UPL.NS", "VEDL.NS", "VOLTAS.NS", 
    "WIPRO.NS", "ZYDUSLIFE.NS"
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
        df = yf.download(symbol, period="1mo", interval="1h", progress=False)
        if df.empty or len(df) < 20: return memory
        last_ts = str(df.index[-1])
        if memory.get(symbol) == last_ts: return memory

        df['Body'] = abs(df['Open'] - df['Close'])
        df['Lower_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['Upper_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['Vol_SMA10'] = df['Volume'].rolling(window=10).mean()

        last = df.iloc[-1]
        vol_ok = last['Volume'] > last['Vol_SMA10']
        
        # Strict Pattern Logic
        is_hammer = (last['Lower_Shadow'] > last['Body'] * 2) and (last['Upper_Shadow'] < last['Body'] * 0.5) and (last['Close'] < last['SMA20']) and vol_ok
        is_star = (last['Upper_Shadow'] > last['Body'] * 2) and (last['Lower_Shadow'] < last['Body'] * 0.5) and (last['Close'] > last['SMA20']) and vol_ok

        if is_hammer or is_star:
            type_str = "🚀 BULLISH HAMMER" if is_hammer else "🔻 BEARISH STAR"
            entry = (last['High'] * 1.0005) if is_hammer else (last['Low'] * 0.9995)
            sl = last['Low'] if is_hammer else last['High']
            target = (entry + abs(entry-sl)*2) if is_hammer else (entry - abs(entry-sl)*2)

            msg = (f"🎯 *{type_str}*\nStock: `{symbol.split('.')[0]}`\n"
                   f"LTP: {last['Close']:.2f}\n"
                   f"Entry: {entry:.2f} | SL: {sl:.2f}\n"
                   f"Target: {target:.2f} | Pts: {abs(target-entry):.2f}")
            send_alert(msg)
            memory[symbol] = last_ts
    except: pass
    return memory

if __name__ == "__main__":
    mem = load_memory()
    for s in FNO_SYMBOLS:
        mem = get_signal(s, mem)
    save_memory(mem)
