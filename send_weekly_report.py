import smtplib, os, pandas as pd
from email.message import EmailMessage
from datetime import datetime

def send_weekly_summary():
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASS')
    
    # Process Realized
    closed_html = "<p>No trades closed this week.</p>"
    realized_pts = 0
    if os.path.exists("weekly_trade_summary.csv") and os.path.getsize("weekly_trade_summary.csv") > 0:
        df_c = pd.read_csv("weekly_trade_summary.csv")
        realized_pts = df_c['Points'].sum()
        closed_html = df_c.to_html(index=False, border=0, classes='table')

    # Process Open
    open_html = "<p>No active positions at close.</p>"
    unrealized_pts = 0
    if os.path.exists("open_positions_snapshot.csv") and os.path.getsize("open_positions_snapshot.csv") > 0:
        df_o = pd.read_csv("open_positions_snapshot.csv")
        unrealized_pts = df_o['MTM_Pts'].sum()
        open_html = df_o.to_html(index=False, border=0, classes='table')

    msg = EmailMessage()
    msg['Subject'] = f"🚀 F&O Weekly Summary: {realized_pts + unrealized_pts:+.2f} Total Points"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    
    html_content = f"""
    <html>
    <head>
        <style>
            .table {{ font-family: Arial; border-collapse: collapse; width: 100%; font-size: 12px; margin-bottom: 20px; }}
            .table td, .table th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .table th {{ background-color: #2c3e50; color: white; }}
            .box {{ background-color: #f4f7f6; padding: 15px; border-left: 5px solid #2980b9; margin-bottom: 20px; }}
            .pos {{ color: #27ae60; font-weight: bold; }}
            .neg {{ color: #e74c3c; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>Weekly Trading Performance Review</h2>
        <div class="box">
            <b>Realized Points:</b> <span class="{'pos' if realized_pts >= 0 else 'neg'}">{realized_pts:+.2f}</span><br>
            <b>Open MTM Points:</b> <span class="{'pos' if unrealized_pts >= 0 else 'neg'}">{unrealized_pts:+.2f}</span><br>
            <hr>
            <b>Net Portfolio Delta:</b> {realized_pts + unrealized_pts:+.2f} Points
        </div>
        <h4>📊 Closed Trades (Realized This Week)</h4>
        {closed_html}
        <h4>🕒 Open Positions (Mark-to-Market Snapshot)</h4>
        {open_html}
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype='html')

    for f_name in ["weekly_trade_summary.csv", "open_positions_snapshot.csv"]:
        if os.path.exists(f_name) and os.path.getsize(f_name) > 0:
            with open(f_name, 'rb') as f:
                msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename=f_name)

    # Added try/except block for better error logging in GitHub Actions
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print(f"✅ Weekly report sent successfully. Net Delta: {realized_pts + unrealized_pts:+.2f} Points")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    send_weekly_summary()
