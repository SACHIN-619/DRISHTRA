"""
DRISHTRA Dataset Ingestion Parsers
Supports standardized Computer Vision annotation formats:
1. COCO JSON (Images, Annotations, Categories, Bounding Boxes)
2. YOLO TXT / YAML (Normalized Coordinates, Class IDs, Class Names)
"""
import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from collections import Counter
from app.crypto.hashing import sha256_canonical_dict

class DatasetParser:
    @staticmethod
    def parse_coco(coco_data: Dict[str, Any], dataset_name: str = "COCO_Dataset") -> Dict[str, Any]:
        """
        Parses COCO format JSON into normalized DRISHTRA dataset structure.
        Extracts image manifests, category distributions, bounding box densities,
        and computes deterministic fingerprint.
        """
        images = coco_data.get("images", [])
        annotations = coco_data.get("annotations", [])
        categories = {cat["id"]: cat["name"] for cat in coco_data.get("categories", [])}
        
        # Build category distribution
        cat_counts = Counter()
        image_annotations = {}
        for ann in annotations:
            cat_id = ann.get("category_id")
            cat_name = categories.get(cat_id, f"class_{cat_id}")
            cat_counts[cat_name] += 1
            
            img_id = ann.get("image_id")
            if img_id not in image_annotations:
                image_annotations[img_id] = []
            image_annotations[img_id].append({
                "bbox": ann.get("bbox", []),
                "category": cat_name,
                "area": ann.get("area", 0)
            })

        # Process sample records
        samples = []
        for img in images:
            img_id = img["id"]
            file_name = img.get("file_name", f"img_{img_id}.jpg")
            img_anns = image_annotations.get(img_id, [])
            primary_label = img_anns[0]["category"] if img_anns else "background"
            
            # Canonical sample representation
            sample_canonical = {
                "sample_id": f"SMP-COCO-{img_id}",
                "file_name": file_name,
                "width": img.get("width", 640),
                "height": img.get("height", 640),
                "label": primary_label,
                "annotation_count": len(img_anns)
            }
            s_hash = sha256_canonical_dict(sample_canonical)
            
            # Synthetic 64-bit dhash for prototype demonstration if image pixels not provided
            pseudo_phash = hashlib.md5(f"{file_name}_{primary_label}".encode()).hexdigest()[:16]
            
            samples.append({
                "sample_id": sample_canonical["sample_id"],
                "file_name": file_name,
                "label": primary_label,
                "sha256": s_hash,
                "phash": pseudo_phash,
                "annotations": img_anns
            })

        manifest = {
            "dataset_name": dataset_name,
            "format": "COCO",
            "image_count": len(images),
            "annotation_count": len(annotations),
            "category_count": len(categories),
            "categories": categories,
            "class_distribution": dict(cat_counts),
            "samples": samples
        }
        manifest["manifest_sha256"] = sha256_canonical_dict({
            "name": dataset_name,
            "format": "COCO",
            "images": len(images),
            "annotations": len(annotations),
            "categories": categories
        })
        return manifest

    @staticmethod
    def parse_yolo(
        annotations_list: List[Dict[str, Any]], 
        class_names: Optional[List[str]] = None,
        dataset_name: str = "YOLO_Dataset"
    ) -> Dict[str, Any]:
        """
        Parses YOLO format annotations into normalized DRISHTRA dataset structure.
        Each item in annotations_list represents an image with its .txt lines:
        `[{'file_name': 'img1.jpg', 'lines': ['0 0.5 0.5 0.2 0.3', ...]}]`
        """
        classes = class_names or ["target_0", "target_1", "target_2"]
        cat_counts = Counter()
        samples = []

        for idx, item in enumerate(annotations_list):
            file_name = item.get("file_name", f"yolo_img_{idx}.jpg")
            lines = item.get("lines", [])
            boxes = []
            primary_label = "unlabeled"

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    cls_id = int(parts[0])
                    cls_name = classes[cls_id] if cls_id < len(classes) else f"class_{cls_id}"
                    cat_counts[cls_name] += 1
                    boxes.append({
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "x_center": float(parts[1]),
                        "y_center": float(parts[2]),
                        "width": float(parts[3]),
                        "height": float(parts[4])
                    })
                    if primary_label == "unlabeled":
                        primary_label = cls_name

            sample_canonical = {
                "sample_id": f"SMP-YOLO-{idx+1:04d}",
                "file_name": file_name,
                "label": primary_label,
                "box_count": len(boxes)
            }
            s_hash = sha256_canonical_dict(sample_canonical)
            pseudo_phash = hashlib.md5(f"{file_name}_{primary_label}".encode()).hexdigest()[:16]

            samples.append({
                "sample_id": sample_canonical["sample_id"],
                "file_name": file_name,
                "label": primary_label,
                "sha256": s_hash,
                "phash": pseudo_phash,
                "boxes": boxes
            })

        manifest = {
            "dataset_name": dataset_name,
            "format": "YOLO",
            "image_count": len(annotations_list),
            "box_count": sum(len(s["boxes"]) for s in samples),
            "classes": classes,
            "class_distribution": dict(cat_counts),
            "samples": samples
        }
        manifest["manifest_sha256"] = sha256_canonical_dict({
            "name": dataset_name,
            "format": "YOLO",
            "images": len(annotations_list),
            "classes": classes
        })
        return manifest
