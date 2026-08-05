"""Optional in-process digest scheduler. Only runs when SMTP env vars are set."""

from __future__ import annotations

import smtplib
import sqlite3
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from apscheduler.schedulers.background import BackgroundScheduler

from ledger.config import Settings
from ledger.digest.render import render_digest
from ledger.store.repository import EventRepository


def send_digest(conn: sqlite3.Connection, settings: Settings, since: datetime, label: str) -> None:
    if not (settings.smtp_host and settings.digest_to):
        return

    repo = EventRepository(conn)
    events = [e for e in repo.query(limit=200) if e.ts >= since]
    text_body, html_body = render_digest(events, label)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Agent Activity Ledger — {label}"
    msg["From"] = settings.smtp_user or "ledger@localhost"
    msg["To"] = settings.digest_to
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def start_scheduler(conn: sqlite3.Connection, settings: Settings) -> BackgroundScheduler | None:
    if not (settings.smtp_host and settings.digest_to):
        return None

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: send_digest(conn, settings, datetime.now(UTC) - timedelta(days=1), "Daily digest"),
        "cron",
        hour=8,
        id="daily-digest",
    )
    scheduler.add_job(
        lambda: send_digest(conn, settings, datetime.now(UTC) - timedelta(days=7), "Weekly digest"),
        "cron",
        day_of_week="mon",
        hour=8,
        id="weekly-digest",
    )
    scheduler.start()
    return scheduler
