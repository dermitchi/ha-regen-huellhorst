"""Creates the signing key pair. The private key stays with the sender, the public key goes into const.py.

Usage: python tools/make_key.py .keys/regen.pem
"""
import base64
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

path = Path(sys.argv[1])
if path.exists():
    sys.exit(f"{path} exists, not overwriting")
key = Ed25519PrivateKey.generate()
path.write_bytes(key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
path.chmod(0o600)
raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
print("PUBLIC_KEY =", base64.b64encode(raw).decode())
