# app.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
import time
import logging

from decrypt_seed import load_private_key, decrypt_seed as decrypt_seed_func
from totp_utils import generate_totp_code, verify_totp_code

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pki-totp")

# Prefer container /data, fallback to local ./data for testing
CONTAINER_DATA = Path("/data")
LOCAL_DATA = Path("data")
DATA_DIR = CONTAINER_DATA if CONTAINER_DATA.exists() else LOCAL_DATA
SEED_FILE = DATA_DIR / "seed.txt"

PRIVATE_KEY_PATH = Path("student_private.pem")

app = FastAPI(title="PKI TOTP Auth Microservice")


class EncryptedSeedPayload(BaseModel):
    encrypted_seed: str


class CodePayload(BaseModel):
    code: str | None = None


def err(msg: str, status_code: int):
    """Helper to return error responses with expected JSON format."""
    return JSONResponse(content={"error": msg}, status_code=status_code)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/decrypt-seed")
def decrypt_seed_endpoint(payload: EncryptedSeedPayload):
    # 1. Load private key file
    if not PRIVATE_KEY_PATH.exists():
        logger.error("student_private.pem not found")
        return err("Decryption failed", 500)

    try:
        priv = load_private_key(PRIVATE_KEY_PATH)
    except Exception:
        logger.exception("Failed to load private key")
        return err("Decryption failed", 500)

    # 2. Decrypt (expects RSA/OAEP-SHA256)
    try:
        hex_seed = decrypt_seed_func(payload.encrypted_seed, priv)
        # decrypt_seed_func should already validate 64-char hex
    except Exception:
        logger.exception("Decryption failed")
        return err("Decryption failed", 500)

    # 3. Save to /data/seed.txt
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SEED_FILE.write_text(hex_seed + "\n", encoding="utf-8")  # LF ending
    except Exception:
        logger.exception("Failed to save seed")
        return err("Decryption failed", 500)

    return {"status": "ok"}


@app.get("/generate-2fa")
def generate_2fa():
    if not SEED_FILE.exists():
        return err("Seed not decrypted yet", 500)

    try:
        hex_seed = SEED_FILE.read_text().strip()
        if len(hex_seed) != 64:
            raise ValueError("Invalid seed in file")

        code = generate_totp_code(hex_seed)  # returns 6-digit string
        remaining = 30 - (int(time.time()) % 30)
        valid_for = remaining if remaining != 0 else 30

        return {"code": code, "valid_for": valid_for}
    except Exception:
        logger.exception("Failed to generate TOTP")
        return err("Seed not decrypted yet", 500)


@app.post("/verify-2fa")
def verify_2fa(payload: CodePayload):
    # 1. Check code present
    if payload.code is None or str(payload.code).strip() == "":
        return err("Missing code", 400)

    code_str = str(payload.code).strip()

    # 2. Validate format: 6-digit numeric
    if not (code_str.isdigit() and len(code_str) == 6):
        return err("Code must be a 6-digit string", 400)

    # 3. Ensure seed exists
    if not SEED_FILE.exists():
        return err("Seed not decrypted yet", 500)

    try:
        hex_seed = SEED_FILE.read_text().strip()
        if len(hex_seed) != 64:
            raise ValueError("Invalid seed in file")

        valid = verify_totp_code(hex_seed, code_str, valid_window=1)
        return {"valid": bool(valid)}
    except Exception:
        logger.exception("Verification error")
        return err("Seed not decrypted yet", 500)
