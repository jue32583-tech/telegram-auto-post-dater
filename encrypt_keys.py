"""
============================================
🔐 API Keys Encrypt / Decrypt Tool v2.0
============================================
Usage:
    Encrypt:  python3 encrypt_keys.py encrypt
    Decrypt:  python3 encrypt_keys.py decrypt

Method 1 (Current): Keys inside bot.py
Method 2 (Secure):  Keys encrypted in .env.encrypted (Fernet 256-bit)
============================================
"""

import base64
import os
import sys

from cryptography.fernet import Fernet


def get_or_create_key() -> bytes:
    """Load encryption key from .env.key or generate a new one."""
    key_file = ".env.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read().strip()
    key = Fernet.generate_key()
    with open(key_file, "wb") as f:
        f.write(key)
    os.chmod(key_file, 0o600)
    return key


def encrypt_env():
    """Read .env and save encrypted version to .env.encrypted."""
    env_file = ".env"
    encrypted_file = ".env.encrypted"
    if not os.path.exists(env_file):
        print("❌ .env file not found. Create one first.")
        return

    key = get_or_create_key()
    f = Fernet(key)

    with open(env_file, "r", encoding="utf-8") as fh:
        content = fh.read()

    encrypted = f.encrypt(content.encode("utf-8"))

    with open(encrypted_file, "wb") as fh:
        fh.write(encrypted)

    print("✅ .env encrypted → .env.encrypted")
    print("🔑 Key saved in .env.key (keep this safe!)")
    print("⚠️  You can now safely delete the plain .env file.")


def decrypt_env():
    """Read .env.encrypted and restore plain .env."""
    env_file = ".env"
    encrypted_file = ".env.encrypted"
    key_file = ".env.key"

    if not os.path.exists(encrypted_file):
        print("❌ .env.encrypted not found.")
        return
    if not os.path.exists(key_file):
        print("❌ .env.key not found.")
        return

    with open(key_file, "rb") as f:
        key = f.read().strip()

    with open(encrypted_file, "rb") as f:
        encrypted = f.read()

    try:
        fernet = Fernet(key)
        content = fernet.decrypt(encrypted).decode("utf-8")
        with open(env_file, "w", encoding="utf-8") as fh:
            fh.write(content)
        print("✅ .env.encrypted decrypted → .env")
    except Exception as e:
        print(f"❌ Decryption failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "encrypt":
        encrypt_env()
    elif mode == "decrypt":
        decrypt_env()
    else:
        print(f"Unknown mode: {mode}")
        print("Use: encrypt or decrypt")
