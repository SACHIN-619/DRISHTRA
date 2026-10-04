"""
DRISHTRA Role-Based Access Control

Five roles, each with one mission. Authority is split on purpose:

  ML_ANALYST           Prepare and assess AI assets (datasets, models, inference, runs).
  SECURITY_ANALYST     Investigate integrity threats, correlate evidence, build assurance
                       cases and RECOMMEND a disposition.
  REVIEWER_SUPERVISOR  Make the binding, signed disposition (ACCEPT / REVIEW / QUARANTINE).
  AUDITOR              Independently verify history. Read-only everywhere.
  ADMINISTRATOR        Operate and govern the platform (users, roles, policy, health).
                       Holds NO assurance authority and cannot operate on AI assets.

Things no role can do (there is no endpoint for them at all):
  - delete or edit audit / platform events
  - edit or delete a recorded decision (decisions are append-only)
  - alter detector findings

There is no superuser bypass anywhere in the authorization layer.
"""
from enum import Enum
from typing import Set, Dict, Any, List


class Role(str, Enum):
    ML_ANALYST = "ML_ANALYST"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    REVIEWER_SUPERVISOR = "REVIEWER_SUPERVISOR"
    AUDITOR = "AUDITOR"
    ADMINISTRATOR = "ADMINISTRATOR"


class Permission(str, Enum):
    # Shared read access to the assurance workspace
    ASSET_READ = "asset:read"                    # cases, contributors, datasets, models, inferences, runs
    EVIDENCE_READ = "evidence:read"              # findings, evidence, graph, lineage, passports, assurance cases
    REPORT_READ = "report:read"

    # Asset operations
    CASE_CREATE = "case:create"
    DATASET_INGEST = "dataset:ingest"
    MODEL_REGISTER = "model:register"
    INFERENCE_SUBMIT = "inference:submit"
    PIPELINE_RUN = "pipeline:run"
    ATTACK_SIMULATE = "attack:simulate"

    # Security operations
    CRYPTO_VERIFY = "crypto:verify"
    ASSURANCE_BUILD = "assurance:build"
    DISPOSITION_RECOMMEND = "disposition:recommend"
    SECURITY_EVENTS_READ = "security_events:read"

    # Governance
    DISPOSITION_DECIDE = "disposition:decide"

    # Audit
    AUDIT_READ = "audit:read"
    AUDIT_VERIFY = "audit:verify"

    # Administration
    USER_MANAGE = "user:manage"
    POLICY_MANAGE = "policy:manage"
    SYSTEM_DIAGNOSTICS = "system:diagnostics"

    # Backward-compatible alias used by older tests and docs
    DISPOSITION_APPROVE = "disposition:decide"


_READ = {Permission.ASSET_READ, Permission.EVIDENCE_READ, Permission.REPORT_READ}

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ML_ANALYST: _READ | {
        Permission.CASE_CREATE,
        Permission.DATASET_INGEST,
        Permission.MODEL_REGISTER,
        Permission.INFERENCE_SUBMIT,
        Permission.PIPELINE_RUN,
        Permission.ATTACK_SIMULATE,
    },
    Role.SECURITY_ANALYST: _READ | {
        Permission.CASE_CREATE,
        Permission.DATASET_INGEST,
        Permission.MODEL_REGISTER,
        Permission.INFERENCE_SUBMIT,
        Permission.PIPELINE_RUN,
        Permission.ATTACK_SIMULATE,
        Permission.CRYPTO_VERIFY,
        Permission.ASSURANCE_BUILD,
        Permission.DISPOSITION_RECOMMEND,
        Permission.SECURITY_EVENTS_READ,
        Permission.AUDIT_READ,
    },
    Role.REVIEWER_SUPERVISOR: _READ | {
        Permission.CRYPTO_VERIFY,
        Permission.DISPOSITION_DECIDE,
        Permission.AUDIT_READ,
    },
    Role.AUDITOR: _READ | {
        Permission.CRYPTO_VERIFY,
        Permission.AUDIT_READ,
        Permission.AUDIT_VERIFY,
    },
    Role.ADMINISTRATOR: {
        Permission.ASSET_READ,
        Permission.REPORT_READ,
        Permission.USER_MANAGE,
        Permission.POLICY_MANAGE,
        Permission.SYSTEM_DIAGNOSTICS,
        Permission.SECURITY_EVENTS_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_VERIFY,
    },
}

ROLE_MISSIONS: Dict[Role, Dict[str, Any]] = {
    Role.ML_ANALYST: {
        "title": "ML Operations",
        "mission": "Prepare and assess AI assets.",
        "question": "What assets need my attention?",
        "forbidden": [
            "Finalize or recommend a disposition",
            "Manage users or policy",
            "Read platform security events",
        ],
    },
    Role.SECURITY_ANALYST: {
        "title": "Security Operations",
        "mission": "Investigate integrity threats and correlate evidence.",
        "question": "Where is the threat and how is it connected?",
        "forbidden": [
            "Finalize a disposition (can only recommend)",
            "Manage users or policy",
        ],
    },
    Role.REVIEWER_SUPERVISOR: {
        "title": "Assurance Review Center",
        "mission": "Make defensible assurance decisions.",
        "question": "Which decisions need my authorization?",
        "forbidden": [
            "Run detectors or ingest assets",
            "Decide a case whose evaluation they initiated",
            "Edit an earlier decision",
        ],
    },
    Role.AUDITOR: {
        "title": "Audit Assurance Center",
        "mission": "Verify that the system's history is trustworthy.",
        "question": "Can I prove the history is intact?",
        "forbidden": [
            "Modify findings, cases or users",
            "Run detectors",
            "Make or recommend decisions",
        ],
    },
    Role.ADMINISTRATOR: {
        "title": "System Administration",
        "mission": "Operate and govern the platform.",
        "question": "Is the platform securely governed?",
        "forbidden": [
            "Make, recommend or edit assurance decisions",
            "Run detectors or alter findings",
            "Delete or edit audit history",
        ],
    },
}


class RBACService:
    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def permissions_for(role: Role) -> List[str]:
        return sorted({p.value for p in ROLE_PERMISSIONS.get(role, set())})

    @staticmethod
    def get_role_capabilities(role: Role) -> Dict[str, Any]:
        mission = ROLE_MISSIONS.get(role, {})
        return {
            "role": role.value,
            "title": mission.get("title"),
            "mission": mission.get("mission"),
            "question": mission.get("question"),
            "permissions": RBACService.permissions_for(role),
            "explicitly_forbidden": mission.get("forbidden", []),
        }
