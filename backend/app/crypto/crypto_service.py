"""
DRISHTRA Cryptographic Assurance Service
Authoritative, centralized cryptographic operations across the sovereign assurance fabric:
- RFC 8785 Canonical JSON Serialization
- SHA-256 Digest & Hash Combinations
- Ed25519 Asymmetric Digital Signatures
- Tamper-Evident Hash-Chaining & Non-Repudiation Verification
- Sovereign Key Management (Environment, Prototype Vault, Future HSM/KMS interface)
"""
import os
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Union
from app.crypto.canonicalization import canonicalize_json
from app.crypto.hashing import sha256_bytes, sha256_file, sha256_canonical_dict, sha256_combine
from app.crypto.signing import generate_keypair, sign_data, verify_data_signature
from app.crypto.chain import compute_chained_hash, verify_hash_chain, GENESIS_HASH

class KeyManagementInterface:
    """
    Abstract interface separating prototype key derivation from future
    production hardware security modules (HSM, PKCS#11, TPM, institutional KMS).
    """
    @staticmethod
    def get_sovereign_node_keypair() -> Tuple[bytes, bytes]:
        """
        Returns this node's Ed25519 signing keypair (private_raw, public_raw).
        Prototype storage: a 32-byte seed in storage/keys/node_ed25519.seed,
        generated once with os.urandom and readable only by the service user.
        Production deployments replace this method with an HSM / PKCS#11 / TPM
        backed implementation; nothing else in the codebase touches key bytes.
        The private key is never returned by any API.
        """
        from app.core.config import KEYS_DIR
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        os.makedirs(KEYS_DIR, exist_ok=True)
        seed_path = os.path.join(KEYS_DIR, "node_ed25519.seed")
        seed = None
        if os.path.exists(seed_path):
            with open(seed_path, "rb") as fh:
                seed = fh.read()
        if not seed or len(seed) != 32:
            seed = os.urandom(32)
            with open(seed_path, "wb") as fh:
                fh.write(seed)
            try:
                os.chmod(seed_path, 0o600)
            except OSError:
                pass

        priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        pub_bytes = priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return seed, pub_bytes

    @staticmethod
    def public_key_fingerprint() -> str:
        """SHA-256 fingerprint of the node public key (safe to display)."""
        _, pub = KeyManagementInterface.get_sovereign_node_keypair()
        return hashlib.sha256(pub).hexdigest()

class CryptoService:
    GENESIS = GENESIS_HASH

    @staticmethod
    def canonicalize(data: Any) -> bytes:
        """Produce canonical, deterministic JSON bytes (RFC 8785)."""
        return canonicalize_json(data)

    @staticmethod
    def hash(data: Union[bytes, str, Dict[str, Any]]) -> str:
        """
        Computes SHA-256 hex digest for bytes, str, or dictionary.
        Dictionaries are canonicalized before hashing.
        """
        if isinstance(data, bytes):
            return sha256_bytes(data)
        elif isinstance(data, str):
            return sha256_bytes(data.encode('utf-8'))
        elif isinstance(data, (dict, list)):
            return sha256_canonical_dict(data)
        else:
            return sha256_bytes(str(data).encode('utf-8'))

    @staticmethod
    def hash_file(filepath: str, chunk_size: int = 65536) -> str:
        """Streams file from disk and computes SHA-256 digest without loading entire file in RAM."""
        return sha256_file(filepath, chunk_size=chunk_size)

    @staticmethod
    def combine_hashes(*hashes: str) -> str:
        """Deterministically combines multiple SHA-256 digests."""
        return sha256_combine(*hashes)

    @staticmethod
    def generate_keys() -> Tuple[bytes, bytes]:
        """Generates an Ed25519 keypair: (private_bytes, public_bytes)."""
        return generate_keypair()

    @classmethod
    def get_node_keys(cls) -> Tuple[bytes, bytes]:
        """Retrieves default sovereign node keypair via KeyManagementInterface."""
        return KeyManagementInterface.get_sovereign_node_keypair()

    @classmethod
    def sign(cls, data: Union[bytes, Dict[str, Any]], private_key_raw: Optional[bytes] = None) -> bytes:
        """
        Signs canonical payload using specified Ed25519 raw private key or sovereign node key.
        """
        if private_key_raw is None:
            private_key_raw, _ = cls.get_node_keys()

        if isinstance(data, dict):
            payload_bytes = cls.canonicalize(data)
        elif isinstance(data, str):
            payload_bytes = data.encode('utf-8')
        else:
            payload_bytes = data

        return sign_data(private_key_raw, payload_bytes)

    @classmethod
    def verify(cls, public_key_raw: Union[bytes, str], signature: Union[bytes, str], data: Union[bytes, Dict[str, Any], str]) -> bool:
        """
        Verifies Ed25519 signature against data.
        Accepts hex-encoded or raw byte keys and signatures.
        """
        try:
            pub_bytes = bytes.fromhex(public_key_raw) if isinstance(public_key_raw, str) else public_key_raw
            sig_bytes = bytes.fromhex(signature) if isinstance(signature, str) else signature

            if isinstance(data, dict):
                payload_bytes = cls.canonicalize(data)
            elif isinstance(data, str):
                payload_bytes = data.encode('utf-8')
            else:
                payload_bytes = data

            return verify_data_signature(pub_bytes, sig_bytes, payload_bytes)
        except Exception:
            return False

    @classmethod
    def build_digest(cls, payload: Dict[str, Any]) -> str:
        """Computes deterministic digest over canonical representation of payload."""
        return cls.hash(cls.canonicalize(payload))

    @staticmethod
    def compute_chained_hash(previous_hash: str, record: Dict[str, Any]) -> str:
        """Computes H_i = SHA256(H_{i-1} || Canonical(Record_i))."""
        return compute_chained_hash(previous_hash, record)

    @staticmethod
    def verify_chain(chain_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cryptographically verifies continuity and hash integrity of append-only chain."""
        return verify_hash_chain(chain_records)
