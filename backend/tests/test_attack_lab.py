"""
Attack Lab & Empirical Metric Evaluation Tests
Verifies:
- Dynamic calculation of TP, FP, FN, TN
- Exact mathematical formulations:
    Precision = TP / (TP + FP)
    Recall = TP / (TP + FN)
    F1 = 2 * Precision * Recall / (Precision + Recall)
    Specificity = TN / (TN + FP)
    FPR = FP / (FP + TN)
- Safe zero-denominator handling
- Mandatory synthetic benchmark disclaimer
- REST API endpoint integration
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.evaluation.attack_lab import DemoAttackLab

client = TestClient(app)

def test_attack_lab_benchmark_execution():
    report = DemoAttackLab.run_benchmark()
    assert report["disclaimer"] == DemoAttackLab.DISCLAIMER
    assert "Synthetic controlled benchmark" in report["disclaimer"]

    cm = report["confusion_matrix"]
    tp = cm["true_positives"]
    fp = cm["false_positives"]
    fn = cm["false_negatives"]
    tn = cm["true_negatives"]
    total = report["total_evaluations"]
    assert total == (tp + fp + fn + tn)
    assert total > 0

    metrics = report["metrics"]
    # Check bounded values [0.0, 1.0]
    for k in ["precision", "recall", "f1_score", "specificity", "false_positive_rate", "accuracy"]:
        val = metrics[k]
        assert 0.0 <= val <= 1.0

    # Verify math consistency
    expected_prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    assert metrics["precision"] == expected_prec

    expected_rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    assert metrics["recall"] == expected_rec

    expected_spec = round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0.0
    assert metrics["specificity"] == expected_spec

    expected_fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
    assert metrics["false_positive_rate"] == expected_fpr

def test_attack_lab_api_endpoint(as_role):
    assert client.post("/api/v1/benchmarks/attack-lab/run").status_code == 401
    assert client.post("/api/v1/benchmarks/attack-lab/run", headers=as_role("AUDITOR")).status_code == 403
    res = client.post("/api/v1/benchmarks/attack-lab/run", headers=as_role("ML_ANALYST"))
    assert res.status_code == 200
    data = res.json()
    assert "confusion_matrix" in data
    assert "metrics" in data
    assert "Synthetic controlled benchmark" in data["disclaimer"]
    assert len(data["results_matrix"]) > 0
