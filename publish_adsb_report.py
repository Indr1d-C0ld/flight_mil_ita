#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_adsb_report.py — genera post Hugo con tabella eventi MIL

Novità:
- Conversione CSV → DB automatica con deduplica.
- Tabella con chiave primaria (first_seen_utc + hex).
- Titolo formattato: "Report voli militari in ITALIA dd.mm.yy".
- Filtri periodici (--period daily|weekly|monthly).
- Notifica Telegram al termine con link al nuovo post.
"""

import sqlite3
import os
from datetime import datetime, timedelta, date
import argparse
import subprocess
import csv
import requests

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

DB_FILE = "/home/pi/flight_mil_ita/events.db"
CSV_FILE = "/home/pi/flight_mil_ita/mil.csv"
TABLE = "events"
BLOG_PATH = "/home/pi/blog"
POSTS_DIR = os.path.join(BLOG_PATH, "content/posts")
BASE_URL = "https://timrouter.dns.army/blog/posts"

# ---------------------------
# Config Telegram (fallback se non in env)
# ---------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_telegram_message(text: str):
    """Invia un messaggio Telegram al canale configurato"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Telegram non configurato, skip notifica.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": False}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            print("[INFO] Notifica Telegram inviata con successo.")
        else:
            print(f"[ERR] Telegram API response: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[ERR] Errore invio Telegram: {e}")

# ---------------------------
# DB helpers
# ---------------------------
def connect_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            first_seen_utc TEXT,
            hex TEXT,
            callsign TEXT,
            reg TEXT,
            model_t TEXT,
            lat REAL,
            lon REAL,
            alt_ft INTEGER,
            gs_kt REAL,
            squawk TEXT,
            ground TEXT,
            PRIMARY KEY (first_seen_utc, hex)
        )
    """)
    conn.commit()

def csv_to_db(csv_path: str, conn):
    if not os.path.isfile(csv_path):
        print(f"[WARN] CSV {csv_path} non trovato, skip import.")
        return
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            print(f"[INFO] CSV vuoto, nessun import.")
            return
        cur = conn.cursor()
        for r in rows:
            cur.execute(f"""
                INSERT OR IGNORE INTO {TABLE} (
                    first_seen_utc, hex, callsign, reg, model_t,
                    lat, lon, alt_ft, gs_kt, squawk, ground
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                r.get("first_seen_utc"),
                r.get("hex"),
                r.get("callsign"),
                r.get("reg"),
                r.get("model_t"),
                r.get("lat"),
                r.get("lon"),
                r.get("alt_ft"),
                r.get("gs_kt"),
                r.get("squawk"),
                r.get("ground"),
            ))
        conn.commit()
    print(f"[INFO] Importati {len(rows)} record (deduplicati con OR IGNORE).")

def query_events_by_day_range(conn, start_day: str, end_day: str):
    q = f"""
        SELECT * FROM {TABLE}
        WHERE substr(first_seen_utc,1,10) BETWEEN ? AND ?
        ORDER BY datetime(first_seen_utc) ASC
    """
    return conn.execute(q, (start_day, end_day)).fetchall()

# ---------------------------
# Export helpers
# ---------------------------
def to_markdown(rows):
    if not rows:
        return "_Nessun evento registrato in questo periodo._"
    headers = rows[0].keys()
    out = "| " + " | ".join(headers) + " |\n"
    out += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for r in rows:
        out += "| " + " | ".join(str(r[h]) if r[h] is not None else "" for h in headers) + " |\n"
    return out

def format_front_matter(title: str, pub_dt_local: datetime, tags=None):
    if tags is None:
        tags = ["ads-b", "report", "militari"]
    if pub_dt_local.tzinfo is not None:
        iso_ts = pub_dt_local.isoformat(timespec="seconds")
    else:
        iso_ts = pub_dt_local.strftime("%Y-%m-%dT%H:%M:%S")
    tags_yaml = "[" + ",".join(f"\"{t}\"" for t in tags) + "]"
    return f"""---
title: "{title}"
date: {iso_ts}
tags: {tags_yaml}
---
"""

def write_post(pub_date_str: str, slug: str, title: str, body_md: str):
    year = pub_date_str[:4]
    post_dir = os.path.join(POSTS_DIR, year)
    os.makedirs(post_dir, exist_ok=True)
    filename = f"{pub_date_str}-{slug}.md"
    filepath = os.path.join(post_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body_md)
    return filepath, filename

# ---------------------------
# Period helpers
# ---------------------------
def today_local_eu_rome():
    if ZoneInfo:
        return datetime.now(ZoneInfo("Europe/Rome"))
    return datetime.now()

def get_period_bounds(period: str, now_local: datetime):
    today = now_local.date()
    if period == "daily":
        start_day = end_day = today
        label = today.strftime("%d.%m.%y")
    elif period == "weekly":
        start_day = today - timedelta(days=today.weekday())
        end_day = start_day + timedelta(days=6)
        label = f"{start_day.strftime('%d.%m.%y')} → {end_day.strftime('%d.%m.%y')}"
    elif period == "monthly":
        start_day = today.replace(day=1)
        if start_day.month == 12:
            next_month = date(start_day.year + 1, 1, 1)
        else:
            next_month = date(start_day.year, start_day.month + 1, 1)
        end_day = next_month - timedelta(days=1)
        label = start_day.strftime("%m.%y")
    else:
        start_day = end_day = today
        label = today.strftime("%d.%m.%y")
    return start_day.strftime("%Y-%m-%d"), end_day.strftime("%Y-%m-%d"), label

# ---------------------------
# Main
# ---------------------------
def main():
    ap = argparse.ArgumentParser(description="Pubblica report ADS-B militari come post Hugo")
    ap.add_argument("--period", choices=["daily", "weekly", "monthly"], default="daily")
    ap.add_argument("--slug", default="monitor-mil-report")
    ap.add_argument("--limit", type=int, default=1000)
    args = ap.parse_args()

    now_local = today_local_eu_rome()
    pub_date_str = now_local.strftime("%Y-%m-%d")

    start_day_str, end_day_str, label = get_period_bounds(args.period, now_local)

    conn = connect_db()
    init_db(conn)
    csv_to_db(CSV_FILE, conn)
    rows = query_events_by_day_range(conn, start_day_str, end_day_str)

    title = f"Report voli militari in ITALIA {label}"
    body_md = format_front_matter(title, now_local) + "\n" + to_markdown(rows)

    # Scrittura post
    filepath, filename = write_post(pub_date_str, args.slug, title, body_md)

    # Rigenera sito Hugo
    subprocess.run(["hugo", "-s", BLOG_PATH], check=True)

    # Costruisci link pubblico
    post_url = f"{BASE_URL}/{filename.replace('.md','')}/"
    msg = f"🛩️ Nuovo report pubblicato:\n{title}\n{post_url}"

    # Notifica Telegram
    send_telegram_message(msg)

if __name__ == "__main__":
    main()
