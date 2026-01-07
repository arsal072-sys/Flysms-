#!/usr/bin/env python3  
# -*- coding: utf-8 -*-  
  
"""  
INTS OTP Forwarder - LIVE ONLY VERSION  
• Old OTP forward ❌  
• Only LIVE / NEW OTP forward ✅  
• Restart-safe (no old spam)  
• Premium Telegram style  
"""  
  
import time  
import logging  
import re  
from hashlib import sha1  
from datetime import datetime, timezone  
  
import requests  
  
# ================= CONFIG =================  
BASE_URL = "http://139.99.208.63/ints"  
DATA_URL = "http://139.99.208.63/ints/agent/res/data_smscdr.php"  
  
BOT_TOKEN = "7448362382:AAGzYcF4XH5cAOIOsrvJ6E9MXqjnmOdKs2o"  
CHAT_IDS = ["-1003140739791"]  
  
PHPSESSID = "07eaadf9f19b9135f4b350da129af35f"  
POLL_INTERVAL = 15  # seconds  
  
# ================= LOGGING =================  
logging.basicConfig(  
    level=logging.INFO,  
    format="%(asctime)s - %(levelname)s - %(message)s",  
)  
log = logging.getLogger("ints-otp-bot")  
  
# ================= SESSION =================  
session = requests.Session()  
session.headers.update({  
    "User-Agent": "Mozilla/5.0",  
    "Accept": "application/json, text/javascript, */*; q=0.01",  
    "X-Requested-With": "XMLHttpRequest",  
})  
session.cookies.set("PHPSESSID", PHPSESSID)  
  
# ================= OTP PATTERNS =================  
OTP_PATTERNS = [  
    r"\b\d{6}\b",  
    r"\b\d{5}\b",  
    r"\b\d{3}-\d{3}\b",  
    r"\b\d{3}\s\d{3}\b",  
]  
  
# in-memory dedup  
seen_messages = set()  
initialized = False  # 🔒 first run lock  
  
# ================= TELEGRAM SEND =================  
def send_telegram(text: str):  
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"  
    for cid in CHAT_IDS:  
        requests.post(  
            url,  
            data={  
                "chat_id": cid,  
                "text": text,  
                "parse_mode": "Markdown",  
                "disable_web_page_preview": True,  
            },  
            timeout=10,  
        )  
  
# ================= OTP EXTRACT =================  
def extract_otp(message: str):  
    for p in OTP_PATTERNS:  
        m = re.findall(p, message)  
        if m:  
            return m[-1]  
    return None  
  
# ================= FETCH SMS =================  
def fetch_sms():  
    params = {  
        "fdate1": "2000-01-01 00:00:00",  
        "fdate2": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),  
        "fg": "0",  
        "sEcho": "1",  
        "iColumns": "9",  
        "iDisplayStart": "0",  
        "iDisplayLength": "50",  
        "_": str(int(time.time() * 1000)),  
    }  
  
    headers = {  
        "Referer": f"{BASE_URL}/agent/SMSCDRReports",  
        "Cache-Control": "no-cache",  
        "Pragma": "no-cache",  
    }  
  
    r = session.get(DATA_URL, params=params, headers=headers, timeout=20)  
    if r.status_code != 200:  
        return []  
    return r.json().get("aaData", [])  
  
# ================= PARSE ROW =================  
def parse_row(row):  
    if not isinstance(row, list) or len(row) < 6:  
        return None  
  
    ts, operator, number, service, _, message = row[:6]  
  
    if not isinstance(message, str):  
        return None  
  
    if sum(c.isdigit() for c in str(number)) < 5:  
        return None  
  
    otp = extract_otp(message)  
    if not otp:  
        return None  
  
    return ts, operator, str(number), service, message, otp  
  
# ================= MESSAGE STYLE =================  
def build_message(ts, number, otp, service, operator, message):  
    return (  
        f"🔐 *NEW OTP RECEIVED* 🔐\n"  
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"  
        f"⏰ *TIME*\n"  
        f"┗ `{ts}`\n\n"  
        f"📞 *NUMBER*\n"  
        f"┗ `{number}`\n\n"  
        f"🔥 *OTP CODE*\n"  
        f"┗ 🔴 *`{otp}`* 🔴\n\n"  
        f"📱 *SERVICE*\n"  
        f"┗ `{service}`\n\n"  
        f"🌍 *OPERATOR*\n"  
        f"┗ `{operator}`\n\n"  
        f"💬 *MESSAGE*\n"  
        f"┗ `{message}`\n\n"  
        f"━━━━━━━━━━━━━━━━━━━━━━\n"  
        f"⚡ *Instant OTP Forwarder*"  
    )  
  
# ================= MAIN LOOP =================  
def main():  
    global initialized  
    log.info("🚀 INTS OTP Bot Started (LIVE ONLY MODE)")  
  
    while True:  
        rows = fetch_sms()  
  
        for row in rows:  
            parsed = parse_row(row)  
            if not parsed:  
                continue  
  
            ts, operator, number, service, message, otp = parsed  
            msg_id = sha1(f"{ts}|{number}|{message}".encode()).hexdigest()  
  
            # 🔒 First cycle: just mark old OTP as seen  
            if not initialized:  
                seen_messages.add(msg_id)  
                continue  
  
            # 🔔 Live OTP only  
            if msg_id in seen_messages:  
                continue  
  
            text = build_message(  
                ts=ts,  
                number=number,  
                otp=otp,  
                service=service,  
                operator=operator,  
                message=message,  
            )  
  
            send_telegram(text)  
            seen_messages.add(msg_id)  
            log.info("📤 Live OTP forwarded: %s", otp)  
  
        initialized = True  
        time.sleep(POLL_INTERVAL)  
  
if __name__ == "__main__":  
    main()
