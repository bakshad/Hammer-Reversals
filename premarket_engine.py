import yfinance as yf
import pandas as pd
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}&parse_mode=Markdown"
    requests.get(url)

def get_premarket_radar():
    try:
        # 1. Market Mood Analysis (Nifty IEP vs Prev Close)
        nifty = yf.download("^NSEI", period="2d", interval="1d", progress=False)
        # FIX: Added .iloc[-1] to prevent "truth value of a Series is ambiguous" error
        prev_close = nifty['Close'].iloc[-2]
        curr_price = nifty['Close'].iloc[-1]
        gap_nifty = ((curr_price - prev_close) / prev_close) * 100
        
        mood = "🟢 BULLISH" if gap_nifty > 0.2 else "🔴 BEARISH" if gap_nifty < -0.2 else "⚪ NEUTRAL"
        
        # 2. Woodie's Pivot for Nifty (Support/Resistance)
        high, low, close = nifty['High'].iloc[-2], nifty['Low'].iloc[-2], nifty['Close'].iloc[-2]
        pp = (high + low + 2 * close) / 4
        r1 = (2 * pp) - low
        s1 = (2 * pp) - high

        # 3. F&O Radar (Simplified high-potential scan)
        # Using ICICIBANK, WIPRO, and SBIN as proxies for sector strength today
        radar_stocks = ["ICICIBANK.NS", "WIPRO.NS", "SBIN.NS"]
        stock_report = ""
        
        for symbol in radar_stocks:
            data = yf.download(symbol, period="2d", interval="1h", progress=False)
            if not data.empty:
                chg = ((data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100
                stock_report += f"• {symbol.replace('.NS','')}: {chg:+.2f}% IEP\n"

        # 4. Final Report Assembly
        report = (
            f"🚀 *9:10 AM PREMARKET RADAR*\n"
            f"Date: April 16, 2026\n\n"
            f"Mood: {mood} ({gap_nifty:+.2f}%)\n"
            f"Nifty Pivot: {pp:.2f}\n"
            f"Levels: S1: {s1:.2f} | R1: {r1:.2f}\n\n"
            f"*F&O IEP Watch:*\n{stock_report}\n"
            f"*Action Plan:*\n"
            f"Focus on Woodie's PP support. Ride trend with 15M EMA9. "
            f"Elite signals only if Vol Delta > 1.5x."
        )
        
        send_telegram_msg(report)

    except Exception as e:
        send_telegram_msg(f"❌ Premarket Engine Error: {str(e)}")

if __name__ == "__main__":
    get_premarket_radar()
