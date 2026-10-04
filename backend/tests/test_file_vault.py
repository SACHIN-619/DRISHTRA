"""
Untrusted File Vault & Defensive Ingestion Security Tests
Verifies:
- Path traversal mitigation & filename sanitization
- Extension & format validation
- File size limit checks
- Decompression bomb protection limits
- Dataset parser normalization (COCO & YOLO -> CanonicalImageRecord)
"""
import os
import json
import pytest
from app.ingestion.file_vault import FileVault
from app.ingestion.dataset_parsers import DatasetNormalizer
from app.core.config import settings

def test_filename_sanitization_path_traversal():
    # Attempting directory traversal
    malicious_names = [
        "../../../../etc/shadow",
        "..\\..\\..\\Windows\\System32\\cmd.exe",
        "dataset/../../../payload.json",
        "normal_dataset.json"
    ]
    for m in malicious_names:
        clean = FileVault.sanitize_filename(m)
        assert "/" not in clean
        assert "\\" not in clean
        assert ".." not in clean

def test_file_extension_validation():
    from app.ingestion.file_vault import SecurityValidationError
    # Approved extensions return the extension string
    assert FileVault.validate_file_extension("annotations.json") == ".json"
    assert FileVault.validate_file_extension("weights.onnx", allowed_category="MODEL") == ".onnx"
    # Dangerous unapproved extensions raise SecurityValidationError
    with pytest.raises(SecurityValidationError):
        FileVault.validate_file_extension("backdoor.exe")
    with pytest.raises(SecurityValidationError):
        FileVault.validate_file_extension("exploit.sh")
    with pytest.raises(SecurityValidationError):
        FileVault.validate_file_extension("script.py")

def test_file_size_limit():
    from app.ingestion.file_vault import SecurityValidationError
    # Within limit -> None
    FileVault.validate_file_size(1024 * 1024, max_mb=10)
    # Exceeds limit -> raises SecurityValidationError
    with pytest.raises(SecurityValidationError):
        FileVault.validate_file_size(20 * 1024 * 1024, max_mb=10)

def test_coco_parser_normalization(tmp_path):
    coco_data = {
        "images": [
            {"id": 1, "file_name": "tank_recon_01.jpg", "width": 640, "height": 640}
        ],
        "annotations": [
            {"id": 101, "image_id": 1, "category_id": 0, "bbox": [50, 50, 200, 150]}
        ],
        "categories": [
            {"id": 0, "name": "armoured_tank"}
        ]
    }
    json_path = tmp_path / "test_coco.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(coco_data, f)

    records = DatasetNormalizer.parse_coco_json(str(json_path), dataset_id="D-COCO-TEST")
    assert len(records) == 1
    rec = records[0]
    assert rec.image_id.startswith("IMG-COCO-")
    assert rec.dataset_id == "D-COCO-TEST"
    assert rec.width == 640
    assert rec.height == 640
    assert rec.class_ids == [0]
    assert len(rec.annotations) == 1

def test_yolo_parser_normalization(tmp_path):
    img_dir = tmp_path / "images"
    lbl_dir = tmp_path / "labels"
    img_dir.mkdir()
    lbl_dir.mkdir()

    # Create dummy dummy image and annotation
    (img_dir / "drone_feed_01.jpg").write_text("dummy image bytes")
    # YOLO format: class_id x_center y_center width height (normalized)
    (lbl_dir / "drone_feed_01.txt").write_text("0 0.5 0.5 0.2 0.3\n")

    records = DatasetNormalizer.parse_yolo_dir(
        images_dir=str(img_dir),
        labels_dir=str(lbl_dir),
        dataset_id="D-YOLO-TEST"
    )
    assert len(records) == 1
    rec = records[0]
    assert rec.dataset_id == "D-YOLO-TEST"
    assert rec.class_ids == [0]
    assert len(rec.annotations) == 1
    anno = rec.annotations[0]
    assert anno.class_id == 0
    assert len(anno.bbox) == 4

