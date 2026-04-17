import os
import requests
import pandas as pd
from nsepython import nse_preopen

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_nse_premarket():
    try:
        # 1. Market Mood (Nifty 50)
        # The key "NIFTY" gets the Nifty 50 pre-open data
        nifty_df = nse_preopen("NIFTY")
        
        # Calculate Mood
        advances = len(nifty_df[nifty_df['pChange'] > 0])
        declines = len(nifty_df[nifty_df['pChange'] < 0])
        avg_chg = nifty_df['pChange'].mean()
        mood = "🟢 BULLISH" if avg_chg > 0.2 else "🔴 BEARISH" if avg_chg < -0.2 else "⚪ NEUTRAL"

        # 2. F&O Radar
        # The key "FO" pulls all F&O stocks
        fno_df = nse_preopen("FO")
        
        # Sort to find the most "explosive" openings
        top_gainers = fno_df.sort_values(by='pChange', ascending=False).head(5)
        top_losers = fno_df.sort_values(by='pChange', ascending=True).head(5)

        # Build Reports
        gain_str = ""
        for _, row in top_gainers.iterrows():
            gain_str += f"• <b>{row['symbol']}</b>: {row['pChange']:+.2f}%\n"

        loss_str = ""
        for _, row in top_losers.iterrows():
            loss_str += f"• <b>{row['symbol']}</b>: {row['pChange']:+.2f}%\n"

        # 3. Final Report
        report = (
            f"🚀 <b>9:10 AM PREMARKET RADAR</b>\n"
            f"Mood: {mood} ({avg_chg:+.2f}%)\n"
            f"Adv/Dec: {advances}/{declines}\n\n"
            f"🔥 <b>Top F&O Gainers:</b>\n{gain_str}\n"
            f"🩸 <b>Top F&O Losers:</b>\n{loss_str}\n"
            f"<i>Action Plan: Watch for 15M EMA9 trend riding on top movers.</i>"
        )
        
        send_telegram_msg(report)

    except Exception as e:
        # Debug print so you can see the error in GitHub Action logs
        print(f"Detailed Error: {str(e)}")
        send_telegram_msg(f"❌ NSE Engine Error: {str(e)}")

if __name__ == "__main__":
    get_nse_premarket()
