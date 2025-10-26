# backend/utils/email.py
from flask_mail import Message
from backend.extensions import mail

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to], body=body)
    mail.send(msg)
