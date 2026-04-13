import yfinance as yf
import pandas as pd
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# The core F&O list for 2026 (including the new April entrants)
SYMBOLS = ["^NSEI", "RELIANCE.NS", "ASHOKLEY.NS", "HYUNDAI.NS", "COCHINSHIP.NS", "ADANIPOWER.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS"] # Add full list

def get_premarket_radar():
    results = []
    # GIFT Nifty serves as the market mood indicator
    gift_nifty = yf.download("^NSEI", period="1d", interval="1m").iloc[-1]['Close']
    prev_nifty = yf.download("^NSEI", period="2d", interval="1d").iloc[-2]['Close']
    gap_nifty = ((gift_nifty - prev_nifty) / prev_nifty) * 100
    mood = "🟢 BULLISH" if gap_nifty > 0.2 else "🔴 BEARISH" if gap_nifty < -0.2 else "⚪ NEUTRAL"

    for s in SYMBOLS:
        if s == "^NSEI": continue
        try:
            # Get daily data to compare today's pre-market/opening to yesterday's close
            data = yf.download(s, period="2d", interval="1d", progress=False)
            if len(data) < 2: continue
            
            prev_close = data['Close'].iloc[-2]
            # yfinance 'info' can sometimes provide pre-market/bid prices
            info = yf.Ticker(s).info
            current_price = info.get('regularMarketPrice', prev_close)
            
            gap = ((current_price - prev_close) / prev_close) * 100
            results.append({'symbol': s.replace('.NS',''), 'gap': gap, 'price': current_price})
        except: continue

    # Sort to find Top 3 Bullish (Highest Gap) and Top 3 Bearish (Lowest Gap)
    sorted_stocks = sorted(results, key=lambda x: x['gap'], reverse=True)
    top_bulls = sorted_stocks[:3]
    top_bears = sorted_stocks[-3:]

    msg = (f"🌅 **PRE-MARKET RADAR (9:10 AM)**\n"
           f"Market Mood: {mood} (Nifty Gap: {gap_nifty:.2f}%)\n"
           f"---------------------------\n"
           f"🐂 **TOP 3 BULLISH (Gap Up):**\n")
    for b in top_bulls:
        msg += f"• {b['symbol']}: {b['gap']:.2f}% (@{b['price']:.2f})\n"
    
    msg += f"\n🐻 **TOP 3 BEARISH (Gap Down):**\n"
    for r in top_bears:
        msg += f"• {r['symbol']}: {r['gap']:.2f}% (@{r['price']:.2f})\n"
        
    msg += (f"---------------------------\n"
            f"💡 *Focus on these for the 10:15 AM candle break!*")
    
    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown")

if __name__ == "__main__":
    get_premarket_radar()
