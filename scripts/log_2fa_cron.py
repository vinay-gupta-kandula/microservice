#!/usr/bin/env python3
"""
Cron script to log 2FA codes every minute.

This is run by cron via:
* * * * * cd /app && /usr/local/bin/python3 scripts/log_2fa_cron.py >> /cron/last_code.txt 2>&1
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import base64
import hmac
import hashlib
import struct
import time


SEED_PATH = Path("/data/seed.txt")


def read_hex_seed() -> str:
    """
    1. Read hex seed from persistent storage (/data/seed.txt)
    2. Strip whitespace/newlines
    3. Handle file-not-found or empty file gracefully
    """
    try:
        data = SEED_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print("ERROR: /data/seed.txt not found", file=sys.stderr)
        return ""

    if not data:
        print("ERROR: /data/seed.txt is empty", file=sys.stderr)
        return ""

    # basic validation: 64 hex chars
    if len(data) != 64:
        print(f"WARNING: /data/seed.txt length is {len(data)}, expected 64 hex chars", file=sys.stderr)

    return data


def hex_to_bytes(hex_seed: str) -> bytes:
    try:
        return bytes.fromhex(hex_seed)
    except ValueError:
        print("ERROR: invalid hex in /data/seed.txt", file=sys.stderr)
        return b""


def generate_totp_from_hex(hex_seed: str, timestep: int = 30, digits: int = 6) -> str:
    """
    Simple TOTP generator using the same logic as your API.
    If you already implemented a helper like `generate_totp_from_hex`
    elsewhere, IMPORT and use that instead.
    """
    key = hex_to_bytes(hex_seed)
    if not key:
        return "000000"

    # Unix time step
    counter = int(time.time() // timestep)
    msg = struct.pack(">Q", counter)

    hmac_hash = hmac.new(key, msg, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    code_int = (
        ((hmac_hash[offset] & 0x7F) << 24)
        | ((hmac_hash[offset + 1] & 0xFF) << 16)
        | ((hmac_hash[offset + 2] & 0xFF) << 8)
        | (hmac_hash[offset + 3] & 0xFF)
    )

    code = code_int % (10 ** digits)
    return str(code).zfill(digits)


def main() -> None:
    # 1. Read hex seed
    hex_seed = read_hex_seed()
    if not hex_seed:
        # error already printed
        return

    # 2. Generate current TOTP code
    code = generate_totp_from_hex(hex_seed)

    # 3. Get current UTC timestamp
    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # 4. Output formatted line
    print(f"{timestamp} - 2FA Code: {code}")


if __name__ == "__main__":
    main()
