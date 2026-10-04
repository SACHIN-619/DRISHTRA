"""
Password hashing: PBKDF2-HMAC-SHA256, 310,000 iterations (OWASP 2023 guidance),
16-byte random salt, constant-time comparison. Standard library only, so it works
on an air-gapped host without extra packages.

Stored format:  pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
"""
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
import os as _os
ITERATIONS = int(_os.getenv("DRISHTRA_PBKDF2_ITERATIONS", "310000"))


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != ALGORITHM:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False
