"""
DRISHTRA Role-Based Access Control (RBAC) Engine
Defines five military AI governance roles and strict permission boundaries:
1. ML_ANALYST: Ingest datasets, register models, run scans, inspect detector findings, run attack simulations.
   CANNOT: Approve final disposition, modify audit history.
2. SECURITY_ANALYST: Inspect cryptographic verification, investigate provenance, replay/tampering, contributor risk, examine evidence graph.
3. REVIEWER_SUPERVISOR: Review assurance cases, inspect evidence, accept/reject findings, approve ACCEPT/REVIEW/QUARANTINE, sign disposition.
4. AUDITOR: Read-only access to audit chain, historical events, assurance reports, coverage statements, verification records.
5. ADMINISTRATOR: Manage users, keys, policies, system configuration.
   CANNOT: Silently rewrite historical evidence, delete or modify tamper-evident audit logs.
"""
from enum import Enum
from typing import Set, Dict, Any, Optional

class Role(str, Enum):
    ML_ANALYST = "ML_ANALYST"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    REVIEWER_SUPERVISOR = "REVIEWER_SUPERVISOR"
    AUDITOR = "AUDITOR"
    ADMINISTRATOR = "ADMINISTRATOR"

class Permission(str, Enum):
    # ML Operations
    DATASET_INGEST = "dataset:ingest"
    DATASET_SCAN = "dataset:scan"
    MODEL_REGISTER = "model:register"
    MODEL_PROBE = "model:probe"
    ATTACK_SIMULATE = "attack:simulate"
    
    # Security Operations
    CRYPTO_VERIFY = "crypto:verify"
    PROVENANCE_INSPECT = "provenance:inspect"
    GRAPH_EXAMINE = "graph:examine"
    CONTRIBUTOR_INVESTIGATE = "contributor:investigate"
    
    # Review & Governance
    ASSURANCE_REVIEW = "assurance:review"
    DISPOSITION_APPROVE = "disposition:approve"
    DISPOSITION_SIGN = "disposition:sign"
    
    # Audit & Inspection
    AUDIT_READ = "audit:read"
    REPORT_READ = "report:read"
    
    # System Administration
    USER_MANAGE = "user:manage"
    POLICY_MANAGE = "policy:manage"
    CONFIG_MANAGE = "config:manage"

# Explicit Permission Matrix
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ML_ANALYST: {
        Permission.DATASET_INGEST,
        Permission.DATASET_SCAN,
        Permission.MODEL_REGISTER,
        Permission.MODEL_PROBE,
        Permission.ATTACK_SIMULATE,
        Permission.REPORT_READ
    },
    Role.SECURITY_ANALYST: {
        Permission.CRYPTO_VERIFY,
        Permission.PROVENANCE_INSPECT,
        Permission.GRAPH_EXAMINE,
        Permission.CONTRIBUTOR_INVESTIGATE,
        Permission.REPORT_READ,
        Permission.AUDIT_READ
    },
    Role.REVIEWER_SUPERVISOR: {
        Permission.ASSURANCE_REVIEW,
        Permission.DISPOSITION_APPROVE,
        Permission.DISPOSITION_SIGN,
        Permission.PROVENANCE_INSPECT,
        Permission.GRAPH_EXAMINE,
        Permission.REPORT_READ,
        Permission.AUDIT_READ
    },
    Role.AUDITOR: {
        Permission.AUDIT_READ,
        Permission.REPORT_READ,
        Permission.PROVENANCE_INSPECT
    },
    Role.ADMINISTRATOR: {
        Permission.USER_MANAGE,
        Permission.POLICY_MANAGE,
        Permission.CONFIG_MANAGE,
        Permission.REPORT_READ,
        Permission.AUDIT_READ
        # CRITICAL SECURITY DESIGN: ADMINISTRATOR DOES NOT HAVE PERMISSION TO DELETE OR REWRITE AUDIT/EVIDENCE
    }
}

class RBACService:
    @staticmethod
    def has_permission(role: Role, permission: Permission) -> bool:
        """Evaluates whether a role is authorized for a specific action."""
        perms = ROLE_PERMISSIONS.get(role, set())
        return permission in perms

    @staticmethod
    def get_role_capabilities(role: Role) -> Dict[str, Any]:
        """Returns human-readable permitted and forbidden operations for a role."""
        perms = [p.value for p in ROLE_PERMISSIONS.get(role, set())]
        forbidden = []
        if role == Role.ML_ANALYST:
            forbidden = ["Approve final disposition (ACCEPT/QUARANTINE)", "Modify audit history"]
        elif role == Role.AUDITOR:
            forbidden = ["Mutate cases", "Register models/datasets", "Execute probes"]
        elif role == Role.ADMINISTRATOR:
            forbidden = ["Silently rewrite historical evidence", "Delete or tamper with audit ledger"]

        return {
            "role": role.value,
            "permissions": perms,
            "explicitly_forbidden": forbidden
        }
