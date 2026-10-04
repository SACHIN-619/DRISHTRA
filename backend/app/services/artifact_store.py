"""
Assessment-input store inside the local vault.

The pipeline must consume real stored artifacts, not values passed in by a
caller at run time. Three kinds of input are kept here, per asset:

  datasets/<dataset_id>.records.json   canonical sample records (CanonicalImageRecord-like)
  models/<model_id>.probes.json        recorded black-box probe responses from the runtime harness
  models/<model_id>.supplied.json      digest of the model artifact *as delivered*
  signers/<signer>.pub                 Ed25519 public key (hex) of an inference signer

Every write returns the SHA-256 of the canonical content, which the pipeline
records as stage input/output digests (that is how stage-to-stage chaining is
proven in the pipeline trace).
"""
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.crypto.crypto_service import CryptoService

ROOT = os.path.join(settings.BASE_STORAGE_DIR, "assessment_inputs")
_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


def _path(kind: str, name: str, ext: str) -> str:
    if not _SAFE.match(name):
        raise ValueError(f"Unsafe artifact identifier: {name!r}")
    d = os.path.join(ROOT, kind)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{name}.{ext}")


def _write_json(path: str, data: Any) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True, indent=1, default=str)
    return CryptoService.hash(data)


def _read_json(path: str) -> Tuple[Optional[Any], Optional[str]]:
    if not os.path.exists(path):
        return None, None
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data, CryptoService.hash(data)


class ArtifactStore:
    # datasets
    @staticmethod
    def save_dataset_records(dataset_id: str, records: List[Dict[str, Any]], extras: Optional[Dict[str, Any]] = None) -> str:
        return _write_json(_path("datasets", dataset_id, "records.json"),
                           {"dataset_id": dataset_id, "records": records, "extras": extras or {}})

    @staticmethod
    def load_dataset_records(dataset_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return _read_json(_path("datasets", dataset_id, "records.json"))

    # models
    @staticmethod
    def save_model_probes(model_id: str, probes: Dict[str, Any]) -> str:
        return _write_json(_path("models", model_id, "probes.json"), probes)

    @staticmethod
    def load_model_probes(model_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return _read_json(_path("models", model_id, "probes.json"))

    @staticmethod
    def save_supplied_digest(model_id: str, sha256: str, source: str = "delivered artifact") -> str:
        return _write_json(_path("models", model_id, "supplied.json"), {"sha256": sha256, "source": source})

    @staticmethod
    def load_supplied_digest(model_id: str) -> Optional[str]:
        data, _ = _read_json(_path("models", model_id, "supplied.json"))
        return data.get("sha256") if data else None

    # signers
    @staticmethod
    def save_signer_key(signer: str, public_key_hex: str) -> None:
        with open(_path("signers", signer, "pub"), "w", encoding="utf-8") as fh:
            fh.write(public_key_hex.strip())

    @staticmethod
    def load_signer_key(signer: str) -> Optional[str]:
        try:
            p = _path("signers", signer, "pub")
        except ValueError:
            return None
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as fh:
            return fh.read().strip() or None
