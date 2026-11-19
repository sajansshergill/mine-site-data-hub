"""SMTP delivery for shift reports."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from minehub_common.settings import Settings, get_settings

log = logging.getLogger("reporting.mailer")


def send_report(
    subject: str,
    body_text: str,
    attachments: list[Path] | None = None,
    settings: Settings | None = None,
) -> None:
    s = settings or get_settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s.smtp_from
    msg["To"] = s.smtp_to
    msg.set_content(body_text)

    for path in attachments or []:
        data = path.read_bytes()
        maintype, subtype = ("application", "pdf") if path.suffix.lower() == ".pdf" else ("application", "octet-stream")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)

    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
        if s.smtp_user:
            smtp.starttls()
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
    log.info("report emailed", extra={"extra": {"to": s.smtp_to, "subject": subject}})
