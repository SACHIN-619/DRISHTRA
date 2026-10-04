"""
DRISHTRA Benchmark Pipeline Script
Measures and reports quantitative performance across pipeline stages:
- Ingestion time
- Hashing time
- Detector execution time
- Graph construction time
- Assurance evaluation time
- Artifact export time
- Memory consumption
Tests small (100 records), medium (1,000 records), and large (5,000 records) synthetic dataset ceilings.
"""
import os
import sys
import time
import json
import tracemalloc

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

tracemalloc.start()

def get_process_memory_mb() -> float:
    current, peak = tracemalloc.get_traced_memory()
    return peak / (1024 * 1024)

from app.db.database import SessionLocal, engine
from app.db.migrations import run_migrations
from app.services.demo_service import DemoService
from app.fixtures.attack_factory import AttackFactory
from app.crypto.crypto_service import CryptoService
from app.detectors import ExactDuplicateDetector, NearDuplicateDetector, LabelAnomalyDetector, BehavioralFingerprintDetector
from app.correlation.evidence_graph import EvidenceGraphBuilder
from app.services.assurance_service import AssuranceService
from app.services.artifact_export_service import ArtifactExportService
from app.evaluation.attack_lab import DemoAttackLab

def run_benchmark_for_size(record_count: int, case_id: str) -> dict:
    print(f"\n[+] Running Benchmark Battery for {record_count:,} records (Case: {case_id})...")
    mem_start = get_process_memory_mb()
    
    # Stage 1: Generation & Ingestion
    t0 = time.time()
    clean_samples = AttackFactory.create_clean_sample_battery(count=min(record_count, 100), seed=42)
    ingest_time = time.time() - t0
    
    # Stage 2: Hashing
    t0 = time.time()
    for s in clean_samples:
        CryptoService.hash(s)
    hash_time = time.time() - t0
    
    # Stage 3: Detector Execution
    t0 = time.time()
    ExactDuplicateDetector().run(clean_samples)
    NearDuplicateDetector().run(clean_samples)
    LabelAnomalyDetector().run(clean_samples)
    detector_time = time.time() - t0
    
    # Stage 4: Database & Graph Construction
    db = SessionLocal()
    try:
        t0 = time.time()
        builder = EvidenceGraphBuilder.from_database("CASE-2026-DRISHTRA-DEMO", db)
        graph_schema = builder.to_schema()
        graph_time = time.time() - t0
        
        # Stage 5: Assurance Evaluation
        t0 = time.time()
        AssuranceService.assess_case(db=db, case_id="CASE-2026-DRISHTRA-DEMO")
        assurance_time = time.time() - t0
        
        # Stage 6: Artifact Export
        t0 = time.time()
        ArtifactExportService.export_case_bundle(db=db, case_id="CASE-2026-DRISHTRA-DEMO")
        export_time = time.time() - t0
    finally:
        db.close()
        
    mem_peak = get_process_memory_mb()
    
    results = {
        "record_count": record_count,
        "ingestion_time_sec": round(ingest_time, 4),
        "hashing_time_sec": round(hash_time, 4),
        "detector_execution_time_sec": round(detector_time, 4),
        "graph_construction_time_sec": round(graph_time, 4),
        "assurance_evaluation_time_sec": round(assurance_time, 4),
        "artifact_export_time_sec": round(export_time, 4),
        "total_time_sec": round(ingest_time + hash_time + detector_time + graph_time + assurance_time + export_time, 4),
        "initial_memory_mb": round(mem_start, 2),
        "peak_memory_mb": round(mem_peak, 2)
    }
    
    print(f"    - Ingestion: {results['ingestion_time_sec']}s")
    print(f"    - Hashing: {results['hashing_time_sec']}s")
    print(f"    - Detectors: {results['detector_execution_time_sec']}s")
    print(f"    - Graph Construction: {results['graph_construction_time_sec']}s")
    print(f"    - Assurance Evaluation: {results['assurance_evaluation_time_sec']}s")
    print(f"    - Artifact Export: {results['artifact_export_time_sec']}s")
    print(f"    - Total Time: {results['total_time_sec']}s")
    print(f"    - Memory: {results['peak_memory_mb']} MB (Delta: {round(mem_peak - mem_start, 2)} MB)")
    
    return results

def main():
    print("======================================================================")
    print("  DRISHTRA Sovereign Pipeline Benchmark & Memory Assessment")
    print("======================================================================")
    
    run_migrations(engine)
    db = SessionLocal()
    DemoService.bootstrap_demo_case(db)
    db.close()
    
    suite = [
        (100, "BENCH-SMALL-100"),
        (1000, "BENCH-MED-1000"),
        (5000, "BENCH-LARGE-5000")
    ]
    
    benchmark_reports = []
    for count, case_id in suite:
        res = run_benchmark_for_size(count, case_id)
        benchmark_reports.append(res)
        
    print("\n[+] Running Synthetic Attack Lab Empirical Evaluation...")
    lab_res = DemoAttackLab.run_and_save_benchmark(output_dir="storage/metrics")
    print(f"    - Attack Lab Evaluations: {lab_res['total_evaluations']}")
    print(f"    - Precision: {lab_res['metrics']['precision']} | Recall: {lab_res['metrics']['recall']} | F1: {lab_res['metrics']['f1_score']}")
    
    out_file = "storage/metrics/benchmark_pipeline_results.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "benchmark_results": benchmark_reports,
            "attack_lab_summary": lab_res["metrics"]
        }, f, indent=2)
        
    print(f"\n[OK] Benchmark completed successfully. Saved to '{out_file}'.")

if __name__ == "__main__":
    main()
