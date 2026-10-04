import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Link, navigate } from "../router";
import {
  Card, COV_GLYPH, Dot, Empty, ErrorBox, Icon, Loading, Meter, Pill, Raw, Sev, ago, human, label, short, tone, useApi, when,
} from "../ui";
import { EvidenceGraph } from "./EvidenceGraph";

const LAYERS = ["DATASET", "MODEL", "INFERENCE"] as const;
const LAYER_NAME: Record<string, string> = { DATASET: "Data", MODEL: "Model", INFERENCE: "Inference", RUNTIME: "Runtime" };

export function verdictOf(ac: any) {
  const final = (ac?.decisions || []).filter((d: any) => d.kind === "DISPOSITION").slice(-1)[0];
  if (final) {
    const map: Record<string, [string, string]> = { ACCEPT: ["ok", "ACCEPTED"], REVIEW: ["warn", "UNDER REVIEW"], QUARANTINE: ["bad", "QUARANTINED"] };
    return { final, cls: map[final.disposition][0], text: map[final.disposition][1], human: true };
  }
  const m: Record<string, [string, string]> = {
    QUARANTINE_RECOMMENDED: ["bad", "QUARANTINE RECOMMENDED"], REVIEW_REQUIRED: ["warn", "REVIEW REQUIRED"],
    INCONCLUSIVE: ["info", "INCONCLUSIVE"], VERIFIED: ["ok", "VERIFIED · ACCEPT RECOMMENDED"],
  };
  const [cls, text] = m[ac?.status] || ["info", ac?.status || "NOT ASSESSED"];
  return { final: null, cls, text, human: false };
}

export function CaseView({ caseId }: { caseId: string }) {
  const { can } = useAuth();
  const c = useApi<any>(`/api/v1/cases/${caseId}`);
  const ac = useApi<any>(`/api/v1/assurance/${caseId}`);
  const [tab, setTab] = useState("why");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ t: string; m: string } | null>(null);
  const [replay, setReplay] = useState(0);

  const run = async () => {
    setBusy("run"); setMsg(null);
    try {
      const r = await api<any>(`/api/v1/cases/${caseId}/pipeline/run`, { method: "POST" });
      setMsg({ t: r.status === "COMPLETED" ? "ok" : "bad", m: `Pipeline ${r.run_id}: ${r.status}. ${r.stages.filter((s: any) => s.status === "SKIPPED").length} stage(s) skipped for missing inputs.` });
      await ac.reload(); await c.reload(); setReplay(Date.now()); setTab("pipeline");
    } catch (e: any) { setMsg({ t: "bad", m: e.message }); }
    setBusy(null);
  };
  const rebuild = async () => {
    setBusy("assess"); setMsg(null);
    try { await api(`/api/v1/assurance/${caseId}/assess`, { method: "POST" }); await ac.reload(); await c.reload(); setMsg({ t: "ok", m: "Assurance case rebuilt from current evidence." }); }
    catch (e: any) { setMsg({ t: "bad", m: e.message }); }
    setBusy(null);
  };

  if (c.loading) return <Loading />;
  if (c.error) return <ErrorBox error={c.error} />;
  const cs = c.data;
  const a = ac.data;
  const v = a ? verdictOf(a) : null;
  const tabs: [string, string][] = [
    ["why", "Why?"], ["lineage", "Trace evidence"], ["coverage", "Coverage & limits"], ["decision", "Decision"],
    ["pipeline", "Pipeline run"], ...(can("audit:read") ? [["audit", "Audit ledger"] as [string, string]] : []),
  ];

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="eyebrow"><Link to="/cases">Cases</Link> / <span className="mono">{cs.case_id}</span></div>
          <h1>{cs.name}</h1>
          <div className="sub row"><Pill s={cs.status} /><span className="tag">{cs.classification}</span><span>{cs.description}</span></div>
        </div>
        <div className="row">
          {can("pipeline:run") && <Link to={`/studio/${caseId}`} className="btn"><Icon name="bolt" />Watch live in Studio</Link>}
          {can("pipeline:run") && <button className="btn primary" disabled={!!busy} onClick={run}><Icon name="play" />{busy === "run" ? "Running 18 stages…" : "Start assurance run"}</button>}
          {can("assurance:build") && <button className="btn" disabled={!!busy} onClick={rebuild}><Icon name="refresh" />Rebuild case</button>}
        </div>
      </div>
      {msg && <div className={`alert ${msg.t} mb`}>{msg.m}</div>}

      {!a && ac.error && /not permitted/i.test(ac.error) ? (
        <Card><Empty>Your role sees the case registry only. Findings, evidence and decisions are visible to analysts, reviewers and auditors.</Empty></Card>
      ) : !a ? (
        <Card><Empty>No assurance case yet. {can("pipeline:run") ? "Start an assurance run to scan the stored assets." : "Waiting for an analyst to run the pipeline."}</Empty></Card>
      ) : (
        <>
          {a.policy_version !== "DRISHTRA-AP-2026.2" && <div className="alert warn mb">This assessment was produced by the v1 policy ({a.policy_version}), which had a known counter-evidence defect. Re-run assurance to reassess under the current policy.</div>}
          <div className={`verdict ${v!.cls}`}>
            <div>
              <div className="q">Can this AI result be trusted?</div>
              <div className="state">{v!.text}</div>
              <div className="claim">{a.claim}</div>
              <div className="row mt-s small muted">
                {v!.human
                  ? <>Decided by <b>{v!.final.actor}</b> {ago(v!.final.decided_at)} · machine recommended <b>{a.recommended_disposition}</b></>
                  : <>Machine recommendation only · awaiting a reviewer's decision · policy {a.policy_version}</>}
              </div>
            </div>
            <div style={{ minWidth: 300 }}>
              <div className="layers" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
                {LAYERS.map(l => {
                  const st = a.coverage_summary?.by_layer?.[l]?.state || "NOT_APPLICABLE";
                  return <div className="layer" key={l}><div className="n">{LAYER_NAME[l]}</div><div className="s"><Dot s={st === "INCOMPLETE" ? "PARTIAL" : st} />{label(st)}</div></div>;
                })}
              </div>
              <div className="mt-s small row between"><span className="muted">Evidence coverage</span><b>{a.coverage_summary?.percent ?? "—"}%</b></div>
              <Meter pct={a.coverage_summary?.percent || 0} />
            </div>
          </div>

          <div className="tabs mt">
            {tabs.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
          </div>
          {tab === "why" && <WhyTab a={a} />}
          {tab === "lineage" && <LineageTab caseId={caseId} />}
          {tab === "coverage" && <CoverageTab a={a} />}
          {tab === "decision" && <DecisionTab caseId={caseId} a={a} onDone={() => { ac.reload(); c.reload(); }} />}
          {tab === "pipeline" && <PipelineTab caseId={caseId} replay={replay} />}
          {tab === "audit" && <CaseAudit caseId={caseId} />}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Why */
function WhyTab({ a }: { a: any }) {
  const byLayer = useMemo(() => {
    const m: Record<string, any[]> = {};
    for (const e of a.evidence || []) (m[e.asset_type] ||= []).push(e);
    return m;
  }, [a]);
  const conv = a.convergence || {};
  // Counter-evidence about the flagged assets is the most informative (e.g. "digest matches
  // but behaviour deviates"), so it is listed first.
  const flagged = new Set((a.evidence || []).map((e: any) => e.asset_id));
  const counter = (a.counter_evidence || []).slice().sort((x: any, y: any) => Number(flagged.has(y.asset_id)) - Number(flagged.has(x.asset_id)));
  return (
    <div className="grid g-main">
      <div className="stack">
        <Card title="Evidence that supports the concern" hint={`${(a.evidence || []).length} finding(s) at MEDIUM or above, grouped by lifecycle layer`}>
          {(a.evidence || []).length === 0 && <Empty>No findings at MEDIUM severity or above.</Empty>}
          {LAYERS.filter(l => byLayer[l]).map(l => (
            <div key={l} className="mb">
              <div className="row between"><h3>{LAYER_NAME[l]} layer</h3><span className="tiny muted">{byLayer[l].length} finding(s)</span></div>
              <ul className="list-clean">
                {byLayer[l].map((e: any) => (
                  <li key={e.finding_id}>
                    <div className="row between">
                      <div className="row"><Sev s={e.severity} /><b>{human(e.type)}</b><span className="tag">{e.asset_id}</span></div>
                      <Link to={`/findings/${e.finding_id}`}>Why? →</Link>
                    </div>
                    <div className="small muted mt-s">{e.explanation}</div>
                    <div className="tiny muted">{e.deterministic ? "Deterministic check" : `Statistical · confidence ${e.confidence ?? "—"}`} · {e.detector_id}</div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </Card>
        {a.drift_assessment && (
          <Card title="Drift or manipulation?" hint="Distribution shift is not automatically an attack">
            <div className="row"><Pill s={a.drift_assessment.assessment === "PROBABLE_OPERATIONAL_DRIFT" ? "VERIFIED" : "FINDING"} text={human(a.drift_assessment.assessment)} /></div>
            <p className="mt-s">{a.drift_assessment.basis}</p>
            <div className="small muted mt-s">Possible explanations considered: {a.drift_assessment.possible_explanations.join(" · ")}</div>
          </Card>
        )}
      </div>
      <div className="stack">
        <Card title="Evidence convergence">
          <p><b>{conv.converged ? `${conv.path_count} independent evidence paths` : "No cross-layer convergence"}</b></p>
          <p className="small muted mt-s">{conv.explanation}</p>
          {(conv.contributors || []).map((c: any) => (
            <div key={c.contributor_id} className="alert bad mt-s small">Contributor <b>{c.contributor_id}</b> is upstream of findings on {c.layers.map((l: string) => LAYER_NAME[l]).join(", ")}.</div>
          ))}
          <div className="tiny muted mt-s">Rules fired: {(a.rules_fired || []).join("; ")}</div>
        </Card>
        <Card title="Counter-evidence" hint="Checks that actually ran and passed">
          {counter.length === 0 ? <Empty>No passed checks to cite.</Empty> : (
            <ul className="list-clean">
              {counter.slice(0, 12).map((c: any) => (
                <li key={c.execution_id || c.check_id + c.asset_id} className="row" style={{ alignItems: "flex-start" }}>
                  <span className="check-ok">✓</span>
                  <div><div className="small"><b>{c.label}</b> <span className="tag">{c.asset_id}</span>{flagged.has(c.asset_id) && <span className="pill info plain" style={{ marginLeft: 6 }}>on a flagged asset</span>}</div><div className="tiny muted">{c.detector_id} · {when(c.executed_at)}</div></div>
                </li>
              ))}
            </ul>
          )}
          {counter.length > 12 && <div className="tiny muted mt-s">+{counter.length - 12} more in the Coverage tab</div>}
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Lineage */
function LineageTab({ caseId }: { caseId: string }) {
  const infs = useApi<any[]>(`/api/v1/inferences?case_id=${caseId}`);
  const models = useApi<any[]>(`/api/v1/models?case_id=${caseId}`);
  const dsets = useApi<any[]>(`/api/v1/datasets?case_id=${caseId}`);
  const subjects = [
    ...(infs.data || []).map(i => ({ id: i.inference_id, k: "Inference", s: i.verification_status })),
    ...(models.data || []).map(m => ({ id: m.model_id, k: "Model", s: "" })),
    ...(dsets.data || []).map(d => ({ id: d.dataset_id, k: "Dataset", s: "" })),
  ];
  const flagged = subjects.find(s => ["INVALID_SIGNATURE", "TAMPERED", "REPLAY_DETECTED"].includes(s.s));
  const [sel, setSel] = useState<string | null>(null);
  const subject = sel || flagged?.id || subjects[0]?.id || null;
  const p = useApi<any>(subject ? `/api/v1/passports/${subject}` : null, [subject]);
  return (
    <div className="stack">
      <Card title="Reverse lineage" hint="From a result back to the contributor that supplied it"
        actions={<select value={subject || ""} onChange={e => setSel(e.target.value)} style={{ width: 260 }}>
          {subjects.map(s => <option key={s.id} value={s.id}>{s.k} {s.id}{s.s && s.s !== "VERIFIED" ? ` · ${label(s.s)}` : ""}</option>)}
        </select>}>
        {!p.data ? <Loading /> : <Chain passport={p.data} />}
        {p.data && <div className="row mt"><Link to={`/passport/${subject}`} className="btn sm"><Icon name="passport" />Open assurance passport</Link></div>}
      </Card>
      <Card title="Cross-lifecycle evidence graph" hint="Every edge is a recorded relationship: registration, training lineage, runtime binding, finding, passed check or declared limitation">
        <EvidenceGraph caseId={caseId} />
      </Card>
    </div>
  );
}

export function Chain({ passport }: { passport: any }) {
  const flaggedAssets = new Set((passport.evidence || []).map((e: any) => e.asset_id));
  const chain = passport.lineage || [];
  return (
    <div className="chain">
      {chain.map((n: any, i: number) => (
        <div key={n.layer + n.id} style={{ display: "flex" }}>
          {i > 0 && <div className="arrow">{n.relation}</div>}
          <div className={`node ${flaggedAssets.has(n.id) ? "flag" : n.layer === "CONTRIBUTOR" || n.layer === "RUNTIME" ? "" : "clear"}`}>
            <div className="k">{n.layer}</div>
            <div className="id">{n.id}</div>
            <div className="lbl">{n.label}</div>
            {flaggedAssets.has(n.id) && <div className="tiny" style={{ color: "var(--bad)", marginTop: 4 }}>{(passport.evidence || []).filter((e: any) => e.asset_id === n.id).length} finding(s)</div>}
            {n.digest && <div className="tiny muted mono" style={{ marginTop: 4 }}>{short(n.digest, 14)}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ Coverage */
export function CoverageTab({ a }: { a: any }) {
  const dims = Object.entries(a.coverage || {}) as [string, any][];
  return (
    <div className="grid g-main">
      <Card title="What was tested" hint={`${a.coverage_summary?.assessed_dimensions ?? 0} of ${a.coverage_summary?.applicable_dimensions ?? 0} applicable checks assessed · NOT TESTED is never counted as a pass`}>
        {LAYERS.map(layer => (
          <div key={layer} className="mb">
            <h3 className="mb" style={{ marginBottom: 4 }}>{LAYER_NAME[layer]}</h3>
            {dims.filter(([, d]) => d.layer === layer).map(([k, d]) => (
              <div className="cov-row" key={k}>
                <div className={`cov-ico ${d.state}`}>{COV_GLYPH[d.state]}</div>
                <div><div className="small"><b>{d.label}</b> <span className="tiny muted mono">{k}</span></div><div className="tiny muted">{d.detail}</div></div>
                <Pill s={d.state} />
              </div>
            ))}
          </div>
        ))}
      </Card>
      <div className="stack">
        <Card title="Known limitations" hint="What this assessment cannot tell you">
          {(a.limitations || []).length === 0 ? <Empty>None declared.</Empty> : (
            <ul className="list-clean small">{a.limitations.map((l: string, i: number) => <li key={i}>{l}</li>)}</ul>
          )}
        </Card>
        <Card title="Out of scope for this prototype">
          <ul className="list-clean small">{(a.coverage_summary?.out_of_scope || []).map((l: string) => <li key={l}><span className="muted">○</span> {l}</li>)}</ul>
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Decision */
function DecisionTab({ caseId, a, onDone }: { caseId: string; a: any; onDone: () => void }) {
  const { user, can } = useAuth();
  const [disp, setDisp] = useState<string>(a.recommended_disposition);
  const [why, setWhy] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [verify, setVerify] = useState<any>(null);
  const decisions = a.decisions || [];
  const mode = can("disposition:decide") ? "decide" : can("disposition:recommend") ? "recommend" : null;
  const blocked = mode === "decide" && (a.initiated_by === user?.username ||
    decisions.some((d: any) => d.kind === "RECOMMENDATION" && d.assurance_id === a.assurance_id && d.actor === user?.username));

  const submit = async () => {
    setErr(null); setOk(null);
    try {
      const r = await api<any>(`/api/v1/assurance/${caseId}/${mode}`, { body: { disposition: disp, rationale: why } });
      setOk(`${mode === "decide" ? "Decision" : "Recommendation"} ${r.decision.decision_id} signed and committed (hash ${short(r.decision.decision_hash, 16)}).`);
      setWhy(""); onDone();
    } catch (e: any) { setErr(e.message); }
  };
  const doVerify = async () => { try { setVerify(await api(`/api/v1/assurance/${caseId}/decisions/verify`, { method: "POST" })); } catch (e: any) { setVerify({ status: "ERROR", reason: e.message }); } };

  return (
    <div className="grid g-main">
      <Card title="Decision history" hint="Append-only. Each entry is hash-linked to the previous one and signed by the node key."
        actions={can("crypto:verify") && <button className="btn sm" onClick={doVerify}><Icon name="check" />Verify signatures</button>}>
        {verify && <div className={`alert ${verify.status === "VALID" ? "ok" : "bad"} mb small`}>{verify.status === "VALID" ? `Chain valid: ${verify.verified_count} decision(s), signer key ${short(verify.signer_key_fingerprint, 16)}` : `Verification failed: ${verify.reason || verify.status}`}</div>}
        {decisions.length === 0 ? <Empty>No human judgement recorded yet.</Empty> : (
          <div className="timeline">
            {decisions.slice().reverse().map((d: any) => (
              <div key={d.decision_id} className={`tl ${tone(d.disposition)}`}>
                <div className="row"><Pill s={d.disposition} /><b>{d.kind === "DISPOSITION" ? "Final disposition" : "Analyst recommendation"}</b><span className="muted small">by {d.actor} · {when(d.decided_at)}</span></div>
                <div className="small mt-s">“{d.rationale}”</div>
                <div className="tiny muted mono mt-s">{d.decision_id} · hash {short(d.decision_hash, 16)} · machine said {d.machine_recommendation}{d.supersedes_decision_id ? ` · supersedes ${d.supersedes_decision_id}` : ""}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
      <Card title={mode === "decide" ? (decisions.some((d: any) => d.kind === "DISPOSITION") ? "Supersede the decision" : "Final decision") : mode === "recommend" ? "Recommend a disposition" : "Who decides?"}
        hint={mode === "decide" && decisions.some((d: any) => d.kind === "DISPOSITION") ? "A new decision is appended; the earlier one stays on record." : undefined}>
        {!mode && <p className="small">Your role can read this case. Only a <b>Reviewer / Supervisor</b> can make the binding decision; a <b>Security Analyst</b> can recommend one.</p>}
        {mode && blocked && <div className="alert warn small">Separation of duties: you initiated or recommended on this evaluation, so another reviewer must decide.</div>}
        {mode && !blocked && (
          <div className="stack">
            <div className="small muted">Machine recommendation: <b>{a.recommended_disposition}</b> · coverage {a.coverage_summary?.percent}%</div>
            <div className="row">
              {["ACCEPT", "REVIEW", "QUARANTINE"].map(dv => (
                <button key={dv} className={`btn ${disp === dv ? (dv === "ACCEPT" ? "ok" : dv === "REVIEW" ? "warn" : "danger") : ""}`} onClick={() => setDisp(dv)}>{dv}</button>
              ))}
            </div>
            <label className="field">Rationale (recorded permanently)
              <textarea value={why} onChange={e => setWhy(e.target.value)} placeholder="What evidence did you weigh? What would change your decision?" />
            </label>
            {disp !== a.recommended_disposition && <div className="alert info small">You are departing from the machine recommendation. That is allowed; say why.</div>}
            <ErrorBox error={err} />
            {ok && <div className="alert ok small">{ok}</div>}
            <button className="btn primary" disabled={why.trim().length < 10} onClick={submit}><Icon name="lock" />{mode === "decide" ? "Sign & commit decision" : "Sign & submit recommendation"}</button>
          </div>
        )}
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Pipeline */
export function PipelineTab({ caseId, replay = 0 }: { caseId: string; replay?: number }) {
  const runs = useApi<any[]>(`/api/v1/cases/${caseId}/pipeline/runs`, [replay]);
  const list = (runs.data || []).slice().sort((x, y) => (y.started_at || "").localeCompare(x.started_at || ""));
  const r = list[0];
  const n = r?.stages?.length || 0;
  // After "Start assurance run", replay the recorded trace stage by stage so a viewer can
  // follow the chain. The data shown is the stored run, not a simulation.
  const [shown, setShown] = useState(Number.MAX_SAFE_INTEGER);
  useEffect(() => {
    if (!replay || !r || reducedMotionPref()) { setShown(Number.MAX_SAFE_INTEGER); return; }
    setShown(0);
    let i = 0;
    const t = setInterval(() => { i += 1; setShown(i); if (i >= n) clearInterval(t); }, 170);
    return () => clearInterval(t);
  }, [replay, r?.run_id]);
  if (runs.loading && !r) return <Loading />;
  if (!r) return <Card><Empty>No pipeline runs yet.</Empty></Card>;
  const done = Math.min(shown, n);
  const replaying = done < n;
  const totalMs = r.stages.reduce((a: number, s: any) => a + (s.duration_ms || 0), 0);
  const last = r.stages[n - 1];
  const chained = last?.output_summary?.chaining_checks_passed;
  return (
    <Card title={`Run ${r.run_id}`} hint={`${r.status} · started ${when(r.started_at)} · ${list.length} run(s) on record`}>
      <div className="run-head">
        <div className="run-prog"><i style={{ width: `${(done / Math.max(1, n)) * 100}%` }} /></div>
        <div className="run-meta mono">
          {replaying ? <>replaying recorded trace · stage {done + 1}/{n}</> : <>{n} stages · {totalMs.toFixed(0)} ms recorded</>}
          {!replaying && chained !== undefined && <span className={`chip ${chained ? "ok" : "bad"}`}>{chained ? "✓ every stage consumed the previous output" : "✕ chaining broken"}</span>}
        </div>
      </div>
      <div className="stages">
        {r.stages.map((s: any, i: number) => {
          const state = i < done ? s.status : "QUEUED";
          return (
            <div key={s.stage_id} className={`stage ${state} ${i === done - 1 && replaying ? "just" : ""}`}>
              <div className="no">{s.stage_id.slice(6, 8)} · {state}</div>
              <div className="nm">{s.stage_name}</div>
              {i < done && <>
                {s.output_summary?.output_digest && <div className="tiny muted mono">out {short(s.output_summary.output_digest, 10)}</div>}
                {s.evidence_generated > 0 && <div className="tiny" style={{ color: "var(--bad)" }}>{s.evidence_generated} finding(s)</div>}
                {(s.warnings || []).slice(0, 2).map((w: string, k: number) => <div className="w" key={k}>{w}</div>)}
                {(s.errors || []).map((w: string, k: number) => <div className="w" style={{ color: "var(--bad)" }} key={k}>{w}</div>)}
              </>}
            </div>
          );
        })}
      </div>
      <p className="tiny muted mt">SKIPPED means the stage had no stored input to work on; the corresponding checks appear as NOT TESTED in coverage, never as passes. Output digests let you confirm each stage consumed the previous stage's output.</p>
      <Raw data={r.stages} label="Show stage trace (inputs, outputs, digests)" />
    </Card>
  );
}

function reducedMotionPref() {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/* ------------------------------------------------------------------ Audit */
export function CaseAudit({ caseId }: { caseId: string }) {
  const ev = useApi<any[]>(`/api/v1/audit/${caseId}`);
  const { can } = useAuth();
  const [v, setV] = useState<any>(null);
  const verify = async () => { try { setV(await api(`/api/v1/audit/${caseId}/verify`, { method: "POST" })); } catch (e: any) { setV({ status: "ERROR", details: e.message }); } };
  return (
    <Card title="Case audit ledger" hint="H(n) = SHA-256(H(n−1) ‖ canonical(event n))"
      actions={can("audit:verify") && <button className="btn sm primary" onClick={verify}><Icon name="check" />Recompute chain</button>}>
      {v && <div className={`alert ${v.status === "VALID" ? "ok" : "bad"} mb small`}>Chain {v.status}: {v.verified_count} event(s) verified. {v.details}</div>}
      {ev.loading ? <Loading /> : <ErrorBox error={ev.error} />}
      <div className="table-wrap">
        <table className="t">
          <thead><tr><th>#</th><th>When</th><th>Actor</th><th>Action</th><th>Asset</th><th>Result</th><th>Event hash</th></tr></thead>
          <tbody>
            {(ev.data || []).slice().reverse().map(e => (
              <tr key={e.event_id}><td className="mono">{e.sequence}</td><td className="small">{when(e.timestamp)}</td><td>{e.actor}</td>
                <td className="small"><b>{e.action}</b></td><td className="mono small">{e.asset_id}</td><td><Pill s={e.result} text={e.result} /></td>
                <td><span className="hash">{short(e.event_hash, 14)}</span></td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function goCase(id: string) { navigate(`/cases/${id}`); }
