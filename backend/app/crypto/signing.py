"""
DRISHTRA Cryptographic Engine - Ed25519 Signing
High-Speed Asymmetric Digital Signatures for Inference Attestation and Audit Records
"""
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from typing import Tuple

def generate_keypair() -> Tuple[bytes, bytes]:
    """Generates an Ed25519 (private_key_bytes, public_key_bytes) tuple."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    from cryptography.hazmat.primitives import serialization
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return priv_bytes, pub_bytes

def sign_data(private_key_raw: bytes, data: bytes) -> bytes:
    """Signs bytes using raw Ed25519 private key."""
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_raw)
    return priv_key.sign(data)

def verify_data_signature(public_key_raw: bytes, signature: bytes, data: bytes) -> bool:
    """Verifies signature against data using raw Ed25519 public key."""
    try:
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_raw)
        pub_key.verify(signature, data)
        return True
    except (InvalidSignature, Exception):
        return False
