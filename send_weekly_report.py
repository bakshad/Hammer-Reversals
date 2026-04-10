import smtplib
import os
from email.message import EmailMessage
from datetime import datetime

def send_weekly_summary():
    # Configuration from GitHub Secrets
    EMAIL_USER = "bakshad@gmail.com"
    EMAIL_PASS = os.getenv('EMAIL_PASS') # Gmail App Password
    
    msg = EmailMessage()
    msg['Subject'] = f"Weekly Trading Performance & ML Data: {datetime.now().strftime('%d %b %Y')}"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg.set_content(
        "Attached is your Weekly Trade Summary and the new ML Context Log.\n\n"
        "Review the 'ml_training_data.csv' to see which trend-flips had the "
        "strongest ADX support this week."
    )

    # Attach the files if they exist
    for filename in ["weekly_trade_summary.csv", "ml_training_data.csv"]:
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                file_data = f.read()
                msg.add_attachment(
                    file_data,
                    maintype='application',
                    subtype='octet-stream',
                    filename=filename
                )

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("Weekly Report Sent Successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_weekly_summary()
