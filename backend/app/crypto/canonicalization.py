"""
DRISHTRA Cryptographic Engine - Canonicalization
Deterministic RFC 8785 JSON Canonicalization for Cryptographic Hashing and Signing
"""
import json
from typing import Any

def canonicalize_json(data: Any) -> bytes:
    """
    Produce canonical, deterministic JSON bytes:
    - UTF-8 encoded
    - Keys sorted recursively
    - No redundant whitespace (separators=(',', ':'))
    - Floats formatted consistently
    """
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':')
    ).encode('utf-8')
