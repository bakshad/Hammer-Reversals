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
    "FEDERALBNK.NS", "GAIL.NS", "GLENMARK.NS", "GNFC.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS", 
    "GUJGASLTD.NS", "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDCOPPER.NS", 
    "HINDPETRO.NS", "HINDUNILVR.NS", "HYUNDAI.NS", "ICICIBANK.NS", "ICICIGI.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS", "IEX.NS", 
    "IGL.NS", "INDHOTEL.NS", "INDIACEM.NS", "INDIAMART.NS", "INDIGO.NS", "INDUSINDBK.NS", "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IPCALAB.NS", 
    "IRCTC.NS", "ITC.NS", "JINDALSTEL.NS", "JKCEMENT.NS", "JSWSTEEL.NS", "JUBLFOOD.NS", "KOTAKBANK.NS", "L&TFH.NS", "LALPATHLAB.NS", 
    "LICHSGFIN.NS", "LTIM.NS", "LT.NS", "LUPIN.NS", "M&M.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS", 
    "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MOTILALOFS.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS", "NAM-INDIA.NS", "NATIONALUM.NS", 
    "NAVINFLUOR.NS", "NESTLEIND.NS", "NIFTYBEES.NS", "NMDC.NS", "NTPC.NS", "OBEROIRLTY.NS", "ONGC.NS", "PAGEIND.NS", "PERSISTENT.NS", 
    "PETRONET.NS", "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS", "POLYCAB.NS", "POWERGRID.NS", "PVRINOX.NS", "RAMCOCEM.NS", "RECLTD.NS", 
    "RELIANCE.NS", "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SRF.NS", "SUNPHARMA.NS", 
    "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAELXSI.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TCS.NS", 
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
        df = yf.download(symbol, period="2mo", interval="1h", progress=False)
        if df.empty or len(df) < 22: return memory
        
        # Use second-to-last candle for confirmed data
        row = df.iloc[-2]
        last_ts = str(df.index[-2])
        if memory.get(symbol) == last_ts: return memory

        # Metrics
        df['Body'] = abs(df['Open'] - df['Close'])
        df['Lower_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['Upper_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['Vol_SMA10'] = df['Volume'].rolling(window=10).mean()
        
        # RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        row = df.iloc[-2]
        vol_ok = row['Volume'] > (row['Vol_SMA10'] * 0.9) # 90% of avg volume is acceptable
        rsi_val = row['RSI']
        
        # Balanced Reversal Logic
        # Hammer: Shadow > 1.5x Body, Small Head, Price < SMA20, RSI < 45
        is_hammer = (row['Lower_Shadow'] > row['Body'] * 1.5) and \
                    (row['Upper_Shadow'] < row['Body'] * 0.8) and \
                    (row['Close'] < row['SMA20']) and vol_ok and (rsi_val < 45)
        
        # Star: Shadow > 1.5x Body, Small Tail, Price > SMA20, RSI > 55
        is_star = (row['Upper_Shadow'] > row['Body'] * 1.5) and \
                  (row['Lower_Shadow'] < row['Body'] * 0.8) and \
                  (row['Close'] > row['SMA20']) and vol_ok and (rsi_val > 55)

        if is_hammer or is_star:
            type_str = "🚀 BALANCED HAMMER" if is_hammer else "🔻 BALANCED STAR"
            entry = (row['High'] * 1.0005) if is_hammer else (row['Low'] * 0.9995)
            sl = (row['Low'] * 0.9995) if is_hammer else (row['High'] * 1.0005)
            target = (entry + abs(entry-sl)*2) if is_hammer else (entry - abs(entry-sl)*2)

            msg = (f"🎯 *{type_str}*\nStock: `{symbol.split('.')[0]}`\n"
                   f"🔥 RSI: {rsi_val:.2f}\n"
                   f"Time: {last_ts}\n"
                   f"---------------------------\n"
                   f"🟢 Entry: {entry:.2f} | 🛑 SL: {sl:.2f}\n"
                   f"🎯 Target: {target:.2f}\n"
                   f"🎁 Capture: {abs(target-entry):.2f} pts")
            send_alert(msg)
            memory[symbol] = last_ts
    except: pass
    return memory

if __name__ == "__main__":
    mem = load_memory()
    for s in FNO_SYMBOLS:
        mem = get_signal(s, mem)
    save_memory(mem)
