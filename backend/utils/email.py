from flask_mail import Message
from backend.extensions import mail
from flask import current_app

def send_email(to, subject, body):
    """
    Send an email using Flask-Mail.
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            sender=current_app.config.get("MAIL_DEFAULT_SENDER", "abednegokaume@gmail.com"),
            body=body
        )
        mail.send(msg)
        current_app.logger.info(f"Email sent successfully to {to}")
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {e}")
        raise
