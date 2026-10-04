# DRISHTRA REST API Contract Specification
**Document Version:** 1.0.0  
**Compliance Standard:** OpenAPI 3.1.0 | DRISHTRA-AP-2026.1  
**Operational Status:** `[IMPLEMENTED]`

*Note: For the complete route catalog and schemas, see [docs/API.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/API.md).*

### Core Endpoint Categories:
- `/health`, `/ready`, `/api/v1/system/info`, `/api/v1/system/capabilities`: System health, capabilities discovery.
- `/api/v1/cases`, `/api/v1/cases/{case_id}/run`: Assurance case lifecycle & 18-stage pipeline.
- `/api/v1/contributors`: Contributor entity registration & risk profiles.
- `/api/v1/datasets`, `/api/v1/datasets/{id}/scan`, `/api/v1/datasets/{id}/chunks`: Dataset ingestion & D1-D6 scanning.
- `/api/v1/models`, `/api/v1/models/{id}/inspect`: Model registration and structural passport.
- `/api/v1/inferences`, `/api/v1/inferences/verify`: Cryptographically signed inference attestations.
- `/api/v1/graph/{case_id}`, `/api/v1/graph/{case_id}/reverse-trace`: NetworkX knowledge graph & reverse trace.
- `/api/v1/assurance/{case_id}`, `/api/v1/assurance/{case_id}/approve`: AP-2026.1 policy and supervisor sign-off.
- `/api/v1/audit/{case_id}`, `/api/v1/audit/{case_id}/verify`: Hash-chained audit ledger inspection & verification.
- `/api/v1/reports/{case_id}`, `/api/v1/reports/{case_id}/export`: Machine-readable JSON assurance reports & 9 artifacts.
- `/api/v1/benchmarks/attack-lab`: Synthetic Attack Laboratory execution & confusion matrix.

See [docs/API.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/API.md).
