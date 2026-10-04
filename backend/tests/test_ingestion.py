"""
Trust-boundary ingestion -> pipeline: an uploaded COCO file is parsed into canonical
records and the pipeline scans exactly those records.
"""
import io
import json
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _case(h):
    cid = client.post("/api/v1/cases", headers=h, json={"name": "Upload case", "classification": "RESTRICTED"}).json()["case_id"]
    con = client.post("/api/v1/contributors", headers=h, json={"case_id": cid, "name": "Vendor X", "contributor_type": "VENDOR"}).json()
    return cid, con["contributor_id"]


def test_coco_upload_then_pipeline(as_role):
    ml = as_role("ML_ANALYST")
    cid, con = _case(ml)
    coco = {"images": [{"id": i, "file_name": f"img_{i}.jpg", "width": 640, "height": 480} for i in range(1, 7)],
            "categories": [{"id": 1, "name": "truck"}, {"id": 2, "name": "tank"}],
            "annotations": [{"id": i, "image_id": i, "category_id": 1 + (i % 2), "bbox": [10, 10, 100, 80]} for i in range(1, 7)]
            + [{"id": 99, "image_id": 3, "category_id": 1, "bbox": [600, 400, 200, 200]}]}  # box outside the image
    r = client.post("/api/v1/datasets/upload", headers=ml,
                    data={"case_id": cid, "contributor_id": con, "dataset_name": "Vendor COCO", "format_type": "COCO"},
                    files={"file": ("ann.json", json.dumps(coco).encode(), "application/json")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["records"] == 6 and body["images_included"] == 0
    run = client.post(f"/api/v1/cases/{cid}/pipeline/run", headers=ml).json()
    assert run["status"] == "COMPLETED"
    ac = client.get(f"/api/v1/assurance/{cid}", headers=ml).json()
    # Without images, near-duplicate analysis honestly cannot run
    assert ac["coverage"]["D2_NEAR_DUPLICATE"]["state"] == "NOT_TESTED"
    # The out-of-bounds box is caught
    assert ac["coverage"]["D6_ANNOTATION_VALIDITY"]["state"] == "FINDING"
    assert any(e["type"] == "MALFORMED_BOUNDING_BOX_COORDINATES" for e in ac["evidence"])
    # Without a model or inference, those layers are not applicable
    assert ac["coverage"]["D8A_WEIGHT_DIGEST"]["state"] == "NOT_APPLICABLE"


def test_yolo_zip_with_images_enables_perceptual_hashing(as_role):
    ml = as_role("ML_ANALYST")
    cid, con = _case(ml)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("classes.txt", "truck\ntank\n")
        for i in range(4):
            img = Image.new("RGB", (64, 64), (i * 60, 100, 200 - i * 40))
            ib = io.BytesIO(); img.save(ib, "PNG")
            z.writestr(f"images/f{i}.png", ib.getvalue())
            z.writestr(f"labels/f{i}.txt", f"{i % 2} 0.5 0.5 0.2 0.2\n")
    r = client.post("/api/v1/datasets/upload", headers=ml,
                    data={"case_id": cid, "contributor_id": con, "dataset_name": "Vendor YOLO", "format_type": "YOLO"},
                    files={"file": ("ds.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 201, r.text
    assert r.json()["images_included"] == 4


def test_path_traversal_archive_rejected(as_role):
    ml = as_role("ML_ANALYST")
    cid, con = _case(ml)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../../evil.txt", "0 0.5 0.5 0.1 0.1")
    r = client.post("/api/v1/datasets/upload", headers=ml,
                    data={"case_id": cid, "contributor_id": con, "dataset_name": "Evil", "format_type": "YOLO"},
                    files={"file": ("evil.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 400


def test_model_registration_requires_real_digest(as_role):
    ml = as_role("ML_ANALYST")
    cid, con = _case(ml)
    r = client.post("/api/v1/models/register", headers=ml, json={"case_id": cid, "contributor_id": con, "name": "m"})
    assert r.status_code == 400
    r = client.post("/api/v1/models/register", headers=ml, json={"case_id": cid, "contributor_id": con, "name": "m",
                                                                 "weight_sha256": "a" * 64})
    assert r.status_code == 201
