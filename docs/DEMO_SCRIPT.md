# Judge demo — 3 minutes

Open four browser tabs at http://127.0.0.1:8000 and sign in as `sec.analyst`, `reviewer`, `auditor`, `ml.analyst` (password `Drishtra@2026`).

1. **Landing (10 s).** "An AI result can be accurate and still untrustworthy." Point at the coverage statement: we publish what we don't test.
2. **ML Analyst → Cases → C-07 submission → Start assurance run (20 s).** 18 stages; open *Pipeline run*: each stage shows output digests; skipped stages are never shown as success.
3. **Security Analyst → same case (40 s).** Banner: *Quarantine recommended*. *Why?* tab: findings grouped by layer, convergence on C-07, and counter-evidence — "model digest verified on M-04" — i.e. *the bytes are genuine but the behaviour is backdoored*. Click *Why?* on I-883 → trace inference → runtime → model → dataset → contributor.
4. **Trace evidence tab (20 s).** Evidence graph: every edge is a recorded relationship; green ✓ = checks that passed, ○ = declared limitations.
5. **Coverage & limits (15 s).** White-box analysis not available for a black-box model — shown, not hidden.
6. **Security Analyst → Decision → recommend QUARANTINE (15 s).** Then show the admin tab can't decide (403 / "not part of your role").
7. **Reviewer → Review center → case → Decision → QUARANTINE + rationale → Sign & commit (25 s).** Verify signatures.
8. **Auditor → Verify all chains (15 s).** Case ledgers, decision chains, platform ledger: all valid.
9. **Close (20 s).** "Existing tools tell you an asset has a problem. DRISHTRA connects evidence across the lifecycle into an assurance case — what supports it, what contradicts it, what wasn't tested, who decided, and proof that decision wasn't altered."

Backup: `python scripts/golden_demo.py` runs the same story headlessly, including mutation propagation and tamper detection.
