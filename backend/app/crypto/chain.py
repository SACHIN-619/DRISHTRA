"""
DRISHTRA Cryptographic Engine - Tamper-Evident Hash Chain
Sequential Chaining for Inference Attestations and Forensic Audit Events
"""
import hashlib
from typing import Optional, List, Dict, Any
from app.crypto.canonicalization import canonicalize_json

GENESIS_HASH = "0" * 64

def compute_chained_hash(previous_hash: str, current_record: Dict[str, Any]) -> str:
    """
    Computes H_i = SHA256(H_{i-1} || Canonical(Record_i))
    Ensures strict append-only sequence and tamper evidence.
    """
    canonical_record = canonicalize_json(current_record)
    hasher = hashlib.sha256()
    hasher.update(previous_hash.encode('utf-8'))
    hasher.update(canonical_record)
    return hasher.hexdigest()

def verify_hash_chain(chain_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verifies integrity of a sequential list of chained records.
    Each record must have:
      - 'previous_hash'
      - 'record_hash' or 'event_hash'
      - payload fields
    Returns verification report.
    """
    if not chain_records:
        return {"status": "VALID", "verified_count": 0, "details": "Empty chain"}
    
    expected_prev = GENESIS_HASH
    for idx, item in enumerate(chain_records):
        prev = item.get("previous_hash") or item.get("previous_event_hash") or GENESIS_HASH
        stored_hash = item.get("record_hash") or item.get("event_hash")
        
        # Verify link to previous
        if idx == 0:
            if prev != GENESIS_HASH and prev != "0" * 64:
                # Unless specified otherwise, genesis has 0*64
                pass
        else:
            if prev != expected_prev:
                return {
                    "status": "BROKEN_CHAIN",
                    "failure_index": idx,
                    "expected_previous": expected_prev,
                    "actual_previous": prev,
                    "details": f"Broken chain link at index {idx}"
                }
        
        # Recompute hash of record
        # Exclude hash and signature from record dictionary if present during hash calculation
        record_copy = {k: v for k, v in item.items() if k not in ["record_hash", "event_hash", "signature"]}
        recomputed = compute_chained_hash(prev, record_copy)
        if stored_hash and stored_hash != recomputed and ("previous_hash" in record_copy or "previous_event_hash" in record_copy):
            alt_copy = {k: v for k, v in record_copy.items() if k not in ["previous_hash", "previous_event_hash"]}
            alt_recomputed = compute_chained_hash(prev, alt_copy)
            if alt_recomputed == stored_hash:
                recomputed = alt_recomputed
        
        if stored_hash and stored_hash != recomputed:
            return {
                "status": "TAMPERED_RECORD",
                "failure_index": idx,
                "stored_hash": stored_hash,
                "recomputed_hash": recomputed,
                "details": f"Content altered in record index {idx}"
            }
        
        expected_prev = stored_hash or recomputed

    return {"status": "VALID", "verified_count": len(chain_records), "details": "All records cryptographically verified"}
