"""E-post och notifieringar."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path


def send_email_report(
    subject: str,
    body_text: str,
    body_html: str | None = None,
    attachment_path: Path | None = None,
) -> bool:
    """Skicka rapport via e-post.

    Args:
        subject: Ämnesrad
        body_text: Brödtext (plain text)
        body_html: Brödtext (HTML, valfritt)
        attachment_path: Bifogad fil (valfritt)

    Returns:
        True om lyckad, False annars
    """
    smtp_host = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    smtp_user = os.getenv("EMAIL_SMTP_USER", "")
    smtp_password = os.getenv("EMAIL_SMTP_PASSWORD", "")
    email_to = os.getenv("EMAIL_TO", "")

    if not all([smtp_user, smtp_password, email_to]):
        print("E-post ej konfigurerad (EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD, EMAIL_TO)")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = email_to

        # Plain text
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        # HTML (om tillgänglig)
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        # Bifogad fil
        if attachment_path and attachment_path.exists():
            from email.mime.base import MIMEBase
            from email import encoders

            with open(attachment_path, "rb") as f:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={attachment_path.name}",
            )
            msg.attach(attachment)

        # Skicka
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, email_to, msg.as_string())

        print(f"Rapport skickad till {email_to}")
        return True

    except Exception as e:
        print(f"Kunde inte skicka e-post: {e}")
        return False


def send_daily_report_email(report: dict) -> bool:
    """Skicka daglig rapport via e-post.

    Args:
        report: Rapportdata från DailyReport.generate()

    Returns:
        True om lyckad
    """
    portfolio = report["portfolio"]

    subject = f"Portföljrapport {report['date']} | {portfolio['total_value']:,.0f} SEK ({portfolio['total_return_pct']:+.1f}%)"

    body_text = f"""Daglig Portföljrapport - {report['date']}

SAMMANFATTNING
Portföljvärde: {portfolio['total_value']:,.0f} SEK
Kassa: {portfolio['cash']:,.0f} SEK
Total avkastning: {portfolio['total_return_pct']:+.1f}%
Benchmark: {report['benchmark']['daily_change_pct']:+.1f}%

POSITIONER
"""
    for pos in report["positions"]:
        body_text += f"- {pos['ticker']}: {pos['market_value']:,.0f} SEK ({pos['unrealized_pnl_pct']:+.1f}%)\n"

    if report["alerts"]:
        body_text += "\nALERTS\n"
        for alert in report["alerts"]:
            body_text += f"- {alert['message']}\n"

    body_text += f"\nPortföljhälsa: {report['health'].upper()}"

    return send_email_report(subject, body_text)


def send_smart_report_email(report: dict) -> bool:
    """Skicka smart rapport med rekommendationer via e-post.

    Args:
        report: Rapportdata från generate_smart_daily_report()

    Returns:
        True om lyckad
    """
    from .smart_report import format_smart_email

    subject, body = format_smart_email(report)
    return send_email_report(subject, body)
