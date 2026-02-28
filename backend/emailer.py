import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_refill_email(to_email: str, patient_username: str, alerts: list):
    """
    Sends an email notification for refill alerts.
    Falls back to printing the email in the console if SMTP is not configured.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", smtp_user)

    alert_details = "\n".join([f"- {alert['medicine']} (Refill in ~{alert['days']} days): {alert['reason']}" for alert in alerts])
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #4CAF50;">RxGenie Refill Notification 🧞‍♂️</h2>
        <p>Hello <b>{patient_username}</b>,</p>
        <p>Our predictive AI has analyzed your recent pharmacy orders and noticed you might need a refill soon to ensure uninterrupted medication.</p>
        <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0;">
          <h3 style="margin-top: 0;">Proactive Alerts:</h3>
          <ul>
            {"".join([f"<li><b>{a['medicine']}</b> (in ~{a['days']} days) - <i>{a['reason']}</i></li>" for a in alerts])}
          </ul>
        </div>
        <p>Please log in to your RxGenie dashboard to process these refills.</p>
        <p>Stay healthy,<br>The RxGenie AI Pharmacist</p>
      </body>
    </html>
    """

    # Mock Mode Fallback
    if not smtp_server or not smtp_user or not smtp_pass:
        print("\n" + "="*50)
        print("📧 [MOCK EMAIL MODE] - SMTP Credentials Missing in .env")
        print(f"To: {to_email}")
        print("Subject: RxGenie Action Required: Proactive Refill Alert")
        print("Body:")
        print(alert_details)
        print("="*50 + "\n")
        return {"status": "mock", "message": "Email printed to console (SMTP not configured)"}

    # Real SMTP Mode
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "RxGenie Action Required: Proactive Refill Alert"
    msg["From"] = f"RxGenie Pharmacist <{sender_email}>"
    msg["To"] = to_email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, to_email, msg.as_string())
        print(f"📧 [REAL EMAIL SENT] - Successfully sent to {to_email}")
        return {"status": "success", "message": "Email sent successfully via SMTP"}
    except Exception as e:
        print(f"📧 [EMAIL FAILED] - Error sending to {to_email}: {e}")
        return {"status": "error", "message": str(e)}
