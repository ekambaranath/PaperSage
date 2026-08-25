"""Send the digest via Gmail SMTP using an app password."""
from __future__ import annotations

import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import Config

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def send_digest(
    cfg: Config,
    subject: str,
    html_body: str,
    markdown_report: str,
    pdf_bytes: bytes | None,
) -> None:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"PaperSage <{cfg.gmail_address}>"
    msg["To"] = cfg.recipient_email

    # HTML (with a minimal plain-text alternative) as the body.
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText("Your PaperSage digest is attached. View in an HTML-capable client.", "plain"))
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

    md_part = MIMEApplication(markdown_report.encode("utf-8"), _subtype="markdown")
    md_part.add_header(
        "Content-Disposition", "attachment", filename=f"PaperSage_{stamp}.md"
    )
    msg.attach(md_part)

    if pdf_bytes:
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition", "attachment", filename=f"PaperSage_{stamp}.pdf"
        )
        msg.attach(pdf_part)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=60) as server:
        server.login(cfg.gmail_address, cfg.gmail_app_password)
        server.sendmail(cfg.gmail_address, [cfg.recipient_email], msg.as_string())
    print(f"[email] digest sent to {cfg.recipient_email}")
