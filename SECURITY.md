# DRISHTRA security model (v2.0)

Five security boundaries, each enforced by the server.

| Boundary | Question | Mechanism |
|---|---|---|
| Identity | Who are you? | `users` table, PBKDF2-SHA256 (310k iterations), lockout after `MAX_FAILED_LOGINS`, one-time temporary passwords, forced first-login change. No self-registration. |
| Authorization | What may you do? | RBAC matrix in `core/rbac.py`. The role is re-read from the database on every request (never taken from the request or token). No superuser bypass. Every denial is logged. |
| Asset integrity | Is this artifact what it claims? | SHA-256 of uploads and delivered models, D8A digest comparison, D9 signature / replay / model-binding checks. |
| Evidence integrity | Can evidence be altered unnoticed? | Case audit ledger, platform ledger and decision chain are SHA-256 hash chains (`H_n = SHA256(H_{n-1} ‖ canonical(e_n))`); decisions and passports are Ed25519-signed with the node key. |
| Decision accountability | Who decided, and why? | Append-only `assurance_decisions`: analysts recommend, reviewers decide, rationale mandatory, initiator/recommender cannot finalize, later decisions supersede (never overwrite). |

## Role authority

| Capability | ML | Security | Reviewer | Auditor | Admin |
|---|:-:|:-:|:-:|:-:|:-:|
| Ingest / register / run pipeline | ✓ | ✓ | — | — | — |
| Read findings, evidence, passports | ✓ | ✓ | ✓ | ✓ | — |
| Build assurance case / recommend | — | ✓ | — | — | — |
| **Final disposition** | — | — | ✓ | — | — |
| Verify chains | — | read | read | ✓ | ✓ |
| Platform security events | — | ✓ | — | — | ✓ |
| Users, policy, diagnostics | — | — | — | — | ✓ |
| Edit/delete history or decisions | ✗ | ✗ | ✗ | ✗ | ✗ (no endpoint exists) |

## Keys and secrets

* JWT secret: `SECRET_KEY` env var, otherwise generated once into `storage/keys/jwt_secret` (0600). A secret that was published in the repository is refused outside demo mode.
* Node signing key: 32-byte seed in `storage/keys/node_ed25519.seed` (0600). `KeyManagementInterface` is the single seam for an HSM/PKCS#11/TPM implementation.
* Tokens live in `sessionStorage` (cleared with the tab) and carry only user id and token version; logout, role change, disable and password change revoke all sessions.

## Network posture

The console is served by the API process with a strict Content-Security-Policy (`default-src 'self'`). No CDN, font or telemetry hosts. The optional external explainer requires three explicit settings and is reported in diagnostics. `backend/tests/test_airgap.py` fails the build on any outbound connection during the demo pipeline.

## Prototype limits (declared)

Prototype access classification (`PUBLIC/INTERNAL/RESTRICTED/SENSITIVE`) is recorded but not yet used to filter data. Enterprise identity (LDAP/AD, smart-card, MFA) and HSM-backed keys are roadmap.
