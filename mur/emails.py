import smtplib
from email.message import EmailMessage

from . import config


def send(to, subject, body, html=None):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = config.FROM_EMAIL
    msg["To"] = to
    msg["Bcc"] = config.FROM_EMAIL
    if html:
        msg.add_alternative(html, subtype="html")
    if not config.SEND_EMAILS:
        return print("Sending email", str(msg))
    try:
        server = smtplib.SMTP_SSL(config.SMTP_HOST)
        server.login(config.SMTP_LOGIN, config.SMTP_PASSWORD)
        server.send_message(msg)
    except smtplib.SMTPException as err:
        print(err)
        raise RuntimeError
    finally:
        server.quit()
