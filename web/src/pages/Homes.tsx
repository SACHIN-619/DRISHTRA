import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { ROLE_LABEL, Role, useAuth } from "../auth";
import { Link, navigate } from "../router";
import { Card, Empty, ErrorBox, Icon, Kpi, Loading, PageHead, Pill, Sev, ago, human, label, short, useApi, when } from "../ui";
import { SevCounts } from "./Shared";

/** Hero entry into the live pipeline (ML + Security homes). */
export function StudioBanner() {
  return (
    <div className="studio-banner">
      <div className="sb-l">
        <div className="sb-eyebrow"><span className="live-dot" />Live assurance</div>
        <h2>Run the 18-stage pipeline and watch every stage report.</h2>
        <p>Inject a real attack in the Attack Lab — poisoned data, swapped weights, a tampered or replayed signed record — then watch which stage catches it and how the verdict changes.</p>
        <div className="sb-cta">
          <Link to="/studio" className="btn sb-primary"><Icon name="bolt" />Open Pipeline Studio</Link>
          <Link to={`/studio/CASE-2026-DRISHTRA-DEMO`} className="btn sb-ghost">Replay the C-07 investigation</Link>
        </div>
      </div>
      <div className="sb-r" aria-hidden="true">
        {Array.from({ length: 18 }).map((_, i) => <i key={i} style={{ animationDelay: `${i * 0.12}s` }} className={[6, 10].includes(i) ? "hit" : ""} />)}
        <div className="sb-cap">18 chained stages · 12 published checks · signed outcome</div>
      </div>
    </div>
  );
}

function Greeting() {
  const { user } = useAuth();
  return <>{user?.capabilities?.question}</>;
}

/* ================================================================== ML ANALYST */
export function MLHome() {
  const cases = useApi<any[]>("/api/v1/cases");
  const q = useApi<any>("/api/v1/assurance/queue");
  const ds = useApi<any[]>("/api/v1/datasets");
  const ms = useApi<any[]>("/api/v1/models");
  const inf = useApi<any[]>("/api/v1/inferences");
  const f = useApi<any[]>("/api/v1/findings");
  const items = q.data?.items || [];
  const attention = items.filter((i: any) => i.recommended_disposition !== "ACCEPT" || (i.coverage_percent ?? 0) < 100);
  return (
    <div>
      <PageHead eyebrow="ML Operations" title="What assets need my attention?" sub="Prepare datasets and models, run assurance, and fix what the checks could not assess."
        actions={<><Link to="/intake" className="btn primary"><Icon name="upload" />Ingest assets</Link><Link to="/studio" className="btn"><Icon name="play" />Start a run</Link></>} />
      <StudioBanner />
      <div className="grid g4 mb">
        <Kpi label="Datasets" value={ds.data?.length ?? "—"} foot="registered & hashed" />
        <Kpi label="Models" value={ms.data?.length ?? "—"} foot="registered digests" />
        <Kpi label="Inference records" value={inf.data?.length ?? "—"} foot={`${(inf.data || []).filter(x => x.verification_status === "VERIFIED").length} verified`} />
        <Kpi label="Open findings" value={(f.data || []).filter(x => ["CRITICAL", "HIGH", "MEDIUM"].includes(x.severity)).length} tone="warn" foot="medium or above" />
      </div>
      <div className="grid g-main">
        <Card title="Needs attention" hint="Cases with findings or untested checks" flush>
          {q.loading ? <Loading /> : attention.length === 0 ? <Empty>Every assessed case is fully covered and clean.</Empty> : (
            <table className="t"><thead><tr><th>Case</th><th>Recommendation</th><th>Coverage</th><th>Findings</th></tr></thead>
              <tbody>{attention.map((i: any) => (
                <tr key={i.case_id} className="click" onClick={() => navigate(`/cases/${i.case_id}`)}>
                  <td><b>{i.case_name}</b><div className="tiny mono muted">{i.case_id}</div></td>
                  <td><Pill s={i.recommended_disposition} /></td><td>{i.coverage_percent}%</td><td><SevCounts c={i.severity_counts} /></td>
                </tr>))}</tbody></table>
          )}
        </Card>
        <Card title="Recent assets">
          <ul className="list-clean">
            {[...(ds.data || []).map(d => ({ id: d.dataset_id, k: "Dataset", n: d.name, t: d.created_at })), ...(ms.data || []).map(m => ({ id: m.model_id, k: "Model", n: m.name, t: m.created_at }))]
              .sort((a, b) => (b.t || "").localeCompare(a.t || "")).slice(0, 8).map(a => (
                <li key={a.id} className="row between"><span><span className="tag">{a.k}</span> <Link to={`/passport/${a.id}`}><b>{a.id}</b></Link> <span className="small muted">{a.n}</span></span><span className="tiny muted">{ago(a.t)}</span></li>
              ))}
          </ul>
        </Card>
      </div>
      <Card title="Your boundary" className="mt">
        <p className="small muted">You prepare and assess assets. You cannot recommend or finalize a disposition, manage users, or read platform security events — that separation is enforced by the server, not just hidden in this screen.</p>
      </Card>
      {cases.error && <ErrorBox error={cases.error} />}
    </div>
  );
}

/* ================================================================== INTAKE */
export function IntakePage() {
  const cases = useApi<any[]>("/api/v1/cases");
  const [caseId, setCaseId] = useState("");
  const contribs = useApi<any[]>(caseId ? `/api/v1/contributors/case/${caseId}` : null, [caseId]);
  const [msg, setMsg] = useState<{ t: string; m: string } | null>(null);
  const done = (t: string, m: string) => { setMsg({ t, m }); contribs.reload(); cases.reload(); };

  const newCase = async (e: any) => {
    e.preventDefault(); const fd = new FormData(e.target);
    try { const c = await api<any>("/api/v1/cases", { body: { name: fd.get("name"), description: fd.get("desc"), classification: "RESTRICTED" } }); setCaseId(c.case_id); done("ok", `Case ${c.case_id} created.`); e.target.reset(); }
    catch (er: any) { done("bad", er.message); }
  };
  const newContrib = async (e: any) => {
    e.preventDefault(); const fd = new FormData(e.target);
    try { const c = await api<any>("/api/v1/contributors", { body: { case_id: caseId, name: fd.get("name"), contributor_type: fd.get("type") } }); done("ok", `Contributor ${c.contributor_id} registered (untrusted until assessed).`); e.target.reset(); }
    catch (er: any) { done("bad", er.message); }
  };
  const upload = async (e: any) => {
    e.preventDefault(); const fd = new FormData(e.target); fd.set("case_id", caseId);
    try { const r = await api<any>("/api/v1/datasets/upload", { form: fd }); done("ok", `Dataset ${r.dataset_id}: ${r.records} records, sha256 ${short(r.sha256, 16)}. Perceptual hashing ${r.perceptual_hashing}.`); e.target.reset(); }
    catch (er: any) { done("bad", er.message); }
  };
  const model = async (e: any) => {
    e.preventDefault(); const fd = new FormData(e.target);
    try {
      const file = fd.get("file") as File;
      let r: any;
      if (file && file.size) { fd.set("case_id", caseId); r = await api<any>("/api/v1/models/upload", { form: fd }); }
      else r = await api<any>("/api/v1/models/register", { body: { case_id: caseId, contributor_id: fd.get("contributor_id"), name: fd.get("model_name"), architecture: fd.get("architecture"), format: "ONNX", access_level: fd.get("access_level"), weight_sha256: fd.get("weight_sha256") || undefined } });
      done("ok", `Model ${r.model_id} registered with digest ${short(r.weight_sha256, 16)}.`); e.target.reset();
    } catch (er: any) { done("bad", er.message); }
  };
  const cOpts = (contribs.data || []).map(c => <option key={c.contributor_id} value={c.contributor_id}>{c.contributor_id} · {c.name}</option>);

  return (
    <div>
      <PageHead eyebrow="Trust boundary" title="Ingest assets" sub="Nothing is trusted on arrival: every file is size- and type-checked, hashed, parsed into canonical records and recorded in the audit ledger before it can be assessed." />
      {msg && <div className={`alert ${msg.t} mb`}>{msg.m}</div>}
      <div className="grid g2">
        <Card title="1 · Case">
          <div className="stack">
            <label className="field">Existing case
              <select value={caseId} onChange={e => setCaseId(e.target.value)}><option value="">Select…</option>{(cases.data || []).map(c => <option key={c.case_id} value={c.case_id}>{c.case_id} · {c.name}</option>)}</select>
            </label>
            <form onSubmit={newCase} className="stack">
              <div className="tiny muted">or create one</div>
              <input name="name" placeholder="Case name, e.g. Vendor B detector v3 submission" required />
              <input name="desc" placeholder="Short description" />
              <button className="btn">Create case</button>
            </form>
          </div>
        </Card>
        <Card title="2 · Contributor" hint="Who is supplying data or models">
          {!caseId ? <Empty>Select a case first.</Empty> : (
            <form onSubmit={newContrib} className="stack">
              <div className="small muted">On this case: {(contribs.data || []).map(c => c.contributor_id).join(", ") || "none yet"}</div>
              <input name="name" placeholder="Organisation name" required />
              <select name="type" defaultValue="VENDOR">{["VENDOR", "LAB", "FIELD_UNIT", "OPEN_SOURCE"].map(t => <option key={t}>{t}</option>)}</select>
              <button className="btn">Register contributor</button>
            </form>
          )}
        </Card>
        <Card title="3 · Dataset" hint="COCO .json, or .zip/.tar with COCO or YOLO labels (+ images for pixel hashing)">
          {!caseId ? <Empty>Select a case first.</Empty> : (
            <form onSubmit={upload} className="stack">
              <select name="contributor_id" required><option value="">Contributor…</option>{cOpts}</select>
              <input name="dataset_name" placeholder="Dataset name" required />
              <div className="row"><select name="format_type" style={{ flex: 1 }}><option>COCO</option><option>YOLO</option></select><input name="version" defaultValue="1.0.0" style={{ flex: 1 }} /></div>
              <input type="file" name="file" accept=".json,.zip,.tar,.gz,.tgz" required />
              <button className="btn primary"><Icon name="upload" />Ingest dataset</button>
            </form>
          )}
        </Card>
        <Card title="4 · Model" hint="Upload ONNX / PyTorch weights, or declare the registered SHA-256">
          {!caseId ? <Empty>Select a case first.</Empty> : (
            <form onSubmit={model} className="stack">
              <select name="contributor_id" required><option value="">Contributor…</option>{cOpts}</select>
              <input name="model_name" placeholder="Model name" required />
              <div className="row"><input name="architecture" defaultValue="YOLOv8s" style={{ flex: 1 }} />
                <select name="access_level" style={{ flex: 1 }}><option>BLACK_BOX</option><option>WHITE_BOX</option><option>STRUCTURAL_ONLY</option></select></div>
              <input type="file" name="file" accept=".onnx,.pt,.pth,.bin" />
              <input name="weight_sha256" placeholder="…or registered SHA-256 (64 hex chars)" pattern="[0-9a-f]{64}" />
              <button className="btn primary"><Icon name="cpu" />Register model</button>
            </form>
          )}
        </Card>
      </div>
      {caseId && <div className="row mt"><Link to={`/cases/${caseId}`} className="btn primary"><Icon name="play" />Go to case and start an assurance run</Link></div>}
    </div>
  );
}

/* ================================================================== SECURITY ANALYST */
export function SecurityHome() {
  const f = useApi<any[]>("/api/v1/findings");
  const q = useApi<any>("/api/v1/assurance/queue");
  const cr = useApi<any[]>("/api/v1/contributors");
  const ss = useApi<any>("/api/v1/platform/security-summary");
  const fs = f.data || [];
  const count = (s: string) => fs.filter(x => x.severity === s).length;
  const layerCounts = useMemo(() => {
    const m: Record<string, number> = { DATASET: 0, MODEL: 0, INFERENCE: 0 };
    fs.filter(x => ["CRITICAL", "HIGH", "MEDIUM"].includes(x.severity)).forEach(x => { m[x.asset_type] = (m[x.asset_type] || 0) + 1; });
    return m;
  }, [fs]);
  const max = Math.max(1, ...Object.values(layerCounts));
  const prio = (q.data?.items || []).filter((i: any) => i.recommended_disposition !== "ACCEPT");
  return (
    <div>
      <PageHead eyebrow="Security Operations" title="Where is the threat, and how is it connected?" sub="Investigate integrity findings across the lifecycle, correlate them, and recommend a disposition." />
      <StudioBanner />
      <div className="grid g4 mb">
        <Kpi label="Critical" value={count("CRITICAL")} tone="bad" foot="deterministic integrity failures" />
        <Kpi label="High" value={count("HIGH")} tone="warn" />
        <Kpi label="Cases to recommend on" value={prio.filter((i: any) => !i.analyst_recommendation).length} foot={`${prio.length} not clean`} />
        <Kpi label="Access denials" value={ss.data?.counts?.access_denied ?? "—"} foot={`${ss.data?.counts?.login_failed ?? 0} failed logins`} />
      </div>
      <div className="grid g-main">
        <Card title="Priority investigations" flush>
          {q.loading ? <Loading /> : prio.length === 0 ? <Empty>No open investigations.</Empty> : (
            <table className="t"><thead><tr><th>Case</th><th>Machine</th><th>Findings</th><th>Your recommendation</th></tr></thead>
              <tbody>{prio.map((i: any) => (
                <tr key={i.case_id} className="click" onClick={() => navigate(`/cases/${i.case_id}`)}>
                  <td><b>{i.case_name}</b><div className="tiny mono muted">{i.case_id}</div></td><td><Pill s={i.machine_status} /></td>
                  <td><SevCounts c={i.severity_counts} /></td><td>{i.analyst_recommendation ? <Pill s={i.analyst_recommendation} /> : <span className="small muted">pending</span>}</td>
                </tr>))}</tbody></table>
          )}
        </Card>
        <div className="stack">
          <Card title="Threat landscape" hint="Findings ≥ medium by lifecycle layer">
            <div className="bars">
              {Object.entries(layerCounts).map(([k, v]) => (
                <div className="bar-row" key={k}><span>{human(k)}</span><div className="bar"><i className={v ? "bad" : ""} style={{ width: `${(v / max) * 100}%` }} /></div><b>{v}</b></div>
              ))}
            </div>
          </Card>
          <Card title="Contributor risk" actions={<Link to="/contributors" className="small">All →</Link>}>
            <ul className="list-clean">{(cr.data || []).slice(0, 5).map(c => (
              <li key={c.contributor_id} className="row between"><span><b className="mono">{c.contributor_id}</b> <span className="small muted">{c.name}</span></span><Pill s={c.risk === "HIGH" ? "FINDING" : c.risk === "ELEVATED" ? "REVIEW" : "VERIFIED"} text={c.risk} /></li>
            ))}</ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function ContributorsPage() {
  const cr = useApi<any[]>("/api/v1/contributors");
  return (
    <div>
      <PageHead eyebrow="Correlation" title="Contributor risk" sub="Findings on a contributor's assets and on everything downstream of them (models trained on their data, inferences from those models)." />
      <Card flush>
        {cr.loading ? <Loading /> : <ErrorBox error={cr.error} />}
        <table className="t"><thead><tr><th>Contributor</th><th>Risk</th><th>Layers implicated</th><th>Findings</th><th>Assets</th><th>Case</th></tr></thead>
          <tbody>{(cr.data || []).map(c => (
            <tr key={c.contributor_id} className="click" onClick={() => navigate(`/cases/${c.case_id}`)}>
              <td><b className="mono">{c.contributor_id}</b><div className="small">{c.name}</div><div className="tiny muted">{c.type}</div></td>
              <td><Pill s={c.risk === "HIGH" ? "FINDING" : c.risk === "ELEVATED" ? "REVIEW" : "VERIFIED"} text={c.risk} /></td>
              <td>{c.layers_implicated.length ? c.layers_implicated.map((l: string) => <span key={l} className="tag" style={{ marginRight: 4 }}>{l}</span>) : <span className="muted small">none</span>}</td>
              <td><SevCounts c={c.severity_counts} /></td>
              <td className="tiny mono">{[...c.datasets, ...c.models, ...c.inferences].join(", ")}</td>
              <td className="tiny mono">{c.case_id}</td>
            </tr>))}</tbody></table>
      </Card>
    </div>
  );
}

/* ================================================================== REVIEWER */
export function ReviewHome() {
  const q = useApi<any>("/api/v1/assurance/queue");
  const items = q.data?.items || [];
  const rank: Record<string, number> = { QUARANTINE: 0, REVIEW: 1, ACCEPT: 2 };
  const pending = items.filter((i: any) => i.awaiting_decision && !i.legacy_policy)
    .sort((x: any, y: any) => (rank[x.recommended_disposition] ?? 3) - (rank[y.recommended_disposition] ?? 3));
  const decided = items.filter((i: any) => !i.awaiting_decision);
  const legacy = items.filter((i: any) => i.awaiting_decision && i.legacy_policy).length;
  return (
    <div>
      <PageHead eyebrow="Assurance Review Center" title="Which decisions need my authorization?" sub="You make the binding disposition. Every decision is signed, hash-linked and permanent; a later decision supersedes, never overwrites." />
      <div className="grid g4 mb">
        <Kpi label="Pending decisions" value={pending.length} tone={pending.length ? "warn" : "ok"} />
        <Kpi label="Quarantine recommended" value={pending.filter((i: any) => i.recommended_disposition === "QUARANTINE").length} tone="bad" />
        <Kpi label="Inconclusive" value={pending.filter((i: any) => i.machine_status === "INCONCLUSIVE").length} foot="coverage gaps" />
        <Kpi label="Decided" value={decided.length} tone="ok" />
      </div>
      {legacy > 0 && <div className="alert warn mb small">{legacy} older case(s) were assessed under the v1 policy and are hidden from this queue until an analyst re-runs assurance.</div>}
      <Card title="Review queue" flush>
        {q.loading ? <Loading /> : pending.length === 0 ? <Empty>Nothing awaiting your decision.</Empty> : (
          <table className="t"><thead><tr><th>Case</th><th>Machine recommendation</th><th>Coverage</th><th>Evidence</th><th>Analyst</th><th></th></tr></thead>
            <tbody>{pending.map((i: any) => (
              <tr key={i.case_id} className="click" onClick={() => navigate(`/cases/${i.case_id}`)}>
                <td><b>{i.case_name}</b><div className="tiny mono muted">{i.case_id}</div></td>
                <td><Pill s={i.recommended_disposition} /> <span className="tiny muted">{label(i.machine_status)}</span></td>
                <td>{i.coverage_percent}%</td><td><SevCounts c={i.severity_counts} /></td>
                <td>{i.analyst_recommendation ? <><Pill s={i.analyst_recommendation} /><div className="tiny muted">{i.analyst}</div></> : <span className="small muted">—</span>}</td>
                <td>{i.self_initiated ? <span className="pill warn plain">you initiated · cannot decide</span> : <span className="btn sm primary">Review →</span>}</td>
              </tr>))}</tbody></table>
        )}
      </Card>
      {decided.length > 0 && (
        <Card title="Recently decided" className="mt" flush>
          <table className="t"><tbody>{decided.map((i: any) => (
            <tr key={i.case_id} className="click" onClick={() => navigate(`/cases/${i.case_id}`)}><td><b>{i.case_name}</b></td><td><Pill s={i.final_disposition} /></td><td className="small muted">by {i.decided_by}</td><td className="small muted">machine: {i.recommended_disposition}</td></tr>
          ))}</tbody></table>
        </Card>
      )}
    </div>
  );
}

export function DecisionHistoryPage() {
  const cases = useApi<any[]>("/api/v1/cases");
  const [all, setAll] = useState<any[] | null>(null);
  useEffect(() => {
    if (!cases.data) return;
    Promise.all(cases.data.map(c => api<any>(`/api/v1/assurance/${c.case_id}/decisions`).then(r => r.items.map((d: any) => ({ ...d, case_name: c.name }))).catch(() => [])))
      .then(r => setAll(r.flat().sort((a, b) => (b.decided_at || "").localeCompare(a.decided_at || ""))));
  }, [cases.data]);
  return (
    <div>
      <PageHead eyebrow="Accountability" title="Decision history" sub="Every recommendation and disposition ever recorded. Nothing here can be edited or deleted — by anyone." />
      <Card flush>
        {!all ? <Loading /> : all.length === 0 ? <Empty>No decisions recorded yet.</Empty> : (
          <table className="t"><thead><tr><th>When</th><th>Case</th><th>Kind</th><th>Disposition</th><th>By</th><th>Rationale</th><th>Hash</th></tr></thead>
            <tbody>{all.map(d => (
              <tr key={d.decision_id} className="click" onClick={() => navigate(`/cases/${d.case_id}`)}>
                <td className="small">{when(d.decided_at)}</td><td><b className="small">{d.case_name}</b></td>
                <td><span className="tag">{d.kind}</span></td><td><Pill s={d.disposition} /></td><td className="small">{d.actor}<div className="tiny muted">{d.actor_role}</div></td>
                <td className="small" style={{ maxWidth: 320 }}>{d.rationale}</td><td><span className="hash">{short(d.decision_hash, 10)}</span></td>
              </tr>))}</tbody></table>
        )}
      </Card>
    </div>
  );
}

/* ================================================================== AUDITOR */
export function AuditHome() {
  const cases = useApi<any[]>("/api/v1/cases");
  const [res, setRes] = useState<Record<string, any>>({});
  const [plat, setPlat] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const verifyAll = async () => {
    setBusy(true);
    const out: Record<string, any> = {};
    for (const c of cases.data || []) {
      const [chain, dec] = await Promise.all([
        api<any>(`/api/v1/audit/${c.case_id}/verify`, { method: "POST" }).catch(e => ({ status: "ERROR", details: e.message })),
        api<any>(`/api/v1/assurance/${c.case_id}/decisions/verify`, { method: "POST" }).catch(e => ({ status: "ERROR", reason: e.message })),
      ]);
      out[c.case_id] = { chain, dec };
    }
    setRes(out);
    setPlat(await api<any>("/api/v1/platform/events/verify", { method: "POST" }).catch(e => ({ status: "ERROR", reason: e.message })));
    setBusy(false);
  };
  const verified = Object.values(res);
  const total = verified.reduce((n, r: any) => n + (r.chain.verified_count || 0), 0);
  const broken = verified.filter((r: any) => r.chain.status !== "VALID" || r.dec.status !== "VALID").length + (plat && plat.status !== "VALID" ? 1 : 0);
  return (
    <div>
      <PageHead eyebrow="Audit Assurance Center" title="Can I prove the history is intact?" sub="Recompute every hash chain independently: per-case ledgers, signed decision chains, and the platform governance ledger."
        actions={<button className="btn primary" disabled={busy || !cases.data} onClick={verifyAll}><Icon name="check" />{busy ? "Recomputing…" : "Verify all chains"}</button>} />
      <div className="grid g4 mb">
        <Kpi label="Chains checked" value={verified.length ? verified.length * 2 + 1 : "—"} />
        <Kpi label="Case events verified" value={verified.length ? total : "—"} />
        <Kpi label="Platform events" value={plat ? plat.verified_count : "—"} foot={plat ? `head ${short(plat.head_hash, 10)}` : ""} />
        <Kpi label="Broken" value={verified.length ? broken : "—"} tone={verified.length ? (broken ? "bad" : "ok") : undefined} />
      </div>
      <Card title="Case chains" flush>
        <table className="t"><thead><tr><th>Case</th><th>Audit ledger</th><th>Decision chain</th><th></th></tr></thead>
          <tbody>{(cases.data || []).map(c => {
            const r = res[c.case_id];
            return (
              <tr key={c.case_id}>
                <td><b>{c.name}</b><div className="tiny mono muted">{c.case_id}</div></td>
                <td>{r ? <><Pill s={r.chain.status} /> <span className="tiny muted">{r.chain.verified_count} events</span></> : <span className="muted small">not checked</span>}</td>
                <td>{r ? <><Pill s={r.dec.status} /> <span className="tiny muted">{r.dec.verified_count ?? 0} decisions{r.dec.reason ? ` · ${r.dec.reason}` : ""}</span></> : <span className="muted small">not checked</span>}</td>
                <td><Link to={`/cases/${c.case_id}`} className="small">Inspect →</Link></td>
              </tr>);
          })}</tbody></table>
      </Card>
      <Card title="Read-only by design" className="mt"><p className="small muted">Auditors can verify, inspect and export — but cannot modify findings, approve cases, manage users, rerun detectors or change policy. There is no API that edits or deletes history for any role.</p></Card>
    </div>
  );
}

export function PlatformLedgerPage({ admin }: { admin?: boolean }) {
  const { can } = useAuth();
  const cats = can("security_events:read") ? ["GOVERNANCE", "AUTH", "AUTHZ"] : ["GOVERNANCE"];
  const [cat, setCat] = useState("ALL");
  const ev = useApi<any>(`/api/v1/platform/events?${(cat === "ALL" ? cats : [cat]).map(c => `category=${c}`).join("&")}&limit=300`, [cat]);
  const ss = useApi<any>(can("security_events:read") ? "/api/v1/platform/security-summary" : null);
  const [v, setV] = useState<any>(null);
  return (
    <div>
      <PageHead eyebrow={admin ? "Administration" : "Platform"} title={admin ? "Governance & security events" : can("security_events:read") ? "Platform security" : "Platform ledger"}
        sub="Identity lifecycle, sign-ins and access denials. Hash-chained and kept separate from AI integrity findings."
        actions={can("audit:verify") && <button className="btn primary" onClick={async () => setV(await api("/api/v1/platform/events/verify", { method: "POST" }))}><Icon name="check" />Verify ledger</button>} />
      {v && <div className={`alert ${v.status === "VALID" ? "ok" : "bad"} mb`}>Platform ledger {v.status}: {v.verified_count} of {v.total} events verified{v.reason ? ` · ${v.reason} at #${v.failure_sequence}` : ""}.</div>}
      {ss.data && (
        <div className="grid g4 mb">
          <Kpi label="Successful sign-ins" value={ss.data.counts.login_succeeded} />
          <Kpi label="Failed sign-ins" value={ss.data.counts.login_failed} tone={ss.data.counts.login_failed ? "warn" : undefined} />
          <Kpi label="Lockouts" value={ss.data.counts.account_locked} tone={ss.data.counts.account_locked ? "bad" : undefined} />
          <Kpi label="Access denied" value={ss.data.counts.access_denied} foot="attempts beyond role" />
        </div>
      )}
      <div className="row mb">{["ALL", ...cats].map(c => <button key={c} className={`btn sm ${cat === c ? "primary" : ""}`} onClick={() => setCat(c)}>{c}</button>)}</div>
      <Card flush>
        {ev.loading ? <Loading /> : <ErrorBox error={ev.error} />}
        <div className="table-wrap"><table className="t"><thead><tr><th>#</th><th>When</th><th>Category</th><th>Actor</th><th>Action</th><th>Target</th><th>Result</th><th>Hash</th></tr></thead>
          <tbody>{(ev.data?.events || []).map((e: any) => (
            <tr key={e.event_id}><td className="mono small">{e.sequence}</td><td className="small">{when(e.timestamp)}</td><td><span className="tag">{e.category}</span></td>
              <td className="small">{e.actor}<div className="tiny muted">{e.actor_role}</div></td><td className="small"><b>{e.action}</b>{e.details && Object.keys(e.details).length > 0 && <div className="tiny muted">{Object.entries(e.details).map(([k, x]) => `${k}: ${typeof x === "object" ? JSON.stringify(x) : x}`).join(" · ").slice(0, 90)}</div>}</td>
              <td className="small mono">{e.target}</td><td><Pill s={e.result} text={e.result} /></td><td><span className="hash">{short(e.event_hash, 10)}</span></td></tr>
          ))}</tbody></table></div>
      </Card>
    </div>
  );
}

/* ================================================================== ADMINISTRATOR */
export function AdminHome() {
  const d = useApi<any>("/api/v1/system/diagnostics");
  const ss = useApi<any>("/api/v1/platform/security-summary");
  if (d.loading) return <Loading />;
  if (d.error) return <ErrorBox error={d.error} />;
  const checks = d.data.checks;
  return (
    <div>
      <PageHead eyebrow="System Administration" title="Is the platform securely governed?" sub="You operate the platform: identity, policy and health. You hold no assurance authority and cannot see findings or decide cases." />
      <div className="grid g4 mb">
        <Kpi label="Users" value={ss.data?.accounts?.total ?? "—"} foot={`${ss.data?.accounts?.active ?? 0} active · ${ss.data?.accounts?.pending_password_change ?? 0} pending first login`} />
        <Kpi label="Cases" value={d.data.counts.cases} />
        <Kpi label="Platform events" value={d.data.counts.platform_events} foot="hash-chained" />
        <Kpi label="Uptime" value={`${Math.round(d.data.uptime_seconds / 60)} min`} foot={`v${d.data.version} · ${d.data.environment}`} />
      </div>
      <div className="grid g-main">
        <Card title="System diagnostics">
          {Object.entries(checks).map(([k, v]: any) => (
            <div className="cov-row" key={k}>
              <div className={`cov-ico ${v.status === "OK" ? "PASS" : v.status === "WARN" ? "PARTIAL" : "FINDING"}`}>{v.status === "OK" ? "✓" : v.status === "WARN" ? "!" : "×"}</div>
              <div><b className="small">{human(k)}</b><div className="tiny muted">{Object.entries(v).filter(([x]) => x !== "status").map(([x, y]) => `${human(x)}: ${String(y)}`).join(" · ")}</div></div>
              <Pill s={v.status === "OK" ? "VERIFIED" : v.status === "WARN" ? "REVIEW" : "FAILED"} text={v.status} />
            </div>
          ))}
        </Card>
        <div className="stack">
          <Card title="Accounts by role">
            <ul className="list-clean">{Object.entries(ss.data?.accounts?.by_role || {}).map(([r, n]: any) => <li key={r} className="row between"><span className="small">{ROLE_LABEL[r as Role] || human(r)}</span><b>{n}</b></li>)}</ul>
            <Link to="/admin/users" className="btn sm mt">Manage users →</Link>
          </Card>
          <Card title="What you cannot do">
            <ul className="list-clean small">{["Make, recommend or edit assurance decisions", "Run detectors or alter findings", "Delete or edit audit history", "Change your own role or disable yourself"].map(x => <li key={x}><span className="check-bad">×</span> {x}</li>)}</ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function UsersPage() {
  const u = useApi<any>("/api/v1/users");
  const { user: me } = useAuth();
  const [creating, setCreating] = useState(false);
  const [secret, setSecret] = useState<{ user: string; pw: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const act = async (fn: () => Promise<any>) => { setErr(null); try { await fn(); await u.reload(); } catch (e: any) { setErr(e.message); } };
  const create = async (e: any) => {
    e.preventDefault(); const fd = new FormData(e.target);
    await act(async () => {
      const r = await api<any>("/api/v1/users", { body: { username: fd.get("username"), full_name: fd.get("full_name"), role: fd.get("role"), access_scope: fd.get("scope") } });
      setSecret({ user: r.user.username, pw: r.temporary_password }); setCreating(false);
    });
  };
  if (u.loading) return <Loading />;
  const roles = Object.keys(u.data?.roles || {});
  return (
    <div>
      <PageHead eyebrow="Identity" title="Users & roles" sub="There is no public registration. Accounts are created here, start with a one-time temporary password, and every change is recorded in the platform ledger."
        actions={<button className="btn primary" onClick={() => setCreating(true)}><Icon name="users" />Create user</button>} />
      <ErrorBox error={err || u.error} />
      {secret && <div className="alert warn mb">Temporary password for <b>{secret.user}</b>: <span className="hash">{secret.pw}</span> — shown once. Hand it over through a separate channel; the user must change it at first sign-in. <button className="btn sm ghost" onClick={() => setSecret(null)}>Dismiss</button></div>}
      <Card flush>
        <div className="table-wrap"><table className="t"><thead><tr><th>User</th><th>Role</th><th>Scope</th><th>Status</th><th>Last sign-in</th><th>Created by</th><th></th></tr></thead>
          <tbody>{(u.data?.users || []).map((x: any) => {
            const self = x.user_id === me?.user_id;
            return (
              <tr key={x.user_id}>
                <td><b>{x.full_name}</b><div className="tiny mono muted">{x.username}{x.is_demo_account ? " · demo" : ""}</div></td>
                <td><select value={x.role} disabled={self} onChange={e => act(() => api(`/api/v1/users/${x.user_id}/role`, { method: "PATCH", body: { role: e.target.value } }))} style={{ width: 190 }}>
                  {roles.map(r => <option key={r} value={r}>{ROLE_LABEL[r as Role]}</option>)}</select></td>
                <td><span className="tag">{x.access_scope}</span></td>
                <td><Pill s={x.status} />{x.locked && <span className="pill bad plain" style={{ marginLeft: 4 }}>locked</span>}{x.must_change_password && <div className="tiny muted">pending first login</div>}</td>
                <td className="small muted">{x.last_login_at ? ago(x.last_login_at) : "never"}</td>
                <td className="small muted">{x.created_by}</td>
                <td><div className="row" style={{ justifyContent: "flex-end" }}>
                  {!self && <button className="btn sm" onClick={() => act(async () => { const r = await api<any>(`/api/v1/users/${x.user_id}/reset-password`, { method: "POST" }); setSecret({ user: x.username, pw: r.temporary_password }); })}>Reset password</button>}
                  {!self && <button className={`btn sm ${x.status === "ACTIVE" ? "" : "ok"}`} onClick={() => act(() => api(`/api/v1/users/${x.user_id}/status`, { method: "PATCH", body: { status: x.status === "ACTIVE" ? "DISABLED" : "ACTIVE" } }))}>{x.status === "ACTIVE" ? "Disable" : "Enable"}</button>}
                  {self && <span className="tiny muted">you</span>}
                </div></td>
              </tr>);
          })}</tbody></table></div>
      </Card>
      <Card title="Role boundaries" className="mt">
        <div className="grid g3">{roles.map(r => (
          <div key={r}><b className="small">{u.data.roles[r].title}</b><div className="tiny muted">{u.data.roles[r].mission}</div>
            <ul className="list-clean tiny">{u.data.roles[r].explicitly_forbidden.map((f: string) => <li key={f}><span className="check-bad">×</span> {f}</li>)}</ul></div>
        ))}</div>
      </Card>
      {creating && (
        <div className="modal-back" onClick={() => setCreating(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="card-h"><h2>Create user</h2></div>
            <form className="card-b stack" onSubmit={create}>
              <label className="field">Username<input name="username" required pattern="[a-z][a-z0-9._-]{2,31}" placeholder="e.g. r.sharma" /></label>
              <label className="field">Full name<input name="full_name" required /></label>
              <label className="field">Role<select name="role">{roles.map(r => <option key={r} value={r}>{ROLE_LABEL[r as Role]}</option>)}</select></label>
              <label className="field">Access scope (prototype classification)<select name="scope" defaultValue="INTERNAL">{(u.data?.access_scopes || []).map((s: string) => <option key={s}>{s}</option>)}</select></label>
              <div className="row"><button className="btn primary">Create with temporary password</button><button type="button" className="btn" onClick={() => setCreating(false)}>Cancel</button></div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export { Greeting, Sev };
