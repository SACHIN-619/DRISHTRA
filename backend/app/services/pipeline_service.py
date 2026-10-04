"""
DRISHTRA 18-stage case pipeline.

Each stage records:
  status          SUCCESS | SKIPPED (nothing to do / inputs absent) | FAILED
  input_digest    SHA-256 of what the stage consumed
  output_digest   SHA-256 of what the stage produced
so the trace proves that stage N consumed stage N-1's actual output
(e.g. stage 05's input_digest == stage 04's output_digest).

Inputs come only from the case's stored records and the local assessment-input
store (see artifact_store.py) - never from values supplied at run time - so a
re-run on the same stored artifacts is reproducible, and mutating one stored
artifact propagates through to the assurance case.

No stage reports SUCCESS for work it did not do: a check whose inputs are
missing is recorded as NOT_TESTED in coverage and the stage as SKIPPED.
"""
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.correlation.evidence_graph import EvidenceGraphBuilder
from app.crypto.crypto_service import CryptoService
from app.db.models import (
    Case, Contributor, Dataset, Evidence, Finding, InferenceRecord, ModelAsset,
    PipelineRun, RuntimeBinding, utc_now_iso,
)
from app.schemas.all_schemas import PipelineRunResponse, StageResult
from app.services.artifact_export_service import ArtifactExportService
from app.services.artifact_store import ArtifactStore
from app.services.assurance_service import AssuranceService
from app.services.audit_service import AuditService
from app.services.dataset_service import DatasetService
from app.services.inference_service import InferenceService
from app.services.model_service import ModelService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

STAGES = [
    ("STAGE_01_CASE_VALIDATION", "Case validation"),
    ("STAGE_02_CONTRIBUTOR_REGISTRATION", "Contributor verification"),
    ("STAGE_03_DATASET_INGESTION", "Dataset ingestion"),
    ("STAGE_04_DATASET_NORMALIZATION", "Dataset normalization"),
    ("STAGE_05_DATASET_INTEGRITY_SCAN", "Dataset integrity scan (D1–D7)"),
    ("STAGE_06_MODEL_REGISTRATION", "Model registration"),
    ("STAGE_07_MODEL_INSPECTION", "Model identity & digest (D8A)"),
    ("STAGE_08_MODEL_BEHAVIOURAL_EVALUATION", "Model behavioural probes (D8B/C)"),
    ("STAGE_09_RUNTIME_CONFIG_BINDING", "Runtime configuration binding"),
    ("STAGE_10_INFERENCE_ATTESTATION_INGESTION", "Inference attestation ingestion"),
    ("STAGE_11_CRYPTOGRAPHIC_VERIFICATION", "Signature & replay verification (D9)"),
    ("STAGE_12_EVIDENCE_NORMALIZATION", "Evidence normalization"),
    ("STAGE_13_CROSS_LIFECYCLE_CORRELATION", "Cross-lifecycle correlation"),
    ("STAGE_14_COUNTER_EVIDENCE_EVALUATION", "Counter-evidence evaluation"),
    ("STAGE_15_ASSURANCE_CASE_CONSTRUCTION", "Assurance case construction"),
    ("STAGE_16_AUDIT_LEDGER_COMMITMENT", "Audit ledger commitment"),
    ("STAGE_17_REPORT_GENERATION", "Machine report generation"),
    ("STAGE_18_COMPLETION_AND_COVERAGE", "Completion, coverage & export"),
]
REQUIRED_RECORD_KEYS = ("sample_id", "sha256", "label")


class PipelineStageError(Exception):
    def __init__(self, stage_id: str, message: str):
        super().__init__(message)
        self.stage_id = stage_id
        self.message = message


def _digest(obj: Any) -> str:
    return CryptoService.hash(json.loads(json.dumps(obj, default=str)))


def _model_supplied_digest(m: ModelAsset) -> (Optional[str], str):
    """Digest of the model artifact as delivered, and where it came from."""
    if m.location and os.path.isfile(m.location):
        real = os.path.realpath(m.location)
        if real.startswith(os.path.realpath(settings.BASE_STORAGE_DIR)):
            return CryptoService.hash_file(real), "vault file"
    supplied = ArtifactStore.load_supplied_digest(m.model_id)
    if supplied:
        return supplied, "recorded delivery digest"
    return None, "no delivered artifact in vault"


class CasePipeline:
    @classmethod
    def run(
        cls,
        db: Session,
        case_id: str,
        actor: str = "pipeline_orchestrator",
        on_event: Optional[Any] = None,
        pace_ms: int = 0,
        **_legacy_kwargs: Any,  # sample_battery / probe_battery / public_key_hex are no longer accepted
    ) -> PipelineRunResponse:
        """Run the 18 stages. ``on_event(dict)`` is called live as each stage starts and finishes
        (used by the streaming endpoint). ``pace_ms`` inserts a visible pause *between* stages for
        presentations; reported stage durations are always the real compute time."""
        from app.db.models import CheckExecution, Finding

        def emit(evt: Dict[str, Any]) -> None:
            if on_event:
                try:
                    on_event(evt)
                except Exception:  # a disconnected viewer must never break a run
                    pass
        run_id = f"RUN-{uuid.uuid4().hex[:10].upper()}"
        run = PipelineRun(run_id=run_id, case_id=case_id, status="RUNNING",
                          current_stage=STAGES[0][0], stages_json="[]", started_at=utc_now_iso())
        db.add(run)
        db.commit()

        stages: List[StageResult] = []
        ctx: Dict[str, Any] = {}
        error: Optional[str] = None

        emit({"type": "run_started", "run_id": run_id, "case_id": case_id,
              "stages": [{"stage_id": a, "stage_name": b} for a, b in STAGES]})

        def stage(idx: int, fn):
            sid, name = STAGES[idx]
            run.current_stage = sid
            db.commit()
            emit({"type": "stage_started", "index": idx, "stage_id": sid, "stage_name": name})
            if pace_ms:
                time.sleep(min(pace_ms, 1500) / 1000.0)  # presentation pause; not counted in duration_ms
            seen_checks = {e for (e,) in db.query(CheckExecution.execution_id).filter(CheckExecution.case_id == case_id).all()}
            t0 = time.time()
            try:
                out = fn() or {}
            except PipelineStageError:
                raise
            except Exception as exc:  # any unexpected failure halts the run honestly
                raise PipelineStageError(sid, f"{name} failed: {exc}") from exc
            new_checks = [c for c in db.query(CheckExecution).filter(CheckExecution.case_id == case_id).all()
                          if c.execution_id not in seen_checks]
            if new_checks:
                fids = [f for c in new_checks for f in json.loads(c.finding_ids_json or "[]")]
                sev = {f.finding_id: (f.severity, f.finding_type) for f in db.query(Finding).filter(Finding.finding_id.in_(fids)).all()} if fids else {}
                out.setdefault("output", {})
                out["output"]["checks_executed"] = [
                    {"check_id": c.check_id, "asset_id": c.asset_id, "outcome": c.outcome, "detail": (c.detail or "")[:220],
                     "findings": [{"finding_id": f, "severity": sev.get(f, ("", ""))[0], "title": sev.get(f, ("", ""))[1]}
                                  for f in json.loads(c.finding_ids_json or "[]")]}
                    for c in new_checks]
            res = StageResult(
                stage_id=sid, stage_name=name, status=out.get("status", "SUCCESS"),
                duration_ms=round((time.time() - t0) * 1000, 2),
                input_summary=out.get("input", {}), output_summary=out.get("output", {}),
                evidence_generated=out.get("evidence", 0),
                artifacts_generated=out.get("artifacts", []),
                warnings=out.get("warnings", []),
            )
            stages.append(res)
            run.stages_json = json.dumps([s.model_dump() for s in stages])
            db.commit()
            emit({"type": "stage_completed", "index": idx, "stage": res.model_dump()})
            return out

        try:
            # 01 ------------------------------------------------------------
            def s01():
                case = db.query(Case).filter(Case.case_id == case_id).first()
                if not case:
                    raise PipelineStageError(STAGES[0][0], f"Case '{case_id}' does not exist.")
                ctx["case"] = case
                out = {"case_id": case.case_id, "classification": case.classification}
                return {"input": {"case_id": case_id}, "output": {**out, "output_digest": _digest(out)}}
            stage(0, s01)

            # 02 ------------------------------------------------------------
            def s02():
                contribs = db.query(Contributor).filter(Contributor.case_id == case_id).all()
                ctx["contributors"] = {c.contributor_id: c for c in contribs}
                datasets = db.query(Dataset).filter(Dataset.case_id == case_id).all()
                models = db.query(ModelAsset).filter(ModelAsset.case_id == case_id).all()
                ctx["datasets"], ctx["models"] = datasets, models
                orphans = [a for a in [d.contributor_id for d in datasets] + [m.contributor_id for m in models]
                           if a not in ctx["contributors"]]
                if orphans:
                    raise PipelineStageError(STAGES[1][0], f"Assets reference unregistered contributors: {sorted(set(orphans))}")
                out = {"contributors": sorted(ctx["contributors"])}
                warn = [f"{c.contributor_id} has no registered public key" for c in contribs if not c.public_key]
                return {"input": {"case_id": case_id}, "output": {**out, "output_digest": _digest(out)}, "warnings": warn}
            stage(1, s02)

            # 03 ------------------------------------------------------------
            def s03():
                loaded, missing = {}, []
                for d in ctx["datasets"]:
                    data, dg = ArtifactStore.load_dataset_records(d.dataset_id)
                    if data:
                        loaded[d.dataset_id] = {"data": data, "digest": dg}
                    else:
                        missing.append(d.dataset_id)
                ctx["raw_datasets"] = loaded
                out = {did: v["digest"] for did, v in loaded.items()}
                return {
                    "status": "SUCCESS" if loaded else "SKIPPED",
                    "input": {"datasets_registered": [d.dataset_id for d in ctx["datasets"]]},
                    "output": {"record_sets": out, "output_digest": _digest(out)},
                    "warnings": [f"{m}: no stored sample records in vault (dataset checks will be NOT_TESTED)" for m in missing],
                }
            stage(2, s03)

            # 04 ------------------------------------------------------------
            def s04():
                normalized, rejected = {}, {}
                for did, v in ctx["raw_datasets"].items():
                    good, bad = [], 0
                    for r in v["data"].get("records", []):
                        if all(k in r and r[k] not in (None, "") for k in REQUIRED_RECORD_KEYS):
                            good.append(r)
                        else:
                            bad += 1
                    normalized[did] = {"records": good, "extras": v["data"].get("extras", {}), "digest": _digest(good)}
                    rejected[did] = bad
                ctx["normalized"] = normalized
                out = {did: n["digest"] for did, n in normalized.items()}
                return {
                    "status": "SUCCESS" if normalized else "SKIPPED",
                    "input": {"record_sets": {did: v["digest"] for did, v in ctx["raw_datasets"].items()}},
                    "output": {"canonical_sets": out, "rejected_records": rejected, "output_digest": _digest(out)},
                }
            stage(3, s04)

            # 05 ------------------------------------------------------------
            def s05():
                produced = 0
                for did, n in ctx["normalized"].items():
                    ex = n["extras"]
                    produced += len(DatasetService.scan_dataset(
                        db, did, n["records"], actor=actor,
                        embeddings=ex.get("embeddings"), reference_profile=ex.get("reference_profile"),
                        operational_metrics=ex.get("operational_metrics"),
                        operational_metadata=ex.get("operational_metadata"),
                    ))
                return {
                    "status": "SUCCESS" if ctx["normalized"] else "SKIPPED",
                    "input": {"canonical_sets": {did: n["digest"] for did, n in ctx["normalized"].items()}},
                    "output": {"findings_produced": produced, "datasets_scanned": sorted(ctx["normalized"])},
                    "evidence": produced,
                }
            stage(4, s05)

            # 06 ------------------------------------------------------------
            def s06():
                out = {m.model_id: {"registered_sha256": m.weight_sha256, "format": m.format,
                                    "access_level": m.access_level} for m in ctx["models"]}
                return {"status": "SUCCESS" if out else "SKIPPED", "input": {"case_id": case_id},
                        "output": {"models": out, "output_digest": _digest(out)}}
            stage(5, s06)

            # 07 ------------------------------------------------------------
            def s07():
                results, warns, produced = {}, [], 0
                for m in ctx["models"]:
                    supplied, source = _model_supplied_digest(m)
                    results[m.model_id] = {"supplied_sha256": supplied, "source": source}
                    if supplied is None:
                        warns.append(f"{m.model_id}: {source} (digest check NOT_TESTED)")
                    produced += len(ModelService.scan_model(db, m.model_id, supplied or "", actor=actor,
                                                            run_digest=True, run_behaviour=False))
                return {"status": "SUCCESS" if ctx["models"] else "SKIPPED",
                        "input": {"registered": {m.model_id: m.weight_sha256 for m in ctx["models"]}},
                        "output": {"digest_inputs": results, "findings_produced": produced,
                                   "output_digest": _digest(results)},
                        "warnings": warns, "evidence": produced}
            stage(6, s07)

            # 08 ------------------------------------------------------------
            def s08():
                produced, used, warns = 0, {}, []
                for m in ctx["models"]:
                    probes, dg = ArtifactStore.load_model_probes(m.model_id)
                    used[m.model_id] = dg
                    if not probes:
                        warns.append(f"{m.model_id}: no recorded probe responses (behavioural check NOT_TESTED)")
                    produced += len(ModelService.scan_model(db, m.model_id, "", probe_responses=probes,
                                                            actor=actor, run_digest=False, run_behaviour=True))
                return {"status": "SUCCESS" if ctx["models"] else "SKIPPED",
                        "input": {"probe_sets": used},
                        "output": {"findings_produced": produced}, "warnings": warns, "evidence": produced}
            stage(7, s08)

            # 09 ------------------------------------------------------------
            def s09():
                rts = db.query(RuntimeBinding).filter(RuntimeBinding.case_id == case_id).all()
                ctx["runtimes"] = rts
                out = {r.runtime_id: {"model_id": r.model_id, "config_digest": r.config_digest} for r in rts}
                unbound = [m.model_id for m in ctx["models"] if m.model_id not in {r.model_id for r in rts}]
                return {"status": "SUCCESS" if rts else "SKIPPED", "input": {"models": [m.model_id for m in ctx["models"]]},
                        "output": {"bindings": out, "output_digest": _digest(out)},
                        "warnings": [f"{u}: no runtime configuration binding" for u in unbound]}
            stage(8, s09)

            # 10 ------------------------------------------------------------
            def s10():
                infs = db.query(InferenceRecord).filter(InferenceRecord.case_id == case_id) \
                    .order_by(InferenceRecord.sequence.asc()).all()
                ctx["inferences"] = infs
                keys = {i.inference_id: ArtifactStore.load_signer_key(i.signer or "") for i in infs}
                ctx["signer_keys"] = keys
                out = {i.inference_id: {"signer": i.signer, "key_resolved": bool(keys[i.inference_id]),
                                        "record_digest": _digest({"in": i.input_sha256, "model": i.model_sha256,
                                                                  "out": i.output_sha256, "nonce": i.nonce})}
                       for i in infs}
                return {"status": "SUCCESS" if infs else "SKIPPED", "input": {"case_id": case_id},
                        "output": {"attestations": out, "output_digest": _digest(out)},
                        "warnings": [f"{k}: signer public key not on record (signature check NOT_TESTED)"
                                     for k, v in keys.items() if not v]}
            stage(9, s10)

            # 11 ------------------------------------------------------------
            def s11():
                statuses = {}
                produced = 0
                for i in ctx["inferences"]:
                    r = InferenceService.verify_inference(db, i.inference_id, ctx["signer_keys"].get(i.inference_id), actor=actor)
                    statuses[i.inference_id] = r["verification_status"]
                    produced += r["findings_count"]
                return {"status": "SUCCESS" if ctx["inferences"] else "SKIPPED",
                        "input": {"attestations": [i.inference_id for i in ctx["inferences"]]},
                        "output": {"verification": statuses, "output_digest": _digest(statuses)},
                        "evidence": produced}
            stage(10, s11)

            # 12 ------------------------------------------------------------
            def s12():
                findings = db.query(Finding).filter(Finding.case_id == case_id).all()
                added = 0
                for f in findings:
                    if not db.query(Evidence).filter(Evidence.finding_id == f.finding_id).first():
                        db.add(Evidence(
                            evidence_id=f"EVD-{uuid.uuid4().hex[:8].upper()}", case_id=case_id, finding_id=f.finding_id,
                            target_type=f.asset_type, target_id=f.asset_id, lifecycle_stage=f.asset_type,
                            detector_id=f.detector_id, finding_type=f.finding_type,
                            evidence_type="CRYPTOGRAPHIC" if f.deterministic else "STATISTICAL",
                            severity=f.severity, status=f.status, source_asset=f.asset_id, detector=f.detector_id,
                            observation=f.explanation, confidence=f.confidence, deterministic=f.deterministic,
                            timestamp=utc_now_iso(), sha256=CryptoService.hash(f.explanation),
                        ))
                        added += 1
                db.commit()
                ids = sorted(f.finding_id for f in findings)
                return {"input": {"findings": len(findings)},
                        "output": {"evidence_records_added": added, "output_digest": _digest(ids)}}
            stage(11, s12)

            # 13 ------------------------------------------------------------
            def s13():
                builder = EvidenceGraphBuilder.from_database(case_id, db)
                findings = db.query(Finding).filter(Finding.case_id == case_id).all()
                conv = builder.analyze_cross_lifecycle_convergence(findings)
                out = {"nodes": builder.graph.number_of_nodes(), "edges": builder.graph.number_of_edges(),
                       "converged": conv["converged"], "layers": conv["lifecycle_boundaries"]}
                return {"input": {"findings": len(findings)}, "output": {**out, "output_digest": _digest(out)}}
            stage(12, s13)

            # 14 ------------------------------------------------------------
            def s14():
                inputs = AssuranceService.collect_inputs(db, case_id)
                passed = [e for e in inputs["executions"] if e["outcome"] == "PASS"]
                outcomes: Dict[str, int] = {}
                for e in inputs["executions"]:
                    outcomes[e["outcome"]] = outcomes.get(e["outcome"], 0) + 1
                return {"input": {"check_executions": len(inputs["executions"])},
                        "output": {"counter_evidence_items": len(passed), "outcomes": outcomes,
                                   "output_digest": _digest(sorted(e["execution_id"] for e in passed))}}
            stage(13, s14)

            # 15 ------------------------------------------------------------
            def s15():
                ac = AssuranceService.assess_case(db, case_id, actor=actor)
                ctx["assurance"] = ac
                out = {"assurance_id": ac.assurance_id, "status": ac.status,
                       "recommended_disposition": ac.recommended_disposition}
                return {"input": {"policy": ac.policy_version}, "output": {**out, "output_digest": _digest(out)}}
            stage(14, s15)

            # 16 ------------------------------------------------------------
            def s16():
                trace_digest = _digest([s.model_dump() for s in stages])
                ev = AuditService.record_event(
                    db=db, case_id=case_id, actor=actor, action="PIPELINE_RUN_COMPLETED", asset_id=run_id,
                    result="SUCCESS",
                    reason=json.dumps({"assurance_id": ctx["assurance"].assurance_id,
                                       "trace_digest_stages_01_15": trace_digest}, sort_keys=True),
                )
                chain = AuditService.verify_case_audit(db, case_id)
                return {"input": {"trace_digest": trace_digest},
                        "output": {"event_id": ev.event_id, "event_hash": ev.event_hash, "chain_status": chain.get("status")}}
            stage(15, s16)

            # 17 ------------------------------------------------------------
            def s17():
                report = ReportService.generate_case_report(db, case_id)
                return {"input": {"assurance_id": ctx["assurance"].assurance_id},
                        "output": {"report_id": report.get("report_id"), "output_digest": _digest(report)}}
            stage(16, s17)

            # 18 ------------------------------------------------------------
            def s18():
                exported = ArtifactExportService.export_all_stage_artifacts(db, case_id)
                trace = {
                    "run_id": run_id, "case_id": case_id, "actor": actor,
                    "stages": [s.model_dump() for s in stages],
                    "chaining_checks": cls.chaining_checks(stages),
                }
                case_dir = os.path.join(settings.ARTIFACTS_DIR, case_id)
                os.makedirs(case_dir, exist_ok=True)
                trace_path = os.path.join(case_dir, f"pipeline_trace_{run_id}.json")
                with open(trace_path, "w", encoding="utf-8") as fh:
                    json.dump(trace, fh, indent=2, default=str)
                return {"input": {"case_id": case_id},
                        "output": {"artifacts_exported": len(exported) + 1,
                                   "chaining_checks_passed": all(c["linked"] for c in trace["chaining_checks"])},
                        "artifacts": [os.path.basename(p) for p in list(exported.values()) + [trace_path]]}
            stage(17, s18)

            run.status = "COMPLETED"
        except PipelineStageError as e:
            logger.error(f"[!] Pipeline halted at {e.stage_id}: {e.message}")
            error = e.message
            stages.append(StageResult(stage_id=e.stage_id, stage_name=dict(STAGES).get(e.stage_id, e.stage_id),
                                      status="FAILED", errors=[e.message]))
            run.status = "FAILED"
            run.error_message = error

        run.completed_at = utc_now_iso()
        run.stages_json = json.dumps([s.model_dump() for s in stages])
        db.commit()
        if error:
            emit({"type": "stage_failed", "stage": stages[-1].model_dump()})
        emit({"type": "run_finished", "run_id": run.run_id, "status": run.status, "error": error})
        return PipelineRunResponse(
            run_id=run.run_id, case_id=run.case_id, status=run.status, current_stage=run.current_stage,
            stages=stages, started_at=run.started_at, completed_at=run.completed_at, error_message=error,
        )

    @staticmethod
    def chaining_checks(stages: List[StageResult]) -> List[Dict[str, Any]]:
        """Verify that consuming stages used the producing stage's exact output."""
        by_id = {s.stage_id: s for s in stages}
        pairs = [
            ("STAGE_03_DATASET_INGESTION", "record_sets", "STAGE_04_DATASET_NORMALIZATION", "record_sets"),
            ("STAGE_04_DATASET_NORMALIZATION", "canonical_sets", "STAGE_05_DATASET_INTEGRITY_SCAN", "canonical_sets"),
        ]
        out = []
        for prod, pkey, cons, ckey in pairs:
            if prod in by_id and cons in by_id:
                produced = by_id[prod].output_summary.get(pkey)
                consumed = by_id[cons].input_summary.get(ckey)
                out.append({"producer": prod, "consumer": cons, "linked": produced == consumed,
                            "digest": _digest(produced) if produced is not None else None})
        return out
