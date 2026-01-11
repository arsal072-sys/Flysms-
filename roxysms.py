import os
import requests
import time
import re
import json
import logging
from datetime import datetime
from pathlib import Path

# ================= CONFIG =================

AJAX_URL = "http://www.roxysms.net/agent/res/data_smscdr.php"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PHPSESSID = os.getenv("PHPSESSID")

CHECK_INTERVAL = 12
STATE_FILE = "state.json"

SUPPORT_URL = "https://t.me/botcasx"
NUMBERS_URL = "https://t.me/CyberOTPCore"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

session = requests.Session()
session.headers.update(HEADERS)

if PHPSESSID:
    session.cookies.set("PHPSESSID", PHPSESSID)

last_seen_time = None
cookie_alert_sent = False

# ============ STATE =======================

def load_state():
    global last_seen_time
    if Path(STATE_FILE).exists():
        try:
            data = json.loads(Path(STATE_FILE).read_text())
            last_seen_time = datetime.fromisoformat(data["last_seen"])
        except Exception:
            pass

def save_state(ts):
    Path(STATE_FILE).write_text(json.dumps({"last_seen": ts.isoformat()}))

# ============ HELPERS =====================

def extract_otp(text):
    m = re.search(r"\b(\d{4,8})\b", text or "")
    return m.group(1) if m else "N/A"

def extract_country(route):
    if not route:
        return "Unknown"
    return route.split("-")[0].strip()

def build_params():
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "",
        "fclient": "",
        "fnum": "",
        "fcli": "",
        "fg": 0,
        "iDisplayStart": 0,
        "iDisplayLength": 10,
        "sEcho": 1,
        "iSortCol_0": 0,
        "sSortDir_0": "desc",
    }

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        return

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
    requests.post(url, json=payload, timeout=10)

def notify_cookie_expired():
    global cookie_alert_sent
    if cookie_alert_sent:
        return
    cookie_alert_sent = True
    send_telegram(
        "⚠️ *COOKIE EXPIRED*\n\n"
        "RoxySMS session logout ho gaya hai.\n"
        "Heroku config vars me naya `PHPSESSID` set karo.\n\n"
        "⚡ *CYBER CORE OTP*"
    )

def format_message(row):
    date = row[0]
    route_raw = row[1]
    number = row[2]
    message = row[4]

    if not number.startswith("+"):
        number = "+" + number

    otp = extract_otp(message)
    country = extract_country(route_raw)

    return (
        "📩 *NEW SMS RECEIVED*\n\n"
        f"📞 *Number:* `{number}`\n"
        f"🔢 *OTP:* 🔥 `{otp}` 🔥\n"
        f"🌍 *Country:* {country}\n"
        f"🕒 *Time:* {date}\n\n"
        f"💬 *SMS:*\n{message}\n\n"
        "⚡ *CYBER CORE OTP*"
    )

# ============ CORE ========================

def fetch_latest_sms():
    global last_seen_time

    try:
        r = session.get(AJAX_URL, params=build_params(), timeout=25)
    except requests.exceptions.RequestException:
        return

    if r.status_code in (401, 403):
        notify_cookie_expired()
        return

    if "login" in r.text.lower():
        notify_cookie_expired()
        return

    try:
        data = r.json()
    except Exception:
        return

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

# ============ START =======================

load_state()
logging.info("🚀 RoxySMS Bot Started (ONLY LIVE MODE – ENV)")

while True:
    try:
        fetch_latest_sms()
    except Exception:
        logging.exception("ERROR")
    time.sleep(CHECK_INTERVAL)
