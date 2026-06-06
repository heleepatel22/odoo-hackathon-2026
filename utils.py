import os
from flask_mail import Message
from extensions import mail

def send_email(to_email, subject, body):
    """
    Sends an email using Flask-Mail.
    Uses environment variables for credentials, otherwise falls back to a 
    mock output for demo/local purposes to avoid crashing without credentials.
    """
    smtp_server = os.environ.get('MAIL_SERVER')
    smtp_user = os.environ.get('MAIL_USERNAME')
    smtp_password = os.environ.get('MAIL_PASSWORD')

    if smtp_server and smtp_user and smtp_password:
        try:
            msg = Message(
                subject=subject,
                sender=smtp_user,
                recipients=[to_email]
            )
            msg.html = body
            mail.send(msg)
            print(f"--> [EMAIL SENT] Successfully sent email to {to_email}")
            return True
        except Exception as e:
            print(f"--> [EMAIL ERROR] Failed to send email to {to_email}: {e}")
            return False
    else:
        # Mock sending if no SMTP configured
        print("="*50)
        print(f"--> [MOCK EMAIL SENT] To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body[:100]}...")
        print("="*50)
        return True
