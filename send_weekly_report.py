import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

def send_email():
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS") # Use Gmail App Password
    receiver_email = "bakshad@gmail.com"
    subject = f"Weekly F&O Reversal Summary - {os.getenv('GITHUB_RUN_ID')}"
    body = "Please find the attached weekly summary of F&O reversal signals."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    filename = "weekly_trade_summary.csv"
    if os.path.exists(filename):
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")
    else:
        print("CSV file not found. Skipping email.")

if __name__ == "__main__":
    send_email()
