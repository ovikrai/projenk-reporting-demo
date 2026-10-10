"""Preview by default; real SMTP delivery requires an explicit send command."""
import hashlib
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate, make_msgid
from pathlib import Path

from .report import currency


def compose(month, metrics, report, recipient="operations@example.com", sender="demo@example.com"):
    message = EmailMessage(policy=SMTP)
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = f"[Synthetic demo] Projenk business report · {month}"
    message.set_content(f"Hello,\n\nYour {month} synthetic business report is ready.\n\n"
        f"Net revenue: {currency(metrics['revenue'])}\n"
        f"Completed orders: {metrics['orders']}\n"
        f"Gross margin: {metrics['margin']:.1f}%\n"
        f"Average order value: {currency(metrics['aov'])}\n\n"
        "The attached HTML report includes category performance, observations and the validation methodology. "
        "Open it in a browser or print it to PDF. All figures are synthetic.\n\nProjenk Reporting\n")
    message.add_attachment(report.encode("utf-8"), maintype="text", subtype="html", filename=f"projenk-report-{month}.html")
    # Stable preview bytes for reproducible site builds.
    message.set_boundary("projenk-" + hashlib.sha256(report.encode()).hexdigest()[:24])
    return message


def send(message, output: Path, identity: str):
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("REPORT_EMAIL_FROM")
    security = os.environ.get("SMTP_SECURITY", "starttls")
    if not host or not sender:
        raise ValueError("Live delivery requires SMTP_HOST and REPORT_EMAIL_FROM")
    if security not in ("starttls", "ssl"):
        raise ValueError("SMTP_SECURITY must be starttls or ssl")
    if not message["To"] or "@example.com" in message["To"]:
        raise ValueError("Set a real recipient with --to or REPORT_EMAIL_TO")
    if "@example.com" in sender:
        raise ValueError("Set a real REPORT_EMAIL_FROM")
    message.replace_header("From", sender)
    key = hashlib.sha256((identity + str(message["To"]) + sender).encode()).hexdigest()[:24]
    receipt = output / f"delivery-{key}.json"
    if receipt.exists():
        return "already sent (delivery receipt found)"
    port = int(os.environ.get("SMTP_PORT", "465" if security == "ssl" else "587"))
    if not 1 <= port <= 65535:
        raise ValueError("SMTP_PORT must be between 1 and 65535")
    if os.environ.get("SMTP_USER") and not os.environ.get("SMTP_PASSWORD"):
        raise ValueError("SMTP_USER requires SMTP_PASSWORD")
    # Exclusive lock also prevents two concurrent runs from sending twice.
    lock = output / f"delivery-{key}.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("Delivery lock exists; inspect the previous send before retrying") from error
    os.close(descriptor)
    for header, value in [("Date", formatdate(localtime=False)), ("Message-ID", make_msgid())]:
        if header in message:
            message.replace_header(header, value)
        else:
            message[header] = value
    client_type = smtplib.SMTP_SSL if security == "ssl" else smtplib.SMTP
    kwargs = {"timeout": 30}
    if security == "ssl":
        kwargs["context"] = ssl.create_default_context()
    try:
        with client_type(host, port, **kwargs) as client:
            if security == "starttls":
                client.ehlo()
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if os.environ.get("SMTP_USER"):
                client.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            refused = client.send_message(message)
            if refused:
                raise ValueError("Some recipients were refused; inspect delivery before retrying")
        receipt.write_text(json.dumps({"status": "sent", "identity": identity}) + "\n")
    except Exception:
        # Keep an uncertain-send lock. Deleting it could cause an accidental resend.
        raise
    else:
        lock.unlink()
    return "sent"
