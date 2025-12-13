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

# Evaluator expects seed ONLY at /data/seed.txt
DATA_DIR = Path("/data")
SEED_FILE = DATA_DIR / "seed.txt"

PRIVATE_KEY_PATH = Path("student_private.pem")

app = FastAPI(title="PKI TOTP Auth Microservice")


class EncryptedSeedPayload(BaseModel):
    encrypted_seed: str


class CodePayload(BaseModel):
    code: str | None = None


def err(msg: str, status_code: int):
    return JSONResponse(content={"error": msg}, status_code=status_code)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/decrypt-seed")
def decrypt_seed_endpoint(payload: EncryptedSeedPayload):
    if not PRIVATE_KEY_PATH.exists():
        return err("Decryption failed", 500)

    try:
        private_key = load_private_key(PRIVATE_KEY_PATH)
    except Exception:
        logger.exception("Failed to load private key")
        return err("Decryption failed", 500)

    try:
        hex_seed = decrypt_seed_func(payload.encrypted_seed, private_key)
    except Exception:
        logger.exception("Seed decryption failed")
        return err("Decryption failed", 500)

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SEED_FILE.write_text(hex_seed, encoding="utf-8")
    except Exception:
        logger.exception("Failed to write seed file")
        return err("Decryption failed", 500)

    return {"status": "ok"}


@app.get("/generate-2fa")
def generate_2fa():
    if not SEED_FILE.exists():
        return err("Seed not decrypted yet", 500)

    try:
        hex_seed = SEED_FILE.read_text().strip()
        code = generate_totp_code(hex_seed)

        remaining = 30 - (int(time.time()) % 30)
        valid_for = remaining if remaining != 0 else 30

        return {"code": code, "valid_for": valid_for}
    except Exception:
        logger.exception("Failed to generate TOTP")
        return err("Seed not decrypted yet", 500)


@app.post("/verify-2fa")
def verify_2fa(payload: CodePayload):
    if payload.code is None:
        return err("Missing code", 400)

    if not SEED_FILE.exists():
        return err("Seed not decrypted yet", 500)

    try:
        hex_seed = SEED_FILE.read_text().strip()
        code_str = str(payload.code).strip()

        valid = False
        if code_str.isdigit() and len(code_str) == 6:
            valid = verify_totp_code(hex_seed, code_str, valid_window=1)

        return {"valid": bool(valid)}
    except Exception:
        logger.exception("Verification error")
        return err("Seed not decrypted yet", 500)
