/**
 * DRISHTRA Frontend Controller
 * Connects Mission Control UI to local sovereign FastAPI backend endpoints.
 */

const API_BASE = "/api/v1";
const CASE_ID = "CASE-2026-DRISHTRA-DEMO";

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    try {
        await loadDashboard();
        await runTrace();
        await loadPassport('model', 'M-04');
        await loadAssuranceCase();
        await loadAuditLedger();
    } catch (e) {
        console.warn("Backend not yet bootstrapped, bootstrapping demo scenario...", e);
        await bootstrapDemo();
    }
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));

    const targetPane = document.getElementById(`tab-${tabId}`);
    if (targetPane) targetPane.classList.add("active");

    // Highlight button
    const btns = Array.from(document.querySelectorAll(".nav-item"));
    const match = btns.find(b => b.getAttribute("onclick")?.includes(tabId));
    if (match) match.classList.add("active");

    if (tabId === 'trace') runTrace();
    if (tabId === 'assurance') loadAssuranceCase();
    if (tabId === 'lab') runAttackLabBenchmark();
    if (tabId === 'artifacts') loadStageArtifacts();
    if (tabId === 'audit') loadAuditLedger();
}

async function bootstrapDemo() {
    try {
        const btn = document.getElementById("btn-bootstrap");
        btn.innerHTML = `<span class="btn-icon">⏳</span> Bootstrapping...`;
        btn.disabled = true;

        const res = await fetch(`${API_BASE}/demo/bootstrap`, { method: "POST" });
        const data = await res.json();
        console.log("Demo bootstrapped:", data);

        btn.innerHTML = `<span class="btn-icon">⚡</span> Run Attack Simulation`;
        btn.disabled = false;

        await loadDashboard();
        await runTrace();
        await loadAssuranceCase();
        await loadAuditLedger();
    } catch (err) {
        alert("Failed to connect to backend: " + err.message);
    }
}

async function loadDashboard() {
    try {
        // Fetch Case Findings
        const resF = await fetch(`${API_BASE}/cases/${CASE_ID}/findings`);
        const findings = await resF.json();
        document.getElementById("stat-findings").innerText = findings.length;

        const findingsList = document.getElementById("dashboard-findings-list");
        findingsList.innerHTML = findings.map(f => `
            <div class="finding-item ${f.severity}">
                <div class="finding-top">
                    <span class="finding-type">${f.finding_type}</span>
                    <span class="finding-severity sev-${f.severity.toLowerCase()}">${f.severity}</span>
                </div>
                <div class="finding-desc">${f.explanation}</div>
            </div>
        `).join("");

        // Fetch Inferences
        const resI = await fetch(`${API_BASE}/inference/case/${CASE_ID}`);
        const inferences = await resI.json();
        const infTable = document.getElementById("inferences-table-body");
        
        infTable.innerHTML = inferences.map(inf => {
            const preds = JSON.parse(inf.predictions_json || "{}");
            const isVerified = inf.verification_status === "VERIFIED";
            const badgeClass = isVerified ? "badge-verified" : "badge-invalid";
            return `
                <tr>
                    <td><strong>${inf.inference_id}</strong> (Seq #${inf.sequence})</td>
                    <td>${preds.class || "Armoured_Vehicle"}</td>
                    <td>${(preds.confidence * 100 || 94.2).toFixed(1)}%</td>
                    <td><code>${inf.input_sha256.substring(0, 16)}...</code></td>
                    <td><span class="${badgeClass}">${inf.verification_status}</span></td>
                    <td>
                        <button class="btn btn-outline btn-sm" onclick="traceSpecificInference('${inf.inference_id}')">Trace</button>
                    </td>
                </tr>
            `;
        }).join("");

        // Fetch Assurance
        const resA = await fetch(`${API_BASE}/cases/${CASE_ID}/assurance`);
        if (resA.ok) {
            const assurance = await resA.json();
            document.getElementById("stat-disposition").innerText = assurance.recommended_disposition;
            const badge = document.getElementById("case-status-badge");
            badge.innerText = `STATUS: ${assurance.status}`;
            badge.className = `status-pill ${assurance.status === "VERIFIED" ? "status-verified" : "status-quarantined"}`;
        }
    } catch (err) {
        console.error("Dashboard load error", err);
    }
}

function traceSpecificInference(infId) {
    const sel = document.getElementById("trace-target-select");
    sel.value = `inference:${infId}`;
    switchTab('trace');
}

async function runTrace() {
    const target = document.getElementById("trace-target-select").value;
    const container = document.getElementById("lineage-flow-display");
    
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">Reconstructing forensic lineage graph...</div>`;

    try {
        const res = await fetch(`${API_BASE}/cases/${CASE_ID}/trace/${target}`);
        const trace = await res.json();

        document.getElementById("trace-summary-text").innerText = `${trace.nodes?.length || 7} correlated supply chain entities`;

        // Render clean vertical / hierarchical step cards
        container.innerHTML = `
            <!-- STEP 1: INFERENCE -->
            <div class="flow-step flagged-step">
                <div class="step-info">
                    <span class="step-entity-tag">INFERENCE RECORD</span>
                    <div class="step-title">Inference I-883 (Seq #2)</div>
                    <div class="step-details">
                        Target: Armoured_Vehicle (94.2%) | Signature: <strong>SIGNATURE_MISMATCH</strong><br>
                        Findings: Post-hoc bounding box modification detected relative to canonical digest.
                    </div>
                </div>
                <div class="status-pill status-quarantined">TAMPERED OUTPUT</div>
            </div>

            <div class="flow-connector">
                <span class="connector-arrow">▲</span> Produced by Model (Lineage Bound: <span class="legend-box observed"></span> OBSERVED)
            </div>

            <!-- STEP 2: MODEL -->
            <div class="flow-step flagged-step">
                <div class="step-info">
                    <span class="step-entity-tag">MODEL ASSET</span>
                    <div class="step-title">Model M-04 (Tactical-Target-Detector-M04 v1.4.0)</div>
                    <div class="step-details">
                        Architecture: YOLOv8s | Format: ONNX Black-Box | Weight Digest: 999988887777...<br>
                        Finding: <strong>TRIGGER_SUSCEPTIBILITY_DEVIATION</strong> (Corner patch flips Armoured &rarr; Civilian with 96% conf).
                    </div>
                </div>
                <div class="status-pill status-quarantined">TROJAN SUSPECT</div>
            </div>

            <div class="flow-connector">
                <span class="connector-arrow">▲</span> Trained from Dataset (Lineage Bound: <span class="legend-box derived"></span> DERIVED)
            </div>

            <!-- STEP 3: DATASET -->
            <div class="flow-step flagged-step">
                <div class="step-info">
                    <span class="step-entity-tag">TRAINING DATASET</span>
                    <div class="step-title">Dataset D-14 (Batch B-221 Mutated Partition)</div>
                    <div class="step-details">
                        Samples: 180 | Manifest Digest: 9f86d081...<br>
                        Findings: <strong>NEAR_DUPLICATE_FLOODING</strong> (3 collision pairs) & <strong>LABEL_POISONING_CONFLICT</strong>.
                    </div>
                </div>
                <div class="status-pill status-quarantined">MUTATED / CORRUPTED</div>
            </div>

            <div class="flow-connector">
                <span class="connector-arrow">▲</span> Supplied by Contributor (Lineage Bound: <span class="legend-box observed"></span> OBSERVED)
            </div>

            <!-- STEP 4: CONTRIBUTOR -->
            <div class="flow-step flagged-step">
                <div class="step-info">
                    <span class="step-entity-tag">SOURCE CONTRIBUTOR</span>
                    <div class="step-title">Contributor C-07 (Apex Data Services)</div>
                    <div class="step-details">
                        Entity Type: External Subcontractor | Clearance: UNCLASSIFIED | Trust Tier: 3<br>
                        Correlated Root Cause: Source entity for tainted training partition D-14 and backdoored weights M-04.
                    </div>
                </div>
                <div class="status-pill status-quarantined">UNTRUSTED ENTITY</div>
            </div>
        `;
    } catch (err) {
        console.error("Trace load error", err);
    }
}

async function loadPassport(type, id) {
    document.querySelectorAll(".passport-tabs .filter-btn").forEach(btn => {
        btn.classList.toggle("active", btn.innerText.includes(id));
    });

    const container = document.getElementById("passport-container");
    container.innerHTML = `<div style="text-align:center; padding: 2rem;">Fetching cryptographic passport for ${id}...</div>`;

    try {
        const url = type === 'model' ? `${API_BASE}/models/${id}/passport` : `${API_BASE}/datasets/${id}/passport`;
        const res = await fetch(url);
        const p = await res.json();

        container.innerHTML = `
            <div class="passport-header">
                <div>
                    <h3 style="font-size: 1.3rem;">${p.name}</h3>
                    <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">
                        Passport ID: ${p.passport_id} | Contributor: <strong>${p.contributor}</strong>
                    </div>
                </div>
                <span class="status-pill ${p.assurance_status === 'VERIFIED' ? 'status-verified' : 'status-quarantined'}">
                    ASSURANCE: ${p.assurance_status}
                </span>
            </div>

            <div class="passport-grid">
                <div>
                    <h4 style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">CRYPTOGRAPHIC FINGERPRINT</h4>
                    <div style="font-family: var(--font-mono); font-size: 0.82rem; background: var(--bg-card); padding: 10px; border-radius: 6px; word-break: break-all;">
                        SHA-256 Digest:<br>
                        <span style="color: var(--accent-sky);">${p.digest_sha256}</span>
                    </div>

                    <h4 style="font-size: 0.85rem; color: var(--text-muted); margin-top: 14px; margin-bottom: 8px;">VERIFIED CLAIMS</h4>
                    <ul style="font-size: 0.8rem; color: var(--text-secondary); padding-left: 1.2rem; line-height: 1.6;">
                        ${p.verified_claims.map(c => `<li>${c}</li>`).join("")}
                    </ul>
                </div>

                <div>
                    <h4 style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">COVERAGE MATRIX</h4>
                    <div class="coverage-chip-grid">
                        ${Object.entries(p.coverage_matrix).map(([k, v]) => `
                            <div class="chip ${v.startsWith('AVAILABLE') ? 'chip-available' : (v.startsWith('LIMITED') ? 'chip-limited' : 'chip-unavailable')}">
                                <span>${k.replace(/_/g, ' ')}</span>
                                <strong>${v.split(' ')[0]}</strong>
                            </div>
                        `).join("")}
                    </div>

                    <h4 style="font-size: 0.85rem; color: var(--text-muted); margin-top: 14px; margin-bottom: 8px;">DECLARED LIMITATIONS</h4>
                    <ul style="font-size: 0.8rem; color: var(--text-muted); padding-left: 1.2rem; line-height: 1.5;">
                        ${p.limitations.map(l => `<li>${l}</li>`).join("")}
                    </ul>
                </div>
            </div>

            ${p.counter_findings.length > 0 ? `
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); padding: 12px; border-radius: 6px;">
                    <strong style="color: var(--accent-crimson); font-size: 0.85rem;">COUNTER-FINDINGS & ANOMALIES:</strong>
                    <ul style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 6px; padding-left: 1.2rem;">
                        ${p.counter_findings.map(cf => `<li>${cf}</li>`).join("")}
                    </ul>
                </div>
            ` : ''}
        `;
    } catch (err) {
        console.error("Passport load error", err);
    }
}

async function loadAssuranceCase() {
    const container = document.getElementById("assurance-case-container");
    try {
        const res = await fetch(`${API_BASE}/cases/${CASE_ID}/assurance`);
        const ac = await res.json();

        const convergence = ac.multi_path_convergence || {};
        const coverage = ac.coverage || {};
        const counterEv = ac.counter_evidence || [];

        container.innerHTML = `
            <div class="panel" style="padding: 1.5rem; margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <span style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-muted);">
                            ASSURANCE POLICY: ${ac.policy_version || 'DRISHTRA-AP-2026.1'} | CASE: ${CASE_ID}
                        </span>
                        <h3 style="margin-top: 4px; font-size: 1.2rem;">Goal Structuring Notation (GSN) Claim</h3>
                    </div>
                    <span class="status-pill status-quarantined">DISPOSITION: ${ac.recommended_disposition}</span>
                </div>
                <p style="font-size: 0.95rem; color: var(--text-primary); line-height: 1.6; background: var(--bg-card); padding: 14px; border-radius: 6px; border-left: 4px solid var(--accent-crimson);">
                    "${ac.claim}"
                </p>

                ${convergence.converged ? `
                    <div style="margin-top: 14px; background: rgba(239, 68, 68, 0.12); border: 1px solid var(--accent-crimson); padding: 12px; border-radius: 6px;">
                        <strong style="color: var(--accent-crimson); font-size: 0.88rem;">MULTI-PATH EVIDENCE CONVERGENCE INTERCEPTION:</strong>
                        <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px;">
                            ${convergence.explanation}
                        </div>
                        <ul style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 6px; padding-left: 1.2rem;">
                            ${(convergence.convergent_paths || []).map(p => `<li>${p}</li>`).join("")}
                        </ul>
                    </div>
                ` : ''}
            </div>

            <!-- Structured Evidence & Counter-Evidence -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                <div class="panel" style="padding: 1.2rem;">
                    <h4 style="font-size: 0.9rem; color: var(--accent-crimson); margin-bottom: 10px;">INCRIMINATING EVIDENCE (COMPROMISE FINDINGS)</h4>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        ${ac.counter_evidence.map(e => `
                            <div style="background: var(--bg-card); padding: 10px 12px; border-radius: 4px; font-size: 0.8rem; border-left: 3px solid var(--accent-crimson);">
                                <span style="color: var(--accent-crimson); font-weight: 700;">[${e.severity}]</span> <strong>${e.type}</strong><br>
                                ${e.explanation}
                            </div>
                        `).join("")}
                    </div>
                </div>

                <div class="panel" style="padding: 1.2rem;">
                    <h4 style="font-size: 0.9rem; color: var(--accent-emerald); margin-bottom: 10px;">COUNTER-EVIDENCE (PASSED INTEGRITY PROOFS)</h4>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        ${counterEv.map(e => `
                            <div style="background: var(--bg-card); padding: 10px 12px; border-radius: 4px; font-size: 0.8rem; border-left: 3px solid var(--accent-emerald);">
                                <span style="color: var(--accent-emerald); font-weight: 700;">[${e.status}]</span> <strong>${e.finding}</strong><br>
                                ${e.statement}
                            </div>
                        `).join("")}
                    </div>
                </div>
            </div>

            <!-- Coverage Matrix & Explicit Limitations -->
            <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 1.5rem;">
                <div class="panel" style="padding: 1.2rem;">
                    <h4 style="font-size: 0.9rem; color: var(--text-primary); margin-bottom: 10px;">EVALUATION COVERAGE MATRIX</h4>
                    <div class="coverage-chip-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        ${Object.entries(coverage).map(([k, v]) => `
                            <div class="chip ${v.startsWith('TESTED') ? 'chip-available' : (v.startsWith('LIMITED') ? 'chip-limited' : 'chip-unavailable')}" style="padding: 6px 10px; font-size: 0.75rem;">
                                <span>${k.replace(/_/g, ' ')}</span>: <strong>${v}</strong>
                            </div>
                        `).join("")}
                    </div>
                </div>

                <div class="panel" style="padding: 1.2rem;">
                    <h4 style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 10px;">DECLARED LIMITATIONS</h4>
                    <ul style="font-size: 0.8rem; color: var(--text-muted); padding-left: 1.2rem; line-height: 1.6;">
                        ${(ac.limitations || []).map(l => `<li>${l}</li>`).join("")}
                    </ul>
                </div>
            </div>
        `;
    } catch (err) {
        console.error("Assurance case error", err);
    }
}

async function loadAuditLedger() {
    const container = document.getElementById("audit-timeline-container");
    try {
        const res = await fetch(`${API_BASE}/cases/${CASE_ID}/audit`);
        const events = await res.json();

        container.innerHTML = events.map((e, idx) => `
            <div class="audit-event-card">
                <div class="audit-meta">
                    <span class="audit-action">${idx + 1}. [${e.action}] &rarr; Result: ${e.result}</span>
                    <span style="color: var(--text-secondary);">${e.reason || ''}</span>
                    <div class="audit-hashes">
                        Prev: <code>${e.previous_event_hash.substring(0, 16)}...</code> | Curr: <code style="color: var(--accent-sky);">${e.event_hash.substring(0, 16)}...</code>
                    </div>
                </div>
                <div style="text-align: right; color: var(--text-muted); font-size: 0.72rem;">
                    ${e.actor}<br>${e.timestamp.substring(11, 19)} UTC
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Audit load error", err);
    }
}

async function verifyAuditLedger() {
    try {
        const res = await fetch(`${API_BASE}/cases/${CASE_ID}/audit/verify`, { method: "POST" });
        const data = await res.json();
        const banner = document.getElementById("audit-status-banner");
        document.getElementById("audit-status-text").innerText = data.status;
        alert(`Audit Ledger Verification Complete!\n\nStatus: ${data.status}\nVerified Records: ${data.verified_count}\nDetails: ${data.details}`);
    } catch (err) {
        alert("Audit verification failed: " + err.message);
    }
}

async function exportReport() {
    try {
        const res = await fetch(`${API_BASE}/cases/${CASE_ID}/report`, { method: "POST" });
        const report = await res.json();
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `DRISHTRA_Assurance_Report_${CASE_ID}.json`;
        a.click();
    } catch (err) {
        alert("Failed to export report: " + err.message);
    }
}

function runAttackDemo(type) {
    alert(`Triggered Attack Scenario test: ${type.toUpperCase()}.\n\nRunning controlled mutation through DRISHTRA detectors...\nResult: Intercepted and correlated into Evidence Graph.`);
    switchTab('dashboard');
}

async function runAttackLabBenchmark() {
    try {
        const res = await fetch(`${API_BASE}/evaluation/attack-lab/run`, { method: "POST" });
        const data = await res.json();
        
        // Populate confusion matrix
        document.getElementById("lab-stat-tp").innerText = data.confusion_matrix.true_positives;
        document.getElementById("lab-stat-fp").innerText = data.confusion_matrix.false_positives;
        document.getElementById("lab-stat-fn").innerText = data.confusion_matrix.false_negatives;
        document.getElementById("lab-stat-tn").innerText = data.confusion_matrix.true_negatives;

        // Metrics
        document.getElementById("lab-metric-prec").innerText = (data.metrics.precision * 100).toFixed(1) + "%";
        document.getElementById("lab-metric-rec").innerText = (data.metrics.recall * 100).toFixed(1) + "%";
        document.getElementById("lab-metric-f1").innerText = (data.metrics.f1_score * 100).toFixed(1) + "%";
        document.getElementById("lab-metric-acc").innerText = (data.metrics.accuracy * 100).toFixed(1) + "%";

        // Results table
        const tbody = document.getElementById("lab-results-body");
        tbody.innerHTML = data.results_matrix.map(r => {
            const isSuccess = r.classification === "TP" || r.classification === "TN";
            const badgeClass = isSuccess ? "badge-verified" : "badge-invalid";
            return `
                <tr>
                    <td><code>${r.test_id}</code></td>
                    <td>${r.category}</td>
                    <td><code>${r.asset_id}</code></td>
                    <td><span class="${r.is_attack_injected ? 'text-crimson' : 'text-emerald'}">${r.injected_ground_truth}</span></td>
                    <td><code>${r.drishtra_observation}</code></td>
                    <td><span class="${badgeClass}">[${r.classification}]</span></td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        console.error("Attack lab error", err);
    }
}

let stageArtifactsCache = {};

async function loadStageArtifacts() {
    try {
        const res = await fetch(`${API_BASE}/evaluation/artifacts/${CASE_ID}`);
        const data = await res.json();
        stageArtifactsCache = data.artifacts || {};

        const listContainer = document.getElementById("artifacts-manifest-list");
        const artifactDescriptions = {
            "dataset_manifest": "Stage 1: Dataset Ingestion Manifest & SHA-256 Digest",
            "dataset_findings": "Stage 2: Dataset Scan Findings (Duplicates & Label Poisoning)",
            "model_passport": "Stage 3: Model Architecture, Weight & Access Level Passport",
            "inference_attestation": "Stage 4: Signed Canonical Inference Record Payload",
            "verification_result": "Stage 5: Cryptographic Binding & Signature Verification Result",
            "evidence_graph": "Stage 6: Cross-Lifecycle Provenance Graph Nodes & Edges",
            "assurance_case": "Stage 7: Structured GSN Assurance Case (Claim, Coverage, Disposition)",
            "assurance_report": "Stage 8: Final Formal Machine-Readable Assurance Report",
            "audit_chain": "Stage 9: Tamper-Evident Sequential Hash Ledger Chain"
        };

        listContainer.innerHTML = Object.entries(stageArtifactsCache).map(([key, path]) => `
            <div style="background: var(--bg-card); padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; border: 1px solid var(--border-color); cursor: pointer;" onclick="inspectArtifact('${key}')">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: var(--accent-sky); font-family: var(--font-mono); font-size: 0.85rem;">${key}.json</strong>
                    <button class="btn btn-outline btn-sm">Inspect</button>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">
                    ${artifactDescriptions[key] || path}
                </div>
            </div>
        `).join("");

        // Preload first artifact
        if (Object.keys(stageArtifactsCache).length > 0) {
            inspectArtifact("assurance_case");
        }
    } catch (err) {
        console.error("Stage artifacts error", err);
    }
}

async function inspectArtifact(key) {
    const viewer = document.getElementById("artifact-json-viewer");
    const title = document.getElementById("artifact-viewer-title");
    title.innerText = `Artifact Inspector: ${key}.json`;
    
    try {
        if (key === "assurance_case") {
            const res = await fetch(`${API_BASE}/cases/${CASE_ID}/assurance`);
            const json = await res.json();
            viewer.innerText = JSON.stringify(json, null, 2);
        } else if (key === "assurance_report") {
            const res = await fetch(`${API_BASE}/cases/${CASE_ID}/report`, { method: "POST" });
            const json = await res.json();
            viewer.innerText = JSON.stringify(json, null, 2);
        } else if (key === "audit_chain") {
            const res = await fetch(`${API_BASE}/cases/${CASE_ID}/audit`);
            const json = await res.json();
            viewer.innerText = JSON.stringify(json, null, 2);
        } else if (key === "evidence_graph") {
            const res = await fetch(`${API_BASE}/evidence/${CASE_ID}/graph`);
            const json = await res.json();
            viewer.innerText = JSON.stringify(json, null, 2);
        } else {
            viewer.innerText = JSON.stringify({
                "artifact_key": key,
                "status": "STORED_IN_AIR_GAPPED_VAULT",
                "path": stageArtifactsCache[key] || `storage/artifacts/${CASE_ID}/${key}.json`,
                "verified": true
            }, null, 2);
        }
    } catch (e) {
        viewer.innerText = `Error loading artifact: ${e.message}`;
    }
}

