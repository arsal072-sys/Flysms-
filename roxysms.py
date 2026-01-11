#!/usr/bin/env python3
import requests
import time
import re
import logging
import json
import os
from datetime import datetime

# ================= CONFIG =================

AJAX_URL = "http://www.roxysms.net/agent/res/data_smscdr.php"

# 🔐 ENV VARIABLES (Heroku Config Vars)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PHPSESSID = os.getenv("PHPSESSID")

if not BOT_TOKEN or not CHAT_ID or not PHPSESSID:
    raise RuntimeError("Missing required ENV vars: BOT_TOKEN / CHAT_ID / PHPSESSID")

COOKIES = {
    "PHPSESSID": PHPSESSID
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

CHECK_INTERVAL = 5  # seconds
STATE_FILE = "state.json"

SUPPORT_URL = "https://t.me/botcasx"
NUMBERS_URL = "https://t.me/CyberOTPCore"

# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("roxysms.log")
    ]
)

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)

# ================= STATE =================

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return datetime.strptime(data["last_seen_time"], "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None
    return None


def save_state(dt):
    with open(STATE_FILE, "w") as f:
        json.dump(
            {"last_seen_time": dt.strftime("%Y-%m-%d %H:%M:%S")},
            f
        )


last_seen_time = load_state()

# ================= HELPERS =================

def extract_otp(text):
    if not text:
        return "N/A"
    m = re.search(r"\b(\d{4,8})\b", text)
    return m.group(1) if m else "N/A"


def build_params(limit=5):
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "",
        "fclient": "",
        "fnum": "",
        "fcli": "",
        "fgdate": "",
        "fgmonth": "",
        "fgrange": "",
        "fgclient": "",
        "fgnumber": "",
        "fgcli": "",
        "fg": 0,
        "sEcho": 1,
        "iColumns": 7,
        "iDisplayStart": 0,
        "iDisplayLength": limit,
        "iSortCol_0": 0,
        "sSortDir_0": "desc",
        "iSortingCols": 1
    }


def format_message(row):
    date = row[0]
    raw_route = str(row[1]) if row[1] else "Unknown"
    number = str(row[2]) if row[2] else "N/A"
    raw_message = row[4]

    # ✅ Country only
    country = raw_route.split("-")[0].split("_")[0]
    message = raw_message.strip() if raw_message else "Message not provided"

    if not number.startswith("+"):
        number = "+" + number

    otp = extract_otp(message)

    return (
        "📩 *LIVE SMS RECEIVED*\n\n"
        f"📞 *Number:* `{number}`\n"
        f"🔢 *OTP:* 🔥 `{otp}` 🔥\n"
        f"🌍 *Country:* {country}\n"
        f"🕒 *Time:* {date}\n\n"
        f"💬 *SMS:*\n{message}\n\n"
        "⚡ *CYBER CORE OTP*"
    )


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🆘 Support", "url": SUPPORT_URL},
                    {"text": "📲 Numbers", "url": NUMBERS_URL}
                ]
            ]
        }
    }
    r = requests.post(url, json=payload, timeout=15)
    if not r.ok:
        logging.error("Telegram Error: %s", r.text)

# ================= CORE (ONLY LIVE) =================

def fetch_latest_sms():
    global last_seen_time

    r = session.get(AJAX_URL, params=build_params(), timeout=20)
    data = r.json()

    rows = data.get("aaData", [])
    if not rows or not isinstance(rows[0], list):
        return

    for row in rows:
        try:
            sms_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        if last_seen_time is None:
            last_seen_time = sms_time
            save_state(last_seen_time)
            logging.info("LIVE baseline set: %s", last_seen_time)
            return

        if sms_time > last_seen_time:
            last_seen_time = sms_time
            save_state(last_seen_time)
            send_telegram(format_message(row))
            logging.info("LIVE OTP sent")
            return

# ================= LOOP =================

logging.info("🚀 RoxySMS Bot Started (ONLY LIVE MODE)")

while True:
    try:
        fetch_latest_sms()
    except Exception:
        logging.exception("ERROR")
    time.sleep(CHECK_INTERVAL)
