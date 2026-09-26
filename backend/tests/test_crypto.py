"""
Unit Tests for DRISHTRA Cryptographic Engine
"""
import pytest
from app.crypto.canonicalization import canonicalize_json
from app.crypto.hashing import sha256_bytes, sha256_canonical_dict
from app.crypto.signing import generate_keypair, sign_data, verify_data_signature
from app.crypto.chain import compute_chained_hash, verify_hash_chain, GENESIS_HASH

def test_canonical_json_determinism():
    dict1 = {"b": 2, "a": 1, "c": [3, 2, 1]}
    dict2 = {"a": 1, "c": [3, 2, 1], "b": 2}
    assert canonicalize_json(dict1) == canonicalize_json(dict2)
    assert sha256_canonical_dict(dict1) == sha256_canonical_dict(dict2)

def test_ed25519_sign_and_verify():
    priv, pub = generate_keypair()
    msg = b"SOVEREIGN_MILITARY_CV_ASSURANCE_PAYLOAD"
    sig = sign_data(priv, msg)
    assert verify_data_signature(pub, sig, msg) is True
    # Tampered message
    assert verify_data_signature(pub, sig, b"TAMPERED_PAYLOAD") is False

def test_hash_chain_tamper_detection():
    r1 = {"seq": 1, "data": "Alpha"}
    h1 = compute_chained_hash(GENESIS_HASH, r1)
    
    r2 = {"seq": 2, "data": "Beta"}
    h2 = compute_chained_hash(h1, r2)

    chain = [
        {"previous_hash": GENESIS_HASH, "record_hash": h1, "seq": 1, "data": "Alpha"},
        {"previous_hash": h1, "record_hash": h2, "seq": 2, "data": "Beta"}
    ]
    res_valid = verify_hash_chain(chain)
    assert res_valid["status"] == "VALID"
    assert res_valid["verified_count"] == 2

    # Tamper with Beta
    chain_tampered = [
        {"previous_hash": GENESIS_HASH, "record_hash": h1, "seq": 1, "data": "Alpha"},
        {"previous_hash": h1, "record_hash": h2, "seq": 2, "data": "Beta_MODIFIED"}
    ]
    res_tampered = verify_hash_chain(chain_tampered)
    assert res_tampered["status"] == "TAMPERED_RECORD"
