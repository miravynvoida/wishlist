import hashlib
import hmac
import os
import time
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MAX_AGE = int(os.getenv("INIT_DATA_MAX_AGE", "86400"))

def validate_init_data(init_data: str) -> dict:
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="BOT_TOKEN is not configured")
    if not init_data or len(init_data) > 8192:
        raise HTTPException(status_code=401, detail="Missing Telegram initData")
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
        received_hash = pairs.pop("hash")
        auth_date = int(pairs.get("auth_date", "0"))
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")
    if abs(int(time.time()) - auth_date) > MAX_AGE:
        raise HTTPException(status_code=401, detail="Telegram initData expired")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")
    import json
    try:
        user = json.loads(pairs.get("user", "{}"))
        user_id = int(user["id"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Telegram user missing")
    return {"id": user_id, "user": user}

def require_telegram_user(x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data")):
    return validate_init_data(x_telegram_init_data)

def require_owner(owner_id: int, user: dict):
    if int(user["id"]) != int(owner_id):
        raise HTTPException(status_code=403, detail="You can only manage your own wishlist")
    return user
