"""
18-stage pipeline: honest stage status, stage chaining, idempotency, failure handling.
"""
from app.db.models import CheckExecution
from app.schemas.all_schemas import CaseCreate, ContributorCreate
from app.services.audit_service import AuditService
from app.services.case_service import CaseService, ContributorService
from app.services.pipeline_service import CasePipeline


def test_empty_case_pipeline_skips_rather_than_fakes_success(db_session):
    case_id = CaseService.create_case(db_session, CaseCreate(
        name="Empty pipeline case", description="no assets", classification="RESTRICTED"), actor="test").case_id
    ContributorService.register_contributor(db_session, ContributorCreate(
        case_id=case_id, name="Test Contributor", contributor_type="LAB"))
    run = CasePipeline.run(db=db_session, case_id=case_id, actor="test_runner")
    assert run.status == "COMPLETED"
    assert len(run.stages) == 18
    by_id = {s.stage_id: s for s in run.stages}
    # Nothing to scan -> SKIPPED, never SUCCESS
    for sid in ["STAGE_03_DATASET_INGESTION", "STAGE_05_DATASET_INTEGRITY_SCAN",
                "STAGE_07_MODEL_INSPECTION", "STAGE_11_CRYPTOGRAPHIC_VERIFICATION"]:
        assert by_id[sid].status == "SKIPPED", sid
    assert by_id["STAGE_15_ASSURANCE_CASE_CONSTRUCTION"].output_summary["status"] == "INCONCLUSIVE"


def test_demo_pipeline_chaining_and_idempotency(db_session):
    from app.services.demo_service import DemoService, DEMO_CASE_ID
    DemoService.bootstrap_demo_case(db_session)
    run_1 = CasePipeline.run(db=db_session, case_id=DEMO_CASE_ID, actor="test_runner")
    assert run_1.status == "COMPLETED"
    by_id = {s.stage_id: s for s in run_1.stages}
    # Stage 5 consumed exactly what stage 4 produced, which came from stage 3.
    assert by_id["STAGE_04_DATASET_NORMALIZATION"].input_summary["record_sets"] == \
        by_id["STAGE_03_DATASET_INGESTION"].output_summary["record_sets"]
    assert by_id["STAGE_05_DATASET_INTEGRITY_SCAN"].input_summary["canonical_sets"] == \
        by_id["STAGE_04_DATASET_NORMALIZATION"].output_summary["canonical_sets"]
    assert by_id["STAGE_18_COMPLETION_AND_COVERAGE"].output_summary["chaining_checks_passed"] is True

    first = AuditService.verify_case_audit(db_session, DEMO_CASE_ID)
    findings_before = {f.finding_id for f in db_session.query(__import__("app.db.models", fromlist=["Finding"]).Finding)
                       .filter_by(case_id=DEMO_CASE_ID).all()}

    run_2 = CasePipeline.run(db=db_session, case_id=DEMO_CASE_ID, actor="test_runner")
    assert run_2.status == "COMPLETED"
    rec1 = by_id["STAGE_15_ASSURANCE_CASE_CONSTRUCTION"].output_summary["recommended_disposition"]
    rec2 = {s.stage_id: s for s in run_2.stages}["STAGE_15_ASSURANCE_CASE_CONSTRUCTION"].output_summary["recommended_disposition"]
    assert rec1 == rec2 == "QUARANTINE"
    # Re-running does not duplicate findings
    from app.db.models import Finding
    findings_after = {f.finding_id for f in db_session.query(Finding).filter_by(case_id=DEMO_CASE_ID).all()}
    assert findings_after == findings_before
    second = AuditService.verify_case_audit(db_session, DEMO_CASE_ID)
    assert first["status"] == second["status"] == "VALID"
    assert second["verified_count"] > first["verified_count"]
    assert db_session.query(CheckExecution).filter_by(case_id=DEMO_CASE_ID).count() > 0


def test_pipeline_nonexistent_case(db_session):
    run = CasePipeline.run(db=db_session, case_id="CASE-DOES-NOT-EXIST-999", actor="test_runner")
    assert run.status == "FAILED"
    assert "does not exist" in (run.error_message or "").lower()
    assert run.stages[-1].status == "FAILED"
