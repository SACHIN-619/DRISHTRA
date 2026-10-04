# DRISHTRA — Gap Analysis and Build Plan

Audit date: 4 Oct 2026. Method: ran the backend and its test suite against a fresh database, called the live API, and read the code path for every claim in the product vision (the 89-point brief). This file records what was found *before* any changes, so the improvement is traceable.

## 1. Headline

The backend has real substance (detectors, Ed25519 helpers, hash-chained audit, NetworkX evidence graph, 18-stage orchestrator). Four things undermined it:

1. **No real authentication.** Anyone could obtain any role.
2. **The assurance engine reported counter-evidence that contradicted its own findings** because of an operator-precedence bug.
3. **The frontend did not talk to the backend at all.** Every screen was hardcoded.
4. **Several product claims were not backed by code** (signed audit events, HSM/TPM, command-node map).

## 2. Findings — security and governance

| # | Severity | Finding | Where |
|---|---|---|---|
| S1 | Critical | `POST /auth/token` accepts **any username, any password, and a caller-chosen `role`**. There is no users table. | `api/routes/auth.py` |
| S2 | Critical | A request with **no token is silently treated as `ML_ANALYST`** (`airgap_analyst`). | `core/security.py:get_current_user` |
| S3 | Critical | `require_role` / `require_permission` **let ADMINISTRATOR bypass every check**, including disposition approval. This breaks the separation of duties the README describes. | `core/security.py` |
| S4 | High | ~55 of ~70 endpoints have **no auth dependency at all** (findings, evidence, graph, passports, reports, audit-adjacent reads, attack lab, model/dataset parsing). | `api/routes/*` |
| S5 | High | Disposition approval **overwrites** `human_disposition` in place, so earlier decisions are lost. Nothing prevents self-approval. | `api/routes/assurance.py` |
| S6 | High | Hardcoded fallback JWT secret `drishtra-sovereign-defence-assurance-secret-key-2026`. | `core/config.py` |
| S7 | Medium | Platform events (user created, role changed, login failed) cannot be audited: `audit_events.case_id` is a required FK to a case. | `db/models.py` |
| S8 | Medium | CORS allows `*` with credentials. | `core/config.py` |
| S9 | Medium | The docs say audit events are "Ed25519-signed", but `signature` is always `None`. | `services/audit_service.py` |
| S10 | Low | The optional Grok explainer sends case findings to an external API when `IS_AIR_GAPPED=false`. It is acceptable only as a clearly-labelled opt-in. | `services/llm_explainer.py` |

## 3. Findings — assurance logic (the core product claim)

| # | Severity | Finding |
|---|---|---|
| A1 | **Critical** | In `AssurancePolicyEngine.evaluate`, expressions like `getattr(f,"finding_type",None) or f.get(...) if isinstance(f,dict) else "FINDING"` parse as `(...) if isinstance(f, dict) else "FINDING"`. For ORM rows, **every finding type becomes the literal `"FINDING"`**. Consequences on the live demo case: the assurance case lists `SIGNATURE_VALID` and `NONCE_FRESHNESS_VERIFIED` as counter-evidence **while a CRITICAL `CRYPTOGRAPHIC_SIGNATURE_INVALID` finding exists**. Coverage shows everything `VERIFIED`, and multi-path convergence is never detected. |
| A2 | High | Counter-evidence is created from the *absence* of a finding type, not from a check that actually ran and passed. If no inference was ever ingested, the system still claims "signature valid". This violates the project's own invariant, NOT_TESTED ≠ PASS. |
| A3 | High | Only `supporting_evidence` (LOW/INFO findings) is persisted. The **incriminating evidence that justifies the disposition is discarded**, so the stored assurance case has an empty evidence list. |
| A4 | Medium | The service overrides coverage with capability flags (`AVAILABLE`, `LIMITED`), which mixes up "can we test this" with "did we test this and what happened". |
| A5 | Medium | Pipeline stages 6, 7 and 10 are DB reads labelled as work. Stage 11 reports `SUCCESS` when it is skipped (no public key or no inferences). It should say `SKIPPED` / `NOT_TESTED`. |

## 4. Findings — frontend and product

| # | Finding |
|---|---|
| F1 | The Next.js app has **zero `fetch` calls**. All verdicts, passports, findings and stages are constants in `src/lib/constants.ts` and inline JSX. The "scenario switcher" swaps strings. |
| F2 | The role is a dropdown in the navbar (`useState('SECURITY_ANALYST')`), so anyone can switch role in the client. Every role sees the same pages. |
| F3 | There is no landing page and no login. |
| F4 | Unbacked claims: an Indian Army command-node map, "BEL Sovereign Key Vault", "HSM Sealed", "TPM 2.0", diode latencies. |
| F5 | Fonts load from Google, which breaks offline/air-gapped operation. |
| F6 | `next.config.js` proxies to port 8005 while the README says 8000. |
| F7 | Demo data names real organisations as contributors ("CAIR / DRDO"). This is replaced with neutral synthetic names. |

## 5. Findings — engineering hygiene

| # | Finding |
|---|---|
| E1 | Tests depend on a developer's existing `drishtra_vault.db`. On a fresh checkout, **7 of 31 fail** with `no such table: cases`. |
| E2 | No test covers authentication, self-approval, admin bypass or decision history. |
| E3 | Duplicate doc sets (`ARCHITECTURE.md` at the root and in `docs/`, `threat-model.md` and `THREAT_MODEL.md`). |

## 6. What is solid and kept

- Detector implementations D1–D9 and the common `DetectorResult` contract
- Canonical JSON + SHA-256 hash chain, and audit verification
- Evidence graph with typed edges and reverse-lineage trace
- 18-stage orchestrator structure, with idempotency on findings
- File vault, COCO/YOLO parsers, ONNX inspector, attack lab with ground-truth separation

## 7. Build plan (executed in this order)

**Phase A — Security foundation (backend)**
1. `users` table, PBKDF2 hashes, account status, `must_change_password`, failed-login lockout.
2. Login checks credentials. The role comes from the database, never from the request.
3. Remove the anonymous fallback and the admin bypass. Every route gets an explicit permission.
4. Admin-only user lifecycle: create (temporary password), change role, disable. No public registration.
5. Bootstrap the first admin from an environment variable, and seed the demo users only in demo mode.
6. Hash-chained `platform_events` ledger for governance and security events, separate from AI findings.
7. Append-only `assurance_decisions` table. Self-approval is blocked: the reviewer cannot be the run's initiator. Decisions are signed by the server key.
8. Secret from the environment. In demo mode, generate a per-install secret file and never use a hardcoded one.

**Phase B — Assurance correctness**
9. Fix A1. Derive counter-evidence and coverage from what actually ran (A2, A4). Persist the incriminating evidence (A3).
10. Report stage status honestly (`SKIPPED`, `NOT_TESTED`) (A5).

**Phase C — Frontend rebuild**
11. Public landing → login → role consoles. Each role gets its own navigation and home that answers its own question.
12. Wired only to the live API, with no mock data and no external fonts or CDNs. Built as a static bundle that FastAPI serves, so it runs as one offline process.
13. Flagship surfaces: Assurance Case, Why-Flagged trace, Passport, Coverage, Decision + history, Audit verification, User admin.

**Phase D — Proof**
14. Fresh-DB conftest, plus tests for every governance rule.
15. Golden demo walk-through in a real browser across all five roles, with screenshots.

## 8. Explicitly out of scope for this pass (roadmap, labelled as such in the UI)

LDAP/AD/smart-card/MFA, HSM-backed keys, a physical removable-media workflow, SAR/thermal modalities, white-box trigger reconstruction, multi-organisation distributed ledger, and evaluation on public datasets and the TrojAI benchmark.
