# DRISHTRA Operational Limitations & Engineering Boundaries
**Document Version:** 1.0.0  
**Transparency Standard:** Military Zero-Trust Assurance  
**Operational Status:** `[IMPLEMENTED]`

*Note: For the full specification, see [docs/LIMITATIONS.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/LIMITATIONS.md).*

### Summary of System Boundaries:
1. **Black-Box Model Constraints:** Without white-box access, internal gradient mapping is unavailable and explicitly marked `NOT_APPLICABLE` / `NOT_TESTED`.
2. **Perceptual dHash Invariant:** dHash detects brightness/compression shifts, but is bounded against extreme non-linear crops and large affine rotations ($> 15^\circ$).
3. **Synthetic Benchmark Generalization:** Attack Lab results demonstrate algorithmic rigor on controlled synthetic mutations; they do not prove universal defense against novel real-world adversarial attacks.
4. **Key Management:** Prototype environment-variable keys must transition to hardware HSM / TPM 2.0 (`[FUTURE ADAPTER]`) for field deployment.
5. **Database Concurrency:** SQLite serializes write transactions; high-concurrency multi-node installations should activate the PostgreSQL adapter.
6. **External LLM Isolation:** External LLMs operate strictly outside the sovereign trust boundary; core assurance never depends on external APIs.

See [docs/LIMITATIONS.md](file:///c:/Users/Sachin/Desktop/DRISHTRA/docs/LIMITATIONS.md).
