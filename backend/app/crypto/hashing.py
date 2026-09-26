"""
DRISHTRA Cryptographic Engine - Hashing
SHA-256 Digest Calculations for Datasets, Models, Inference Artifacts and Manifests
"""
import hashlib
import os
from typing import Any, Union
from app.crypto.canonicalization import canonicalize_json

def sha256_bytes(data: bytes) -> str:
    """Calculate hex-encoded SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()

def sha256_file(filepath: str, chunk_size: int = 65536) -> str:
    """Calculate SHA-256 digest of a local file in streaming chunks."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found for hashing: {filepath}")
    
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def sha256_canonical_dict(data: Any) -> str:
    """Canonicalize dictionary/data structure and return its SHA-256 hex digest."""
    canonical_bytes = canonicalize_json(data)
    return hashlib.sha256(canonical_bytes).hexdigest()

def sha256_combine(*hashes: str) -> str:
    """Combine multiple SHA-256 digests in a deterministic sequence."""
    combined = ":".join(hashes).encode('utf-8')
    return hashlib.sha256(combined).hexdigest()
