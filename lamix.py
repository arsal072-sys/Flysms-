#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NumberPanel OTP Bot
Mode: FORWARD LAST 3 OTP ONLY
Group: -1003405109562
"""

import time
import json
import re
import requests
from datetime import datetime

# ================== CONFIG ==================
BASE_URL = "http://51.89.99.105/NumberPanel"
API_PATH = "/client/res/data_smscdr.php"

PHPSESSID = "PASTE_YOUR_PHPSESSID_HERE"   # 🔐 fresh session
BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"   # 🤖 bot token

CHAT_ID = "-1003405109562"                # ✅ your GC
CHECK_INTERVAL = 10                       # seconds
STATE_FILE = "last_seen.json"

# ================== HEADERS ==================
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0",
    "Referer": f"{BASE_URL}/client/SMSDashboard",
}

# ================== SESSION ==================
session = requests.Session()
session.cookies.set("PHPSESSID", PHPSESSID)

# ================== HELPERS ==================
def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {"sent_keys": []}

def save_state(state):
    json.dump(state, open(STATE_FILE, "w"))

def extract_otp(text):
    """
    Supports:
    123456
    589-837
    589 837
    """
    if not text:
        return None
    m = re.search(r"\b(\d{3,4}[-\s]?\d{3,4})\b", text)
    return m.group(1) if m else None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    r = requests.post(url, json=payload, timeout=10)
    print("📤 Telegram:", r.status_code)

# ================== START ==================
print("🚀 NumberPanel OTP Bot Started")
print("⚡ Mode: LAST 3 OTP ONLY")
print("📢 Group:", CHAT_ID)

state = load_state()
sent_keys = state.get("sent_keys", [])

while True:
    try:
        params = {
            "fdate1": "2025-01-01 00:00:00",
            "fdate2": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iDisplayStart": 0,
            "iDisplayLength": 3,  # 🔥 LAST 3 ONLY
            "sEcho": 1,
            "_": int(time.time() * 1000),
        }

        r = session.get(
            BASE_URL + API_PATH,
            headers=HEADERS,
            params=params,
            timeout=10
        )

        if r.status_code != 200:
            print("❌ API error:", r.status_code)
            time.sleep(CHECK_INTERVAL)
            continue

        data = r.json()
        rows = data.get("aaData", [])

        if not rows:
            time.sleep(CHECK_INTERVAL)
            continue

        # 🔁 Process from OLDEST → NEWEST (clean order)
        rows.reverse()

        for row in rows:
            ts, pool, number, service, message = row[:5]
            key = f"{number}_{ts}"

            if key in sent_keys:
                continue

            otp = extract_otp(message)
            print("🧾 SMS:", message, "| OTP:", otp)

            if otp:
                text = (
                    f"🔐 *NEW OTP RECEIVED*\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"🕒 `{ts}`\n"
                    f"📞 `{number}`\n"
                    f"📲 `{service}`\n"
                    f"🔢 *OTP:* `{otp}`\n"
                )
                send_telegram(text)

            sent_keys.append(key)

        # 🔒 keep memory small (last 10 only)
        sent_keys = sent_keys[-10:]
        save_state({"sent_keys": sent_keys})

    except Exception as e:
        print("💥 ERROR:", e)

    time.sleep(CHECK_INTERVAL)
