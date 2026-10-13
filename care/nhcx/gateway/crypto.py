"""G6. Encryption: compact JWE (RSA-OAEP-256 + A256GCM out, allow-listed algorithms in)."""

from __future__ import annotations

import base64
import binascii
import json
import re
from typing import Any

from authlib.jose import JsonWebEncryption
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

OUT_ALG = "RSA-OAEP-256"
OUT_ENC = "A256GCM"
IN_ALGS = ("RSA-OAEP-256", "RSA-OAEP")
IN_ENCS = (
    "A256GCM",
    "A128GCM",
    "A192GCM",
    "A256CBC-HS512",
    "A128CBC-HS256",
    "A192CBC-HS384",
)
DROPPED_HEADERS = ("alg", "enc", "typ")
NOT_COMPACT = "payload is not a compact JWE (expected five dot-separated parts)"
COMPACT_PARTS = 5

_PEM_RE = re.compile(
    r"-----BEGIN ([A-Z0-9 ]+)-----\s*(.*?)\s*-----END \1-----", re.DOTALL
)

_jwe_out = JsonWebEncryption(algorithms=[OUT_ALG, OUT_ENC])
_jwe_in = JsonWebEncryption(algorithms=[*IN_ALGS, *IN_ENCS])


class CryptoError(Exception):
    """Plain error with the verbatim G6S message; callers wrap it."""


def _b64url_decode(s: str) -> bytes:
    s = s.strip().rstrip("=")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def is_compact_jwe(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    parts = s.strip().split(".")
    return len(parts) == COMPACT_PARTS and parts[0] != ""


def flattened_to_compact(obj: Any) -> str | None:
    """A flattened JSON JWE as the compact string, or None when `obj` is not one.

    The knowledge source (nhcx.decision.jwe-serialisation) asks receivers to parse
    either serialisation; G8 hands the compact form on.
    """
    if not isinstance(obj, dict):
        return None
    keys = ("protected", "encrypted_key", "iv", "ciphertext", "tag")
    if not all(isinstance(obj.get(k), str) for k in keys) or obj.get("aad"):
        return None
    return ".".join(obj[k] for k in keys)


def encrypt(payload: bytes | str, public_key: Any, headers: dict | None) -> str:
    if public_key is None:
        raise CryptoError("no recipient public key")
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    if not payload:
        raise CryptoError("payload is empty")
    protected = {"alg": OUT_ALG, "enc": OUT_ENC}
    for k, v in (headers or {}).items():
        if k not in DROPPED_HEADERS:
            protected[k] = v
    try:
        out = _jwe_out.serialize_compact(protected, payload, public_key)
    except Exception as e:
        msg = f"encrypt: {e}"
        raise CryptoError(msg) from e
    return out.decode("ascii") if isinstance(out, bytes) else out


def parse_header(compact: str) -> dict:
    if not is_compact_jwe(compact):
        raise CryptoError(NOT_COMPACT)
    first = compact.strip().split(".")[0]
    try:
        raw = _b64url_decode(first)
    except (binascii.Error, ValueError) as e:
        msg = f"decode JWE header: {e}"
        raise CryptoError(msg) from e
    try:
        out = json.loads(raw)
    except ValueError as e:
        msg = f"JWE header is not a JSON object: {e}"
        raise CryptoError(msg) from e
    if not isinstance(out, dict):
        raise CryptoError("JWE header is not a JSON object: not an object")
    return out


def decrypt(compact: str, private_key: Any) -> bytes:
    if private_key is None:
        raise CryptoError("no private key")
    if not is_compact_jwe(compact):
        raise CryptoError(NOT_COMPACT)
    try:
        header = parse_header(compact)
    except CryptoError as e:
        msg = f"parse JWE: {e}"
        raise CryptoError(msg) from e
    alg, enc = header.get("alg"), header.get("enc")
    if alg not in IN_ALGS:
        msg = f"parse JWE: unsupported key algorithm {alg!r}"
        raise CryptoError(msg)
    if enc not in IN_ENCS:
        msg = f"parse JWE: unsupported content encryption {enc!r}"
        raise CryptoError(msg)
    if "zip" in header:
        raise CryptoError("parse JWE: compressed payloads are not accepted")
    try:
        out = _jwe_in.deserialize_compact(compact.strip(), private_key)
    except Exception as e:
        msg = f"decrypt: {e}"
        raise CryptoError(msg) from e
    return out["payload"]


def decode_key_material(text: str) -> str:
    text = (text or "").strip()
    if "-----BEGIN" in text:
        return text
    compact = "".join(text.split())
    for decoder in (
        lambda s: base64.b64decode(s, validate=True),
        lambda s: base64.b64decode(s + "=" * (-len(s) % 4), validate=True),
        lambda s: base64.urlsafe_b64decode(s),
        lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)),
    ):
        try:
            out = decoder(compact).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if "-----BEGIN" in out:
            return out.strip()
    return text


def _first_block(text: str) -> tuple[str, bytes] | None:
    m = _PEM_RE.search(decode_key_material(text))
    if not m:
        return None
    label = m.group(1)
    body = "".join(m.group(2).split())
    pem = f"-----BEGIN {label}-----\n{body}\n-----END {label}-----\n"
    return label, pem.encode("ascii")


def parse_private_key(text: str) -> rsa.RSAPrivateKey:
    block = _first_block(text)
    if block is None:
        raise CryptoError("no PEM block found in private key material")
    label, pem = block
    try:
        key = serialization.load_pem_private_key(
            pem.replace(label.encode(), b"PRIVATE KEY")
            if label != "PRIVATE KEY"
            else pem,
            password=None,
        )
    except (ValueError, TypeError):
        key = None
    if key is not None:
        if not isinstance(key, rsa.RSAPrivateKey):
            raise CryptoError("private key is not an RSA key")
        return key
    try:
        rsa_pem = pem.replace(label.encode(), b"RSA PRIVATE KEY")
        key = serialization.load_pem_private_key(rsa_pem, password=None)
    except (ValueError, TypeError) as e:
        msg = f"private key is neither PKCS#8 nor PKCS#1: {e}"
        raise CryptoError(msg) from e
    if not isinstance(key, rsa.RSAPrivateKey):
        raise CryptoError("private key is not an RSA key")
    return key


def parse_public_key(text: str) -> rsa.RSAPublicKey:
    block = _first_block(text)
    if block is None:
        raise CryptoError("no PEM block found in certificate material")
    label, pem = block
    if label in ("PUBLIC KEY", "RSA PUBLIC KEY"):
        try:
            key = serialization.load_pem_public_key(pem)
        except (ValueError, TypeError) as e:
            msg = f"parse public key: {e}"
            raise CryptoError(msg) from e
        if not isinstance(key, rsa.RSAPublicKey):
            raise CryptoError("public key is not an RSA key")
        return key
    try:
        cert = x509.load_pem_x509_certificate(
            pem.replace(label.encode(), b"CERTIFICATE")
        )
    except (ValueError, TypeError) as e:
        msg = f"parse certificate: {e}"
        raise CryptoError(msg) from e
    key = cert.public_key()
    if not isinstance(key, rsa.RSAPublicKey):
        raise CryptoError("certificate public key is not an RSA key")
    return key


def public_numbers_equal(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return False
    try:
        return a.public_numbers() == b.public_numbers()
    except AttributeError:
        return False


__all__ = [
    "CryptoError",
    "decode_key_material",
    "decrypt",
    "encrypt",
    "flattened_to_compact",
    "is_compact_jwe",
    "parse_header",
    "parse_private_key",
    "parse_public_key",
    "public_numbers_equal",
]
