"""
Signal NFX authentication helper.

Tries to auto-extract the JWT from Chrome on macOS.
Falls back to manual paste if that fails.
Saves the JWT to .signal_jwt for reuse.
"""

import os
import sys
import json
import sqlite3
import shutil
import tempfile
import subprocess
import re
import struct
import hashlib
from pathlib import Path

JWT_CACHE = Path(__file__).parent / ".signal_jwt"
COOKIE_DB_PATHS = [
    Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies",
    Path.home() / "Library/Application Support/Google/Chrome/Profile 15/Cookies",
    Path.home() / "Library/Application Support/Google/Chrome/Profile 1/Cookies",
    Path.home() / "Library/Application Support/Google/Chrome/Profile 2/Cookies",
]


def _get_chrome_safe_storage_key():
    result = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", "Chrome Safe Storage", "-a", "Chrome"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("Could not read Chrome Safe Storage key. Make sure Chrome is installed.")
    return result.stdout.strip()


def _derive_key(password: str) -> bytes:
    try:
        from Crypto.Protocol.KDF import PBKDF2
        from Crypto.Hash import SHA1
        return PBKDF2(password.encode(), b"saltysalt", dkLen=16, count=1003, prf=lambda p, s: __import__('hmac').new(p, s, __import__('hashlib').sha1).digest())
    except ImportError:
        # fallback using hashlib
        import hashlib
        key = hashlib.pbkdf2_hmac("sha1", password.encode(), b"saltysalt", 1003, dklen=16)
        return key


def _decrypt_value(encrypted_value: bytes, key: bytes) -> str:
    try:
        from Crypto.Cipher import AES
        iv = b" " * 16
        cipher = AES.new(key, AES.MODE_CBC, iv)
        # Strip the "v10" prefix
        decrypted = cipher.decrypt(encrypted_value[3:])
        # Remove PKCS7 padding
        pad_len = decrypted[-1]
        decrypted = decrypted[:-pad_len]
        return decrypted.decode("utf-8", errors="ignore")
    except ImportError:
        raise RuntimeError(
            "pycryptodome is required for auto-auth. Install it with: pip install pycryptodome\n"
            "Or paste your JWT manually when prompted."
        )


def _extract_jwt_from_chrome() -> str | None:
    """Try to extract SIGNAL_ACCESS_JWT from Chrome cookies."""
    for db_path in COOKIE_DB_PATHS:
        if not db_path.exists():
            continue
        try:
            # Copy the DB (Chrome locks it while running)
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            shutil.copy2(db_path, tmp_path)

            conn = sqlite3.connect(tmp_path)
            cursor = conn.execute(
                "SELECT value, encrypted_value FROM cookies WHERE host_key LIKE '%signal.nfx.com%' AND name = 'SIGNAL_ACCESS_JWT'"
            )
            row = cursor.fetchone()
            conn.close()
            os.unlink(tmp_path)

            if not row:
                continue

            value, encrypted_value = row
            if value:
                return _extract_jwt_from_string(value)

            if encrypted_value:
                password = _get_chrome_safe_storage_key()
                key = _derive_key(password)
                decrypted = _decrypt_value(encrypted_value, key)
                return _extract_jwt_from_string(decrypted)

        except Exception:
            continue

    return None


def _extract_jwt_from_string(s: str) -> str | None:
    """Extract JWT token from a string using regex."""
    match = re.search(r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+', s)
    if match:
        return match.group(0)
    return None


def get_jwt(force_manual: bool = False) -> str:
    """
    Get a valid Signal NFX JWT. Order of precedence:
    1. SIGNAL_JWT environment variable
    2. Cached .signal_jwt file
    3. Auto-extract from Chrome (macOS only)
    4. Manual paste
    """
    # 1. Env var
    if not force_manual and os.environ.get("SIGNAL_JWT"):
        return os.environ["SIGNAL_JWT"].strip()

    # 2. Cache
    if not force_manual and JWT_CACHE.exists():
        jwt = JWT_CACHE.read_text().strip()
        if jwt:
            return jwt

    # 3. Auto-extract from Chrome
    if not force_manual and sys.platform == "darwin":
        print("Attempting to auto-extract JWT from Chrome...")
        jwt = _extract_jwt_from_chrome()
        if jwt:
            print("JWT extracted successfully from Chrome.")
            JWT_CACHE.write_text(jwt)
            return jwt
        else:
            print("Could not find Signal NFX cookie in Chrome. Make sure you're logged in at signal.nfx.com")

    # 4. Manual paste
    print("\nTo get your JWT manually:")
    print("  1. Go to signal.nfx.com and log in")
    print("  2. Open DevTools (Cmd+Option+I) > Application > Cookies > signal.nfx.com")
    print("  3. Copy the value of SIGNAL_ACCESS_JWT")
    print()
    jwt = input("Paste your JWT here: ").strip()

    if not jwt:
        print("No JWT provided. Exiting.")
        sys.exit(1)

    JWT_CACHE.write_text(jwt)
    print("JWT saved to .signal_jwt for future use.")
    return jwt


def clear_jwt():
    """Remove cached JWT (useful if it expires)."""
    if JWT_CACHE.exists():
        JWT_CACHE.unlink()
        print("Cached JWT cleared.")


if __name__ == "__main__":
    jwt = get_jwt()
    print(f"\nJWT (first 40 chars): {jwt[:40]}...")
