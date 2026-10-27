#!/usr/bin/env python3
"""Frontier Analyst encryption.

Design (no secret is ever stored by the pipeline):
  * An RSA-3072 key pair is generated once (``keygen``).
  * The public key is published in ``docs/site.json``. Runs only need the public key to
    encrypt new issues, so a scheduled run never sees the password.
  * The private key is stored in ``docs/site.json`` too, but encrypted with AES-256-GCM under a
    key derived from the reader password (PBKDF2-HMAC-SHA256, 600,000 iterations, random salt).
  * Every published file gets its own random AES-256-GCM key, wrapped with RSA-OAEP-SHA256.

Readers type the password in the browser; ``docs/viewer.js`` derives the key, unlocks the
private key and decrypts the files locally. Nothing is sent to a server.

Usage:
  fa_crypto.py keygen  --site docs/site.json --password-file PATH
  fa_crypto.py encrypt --site docs/site.json --in FILE --out FILE.enc [--type text/html]
  fa_crypto.py decrypt --site docs/site.json --password-file PATH --in FILE.enc --out FILE   (testing)
"""
import argparse
import base64
import json
import os
import re
import sys
import unicodedata

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 600_000
FORMAT = "fa-enc-1"


def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()


def b64d(s: str) -> bytes:
    return base64.b64decode(s)


def normalize_password(pw: str) -> str:
    """Must match normalizePassword() in docs/viewer.js.

    Lower-case, NFKC, and any run of spaces/hyphens/underscores becomes one hyphen, so
    "Word word-word" and "word word word" unlock the same site.
    """
    pw = unicodedata.normalize("NFKC", pw).strip().lower()
    return re.sub(r"[\s\-_]+", "-", pw)


def derive_kek(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return kdf.derive(normalize_password(password).encode("utf-8"))


OAEP = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


def keygen(site_path: str, password: str) -> None:
    if len(normalize_password(password)) < 20:
        sys.exit("Refusing a short password: use a passphrase of at least 5 random words.")
    priv = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    pkcs8 = priv.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                               serialization.NoEncryption())
    spki = priv.public_key().public_bytes(serialization.Encoding.DER,
                                          serialization.PublicFormat.SubjectPublicKeyInfo)
    salt = os.urandom(16)
    iv = os.urandom(12)
    kek = derive_kek(password, salt, ITERATIONS)
    wrapped = AESGCM(kek).encrypt(iv, pkcs8, b"fa-private-key")
    site = {
        "format": FORMAT,
        "kdf": {"name": "PBKDF2", "hash": "SHA-256", "iterations": ITERATIONS, "salt": b64e(salt)},
        "private_key": {"alg": "A256GCM", "iv": b64e(iv), "aad": "fa-private-key", "ct": b64e(wrapped)},
        "public_key": {"alg": "RSA-OAEP-256", "spki": b64e(spki)},
        "display": {"motif": "aletheia"},
    }
    os.makedirs(os.path.dirname(os.path.abspath(site_path)), exist_ok=True)
    with open(site_path, "w") as f:
        json.dump(site, f, indent=1)
    print(f"Wrote {site_path}")


def load_site(site_path: str) -> dict:
    with open(site_path) as f:
        site = json.load(f)
    if site.get("format") != FORMAT:
        sys.exit(f"{site_path}: unknown format")
    return site


def encrypt_bytes(site: dict, data: bytes, content_type: str) -> dict:
    pub = serialization.load_der_public_key(b64d(site["public_key"]["spki"]))
    key = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    aad = content_type.encode()
    return {
        "format": FORMAT,
        "type": content_type,
        "ek": b64e(pub.encrypt(key, OAEP)),
        "iv": b64e(iv),
        "ct": b64e(AESGCM(key).encrypt(iv, data, aad)),
    }


def decrypt_envelope(site: dict, password: str, env: dict) -> bytes:
    kdf = site["kdf"]
    kek = derive_kek(password, b64d(kdf["salt"]), kdf["iterations"])
    pk = site["private_key"]
    pkcs8 = AESGCM(kek).decrypt(b64d(pk["iv"]), b64d(pk["ct"]), pk["aad"].encode())
    priv = serialization.load_der_private_key(pkcs8, password=None)
    key = priv.decrypt(b64d(env["ek"]), OAEP)
    return AESGCM(key).decrypt(b64d(env["iv"]), b64d(env["ct"]), env["type"].encode())


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen")
    k.add_argument("--site", required=True)
    k.add_argument("--password-file", required=True)
    e = sub.add_parser("encrypt")
    e.add_argument("--site", required=True)
    e.add_argument("--in", dest="inp", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--type", default="text/html")
    d = sub.add_parser("decrypt")
    d.add_argument("--site", required=True)
    d.add_argument("--password-file", required=True)
    d.add_argument("--in", dest="inp", required=True)
    d.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.cmd == "keygen":
        keygen(a.site, open(a.password_file).read())
    elif a.cmd == "encrypt":
        site = load_site(a.site)
        env = encrypt_bytes(site, open(a.inp, "rb").read(), a.type)
        with open(a.out, "w") as f:
            json.dump(env, f)
    elif a.cmd == "decrypt":
        site = load_site(a.site)
        env = json.load(open(a.inp))
        with open(a.out, "wb") as f:
            f.write(decrypt_envelope(site, open(a.password_file).read(), env))


if __name__ == "__main__":
    main()
