from __future__ import annotations

import base64
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "cryptography is required for v0.5. Run: python -m pip install cryptography"
    ) from exc


KEYS_DIR = Path.cwd() / "keys"

CERT_PRIVATE_KEY_PATH = KEYS_DIR / "omega_cert_ed25519_private.pem"
CERT_PUBLIC_KEY_PATH = KEYS_DIR / "omega_cert_ed25519_public.pem"

POLICY_PRIVATE_KEY_PATH = KEYS_DIR / "omega_policy_ed25519_private.pem"
POLICY_PUBLIC_KEY_PATH = KEYS_DIR / "omega_policy_ed25519_public.pem"

CERT_KEY_ID = "omega-cert-ed25519-dev-v1"
POLICY_KEY_ID = "omega-policy-ed25519-dev-v1"


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def generate_ed25519_keypair(private_path: str | Path, public_path: str | Path) -> None:
    private_path = Path(private_path)
    public_path = Path(public_path)

    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_bytes)
    public_path.write_bytes(public_bytes)


def ensure_keypair(private_path: str | Path, public_path: str | Path) -> None:
    private_path = Path(private_path)
    public_path = Path(public_path)

    if not private_path.exists() or not public_path.exists():
        generate_ed25519_keypair(private_path, public_path)


def ensure_dev_keys() -> None:
    ensure_keypair(CERT_PRIVATE_KEY_PATH, CERT_PUBLIC_KEY_PATH)
    ensure_keypair(POLICY_PRIVATE_KEY_PATH, POLICY_PUBLIC_KEY_PATH)


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    data = Path(path).read_bytes()
    key = serialization.load_pem_private_key(data, password=None)

    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("expected Ed25519 private key")

    return key


def load_public_key(path: str | Path) -> Ed25519PublicKey:
    data = Path(path).read_bytes()
    key = serialization.load_pem_public_key(data)

    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("expected Ed25519 public key")

    return key


def sign_bytes(message: bytes, private_key_path: str | Path) -> str:
    private_key = load_private_key(private_key_path)
    signature = private_key.sign(message)
    return _b64encode(signature)


def verify_signature_bytes(message: bytes, signature_b64: str, public_key_path: str | Path) -> bool:
    public_key = load_public_key(public_key_path)

    try:
        public_key.verify(_b64decode(signature_b64), message)
        return True
    except Exception:
        return False


def sign_text(message: str, private_key_path: str | Path) -> str:
    return sign_bytes(message.encode("utf-8"), private_key_path)


def verify_signature_text(message: str, signature_b64: str, public_key_path: str | Path) -> bool:
    return verify_signature_bytes(message.encode("utf-8"), signature_b64, public_key_path)


if __name__ == "__main__":
    ensure_dev_keys()
    print("CERT_PRIVATE:", CERT_PRIVATE_KEY_PATH)
    print("CERT_PUBLIC:", CERT_PUBLIC_KEY_PATH)
    print("POLICY_PRIVATE:", POLICY_PRIVATE_KEY_PATH)
    print("POLICY_PUBLIC:", POLICY_PUBLIC_KEY_PATH)

# ---------------------------------------------------------------------------
# v0.4.1 STRICT SIGNATURE VERIFICATION PATCH
# ---------------------------------------------------------------------------
# This intentionally overrides earlier sign/verify helpers if they were loose.
# Any byte change in signature must fail verification.
#
# Uses stdlib HMAC-SHA256 as the current dev-signature backend so the project
# remains dependency-free on Windows. The interface remains:
#   sign_text(text, private_key_path)
#   verify_signature_text(text, signature, public_key_path)
#
# In this dev backend, ensure_dev_keys writes the same secret to private/public
# key files. A wrong public key file will therefore fail verification.
# ---------------------------------------------------------------------------

import base64 as _omega_b64
import hashlib as _omega_hashlib
import hmac as _omega_hmac
import secrets as _omega_secrets
from pathlib import Path as _OmegaPath


def _omega_key_bytes(path) -> bytes:
    p = _OmegaPath(path)
    if not p.exists():
        ensure_dev_keys()
    data = p.read_bytes().strip()
    if not data:
        raise ValueError(f"empty key file: {p}")
    return data


def ensure_dev_keys() -> None:
    priv = _OmegaPath(CERT_PRIVATE_KEY_PATH)
    pub = _OmegaPath(CERT_PUBLIC_KEY_PATH)

    priv.parent.mkdir(parents=True, exist_ok=True)
    pub.parent.mkdir(parents=True, exist_ok=True)

    if not priv.exists() or not pub.exists():
        secret = _omega_b64.urlsafe_b64encode(_omega_secrets.token_bytes(32))
        priv.write_bytes(secret)
        pub.write_bytes(secret)

    # If one exists and the other does not, repair by copying the existing key.
    if priv.exists() and not pub.exists():
        pub.write_bytes(priv.read_bytes())

    if pub.exists() and not priv.exists():
        priv.write_bytes(pub.read_bytes())


def sign_text(text: str, private_key_path=CERT_PRIVATE_KEY_PATH) -> str:
    key = _omega_key_bytes(private_key_path)
    digest = _omega_hmac.new(
        key,
        text.encode("utf-8"),
        _omega_hashlib.sha256,
    ).digest()
    return _omega_b64.urlsafe_b64encode(digest).decode("ascii")


def verify_signature_text(
    text: str,
    signature: str,
    public_key_path=CERT_PUBLIC_KEY_PATH,
) -> bool:
    try:
        key = _omega_key_bytes(public_key_path)
        expected = _omega_b64.urlsafe_b64encode(
            _omega_hmac.new(
                key,
                text.encode("utf-8"),
                _omega_hashlib.sha256,
            ).digest()
        ).decode("ascii")

        # Strict constant-time comparison. No prefix acceptance. No fallback pass.
        return _omega_hmac.compare_digest(str(signature), expected)
    except Exception:
        return False
