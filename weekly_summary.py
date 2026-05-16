import pandas as pd
import requests
import os
import json
import smtplib
import yfinance as yf
from email.message import EmailMessage
from datetime import datetime, timedelta
import pytz

# --- CONFIG ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
EMAIL_RECEIVER = os.getenv('EMAIL_RECEIVER') or EMAIL_USER
LOG_FILE = "trade_performance_log.csv"
POSITIONS_FILE = "active_positions_reversal.json"
IST = pytz.timezone('Asia/Kolkata')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def get_live_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1d", interval="1m")
        return df['Close'].iloc[-1] if not df.empty else None
    except:
        return None

def send_weekly_summary():
    # 1. Process Realized Trades
    closed_html = "<p style='color: #666;'>No trades closed this week.</p>"
    realized_pts = 0
    trade_list_tg = "No trades closed."
    
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
        df_c = pd.read_csv(LOG_FILE)
        
        if 'Date' in df_c.columns:
            # FIX: Convert CSV dates to IST and handle timezone awareness
            df_c['Date'] = pd.to_datetime(df_c['Date'], utc=True).dt.tz_convert('Asia/Kolkata')
            
            # FIX: Ensure comparison date is also IST (Aware)
            last_week = datetime.now(IST) - timedelta(days=7)
            
            week_df = df_c[df_c['Date'] >= last_week]
            
            if not week_df.empty:
                realized_pts = week_df['Points'].sum()
                closed_html = week_df.to_html(index=False, border=0, classes='table')
                
                summary_lines = []
                for _, row in week_df.iterrows():
                    icon = "✅" if row['Points'] > 0 else "❌"
                    summary_lines.append(f"{icon} {row['Symbol']}: {row['Points']:+.2f} ({row.get('Pct', 0)}%)")
                trade_list_tg = "\n".join(summary_lines)

    # 2. Process Unrealized MTM
    open_html = "<p style='color: #666;'>No active positions.</p>"
    unrealized_pts = 0
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r') as f:
            open_data = json.load(f)
        
        open_rows = []
        for s, d in open_data.items():
            cp = get_live_price(s)
            if cp:
                mtm = round(cp - d['Entry'], 2) if d['Side'] == "BUY" else round(d['Entry'] - cp, 2)
                pct = round((mtm / d['Entry']) * 100, 2)
                unrealized_pts += mtm
                open_rows.append({
                    "Symbol": s.replace('.NS',''), "Side": d['Side'], 
                    "Entry": d['Entry'], "LTP": round(cp, 2), 
                    "MTM Pts": mtm, "MTM %": f"{pct}%"
                })
        
        if open_rows:
            open_html = pd.DataFrame(open_rows).to_html(index=False, border=0, classes='table')

    total_delta = round(realized_pts + unrealized_pts, 2)
    
    # Telegram Message
    tg_msg = (f"🗓️ *WEEKLY SNIPER AUDIT*\n"
              f"---------------------------\n"
              f"{trade_list_tg}\n"
              f"---------------------------\n"
              f"💰 *Total Net:* {total_delta:+.2f} Pts\n"
              f"✅ _Realized:_ {realized_pts:+.2f}\n"
              f"⏳ _Open MTM:_ {unrealized_pts:+.2f}")
    
    # Email Content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; color: #333; }}
            .table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            .table td, .table th {{ border: 1px solid #eee; padding: 8px; text-align: left; }}
            .table th {{ background: #f4f4f4; }}
            .summary {{ background: #eef7ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid #3498db; }}
            .pos {{ color: green; font-weight: bold; }}
            .neg {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>Weekly Sniper Performance Report</h2>
        <div class="summary">
            <b>Net Performance: </b> 
            <span class="{'pos' if total_delta >= 0 else 'neg'}">{total_delta:+.2f} Points</span>
        </div>
        <h3>Closed Trades</h3> {closed_html}
        <h3>Open Positions</h3> {open_html}
    </body>
    </html>
    """

    send_telegram(tg_msg)
    
    if EMAIL_USER and EMAIL_PASS:
        msg = EmailMessage()
        msg['Subject'] = f"{'🚀' if total_delta >= 0 else '📉'} Weekly Performance: {total_delta:+.2f} Pts"
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECEIVER
        msg.add_alternative(html_content, subtype='html')
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_USER, EMAIL_PASS)
                smtp.send_message(msg)
        except Exception as e:
            print(f"Email failed: {e}")

if __name__ == "__main__":
    send_weekly_summary()
