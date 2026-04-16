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
        # 1. Market Mood Analysis
        # Note: We download 3 days to ensure we have at least 2 full sessions
        nifty_data = yf.download("^NSEI", period="3d", interval="1d", progress=False)
        
        # FIX: Flatten MultiIndex columns if they exist (Common in 2026 yfinance)
        if isinstance(nifty_data.columns, pd.MultiIndex):
            nifty_data.columns = nifty_data.columns.get_level_values(0)

        prev_close = nifty_data['Close'].iloc[-2]
        curr_price = nifty_data['Close'].iloc[-1]
        
        # Ensure we are comparing single float values, not Series
        gap_nifty = float(((curr_price - prev_close) / prev_close) * 100)
        
        # This comparison will now work because gap_nifty is a float
        mood = "🟢 BULLISH" if gap_nifty > 0.2 else "🔴 BEARISH" if gap_nifty < -0.2 else "⚪ NEUTRAL"
        
        # 2. Woodie's Pivot for Nifty
        high, low, close = nifty_data['High'].iloc[-2], nifty_data['Low'].iloc[-2], nifty_data['Close'].iloc[-2]
        pp = (high + low + 2 * close) / 4
        r1 = (2 * pp) - low
        s1 = (2 * pp) - high

        # 3. F&O Radar
        radar_stocks = ["ICICIBANK.NS", "WIPRO.NS", "SBIN.NS"]
        stock_report = ""
        
        for symbol in radar_stocks:
            s_data = yf.download(symbol, period="2d", interval="1h", progress=False)
            if not s_data.empty:
                if isinstance(s_data.columns, pd.MultiIndex):
                    s_data.columns = s_data.columns.get_level_values(0)
                
                s_prev = s_data['Close'].iloc[-2]
                s_curr = s_data['Close'].iloc[-1]
                chg = float(((s_curr - s_prev) / s_prev) * 100)
                stock_report += f"• {symbol.replace('.NS','')}: {chg:+.2f}% IEP\n"

        # 4. Final Report
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
