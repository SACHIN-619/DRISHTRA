/* Pipeline Studio — run the real 18-stage pipeline and watch it live.
   Events are streamed by the server as each stage executes (NDJSON). On the Attack Lab
   sandbox, attacks can be injected into the stored inputs first; the pipeline has to
   find them on its own. */
import { useEffect, useMemo, useRef, useState } from "react";
import { api, getToken } from "../api";
import { useAuth } from "../auth";
import { Link, navigate } from "../router";
import { Icon, Sev, short, useApi } from "../ui";

const LAB = "CASE-2026-ATTACK-LAB";
const PHASES: { name: string; tag: string; stages: number[] }[] = [
  { name: "Intake", tag: "trust nothing on arrival", stages: [0, 1] },
  { name: "Data", tag: "datasets · D1–D7", stages: [2, 3, 4] },
  { name: "Model", tag: "identity · behaviour", stages: [5, 6, 7] },
  { name: "Runtime & inference", tag: "binding · signatures · replay", stages: [8, 9, 10] },
  { name: "Correlate", tag: "graph · counter-evidence", stages: [11, 12, 13] },
  { name: "Assure", tag: "policy DRISHTRA-AP-2026.2", stages: [14] },
  { name: "Seal", tag: "ledger · report · trace", stages: [15, 16, 17] },
];
const LAYER_OF: Record<string, string> = { DATA: "Data", MODEL: "Model", INFERENCE: "Inference" };

type Stage = { stage_id: string; stage_name: string; status?: string; duration_ms?: number; input_summary?: any; output_summary?: any; warnings?: string[]; errors?: string[]; evidence_generated?: number };
type Feed = { key: string; stage: string; idx: number; check: string; asset: string; severity: string; title: string };

export function StudioPage({ caseId: initial }: { caseId?: string }) {
  const { can } = useAuth();
  const cases = useApi<any[]>("/api/v1/cases");
  const [caseId, setCaseId] = useState(initial || LAB);
  useEffect(() => { if (initial) setCaseId(initial); }, [initial]);
  const isLab = caseId === LAB;
  const lab = useApi<any>(isLab && can("attack:simulate") ? "/api/v1/attack-lab" : null, [caseId]);
  const [labBusy, setLabBusy] = useState<string | null>(null);

  const [pace, setPace] = useState(true);
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<Stage[]>([]);
  const [current, setCurrent] = useState(-1);
  const [open, setOpen] = useState<number | null>(null);
  const [feed, setFeed] = useState<Feed[]>([]);
  const [result, setResult] = useState<any>(null);
  const [assurance, setAssurance] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number>(0);
  const [elapsed, setElapsed] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => { reset(); }, [caseId]);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setElapsed(Date.now() - startedAt), 100);
    return () => clearInterval(t);
  }, [running, startedAt]);
  useEffect(() => () => abort.current?.abort(), []);
  // Follow the executing stage so the viewer never loses the run.
  useEffect(() => {
    if (!running || current < 0) return;
    document.getElementById(`srow-${current}`)?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [current, running]);

  function reset() {
    setStages([]); setCurrent(-1); setOpen(null); setFeed([]); setResult(null); setAssurance(null); setError(null); setElapsed(0);
  }

  async function run() {
    reset(); setRunning(true); setStartedAt(Date.now());
    const ctl = new AbortController(); abort.current = ctl;
    try {
      const res = await fetch(`/api/v1/cases/${caseId}/pipeline/stream?pace_ms=${pace ? 650 : 0}`, {
        method: "POST", headers: { Authorization: `Bearer ${getToken()}` }, signal: ctl.signal,
      });
      if (!res.ok || !res.body) throw new Error((await res.text()) || res.statusText);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let nl: number;
        while ((nl = buf.indexOf("\n")) >= 0) {
          const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
          if (line) onEvent(JSON.parse(line));
        }
      }
      const a = await api<any>(`/api/v1/assurance/${caseId}`).catch(() => null);
      setAssurance(a);
    } catch (e: any) {
      if (e.name !== "AbortError") setError(e.message);
    }
    setRunning(false);
  }

  function onEvent(e: any) {
    if (e.type === "run_started") setStages(e.stages);
    else if (e.type === "stage_started") { setCurrent(e.index); }
    else if (e.type === "stage_completed") {
      const s: Stage = e.stage;
      setStages(prev => prev.map((p, i) => (i === e.index ? { ...p, ...s } : p)));
      const checks = s.output_summary?.checks_executed || [];
      const hits: Feed[] = [];
      for (const c of checks) for (const f of c.findings || []) {
        hits.push({ key: f.finding_id, stage: s.stage_id, idx: e.index, check: c.check_id, asset: c.asset_id, severity: f.severity, title: f.title });
      }
      if (hits.length) { setFeed(prev => [...hits, ...prev]); setOpen(e.index); }
    } else if (e.type === "stage_failed") {
      setStages(prev => prev.map(p => (p.stage_id === e.stage.stage_id ? { ...p, ...e.stage } : p)));
    } else if (e.type === "run_finished") { setCurrent(-1); setResult(e); }
    else if (e.type === "assurance") setResult((r: any) => ({ ...(r || {}), assurance: e }));
    else if (e.type === "error") setError(e.message);
  }

  async function labAction(path: string, label: string) {
    setLabBusy(path);
    try {
      await api(`/api/v1/attack-lab/${path}`, { method: "POST" });
      await lab.reload(); reset();
      setToast(label); setTimeout(() => setToast(null), 3800);
    } catch (e: any) { setError(e.message); }
    setLabBusy(null);
  }

  const done = stages.filter(s => s.status).length;
  const total = stages.length || 18;
  const computeMs = stages.reduce((a, s) => a + (s.duration_ms || 0), 0);
  const chained = stages[17]?.output_summary?.chaining_checks_passed;
  const verdict = result?.assurance;
  const assetsHit = useMemo(() => new Set(feed.map(f => f.asset)), [feed]);
  const caught = useMemo(() => {
    const m: Record<string, Feed[]> = {};
    for (const f of feed) (m[f.check] ||= []).push(f);
    return m;
  }, [feed]);

  return (
    <div className="studio">
      <div className="studio-head">
        <div>
          <div className="eyebrow"><span className="live-dot" />Live assurance · Pipeline Studio</div>
          <h1>Watch the 18-stage pipeline run</h1>
          <div className="sub">Each stage is streamed from the server as it executes and consumes the previous stage's exact output.</div>
        </div>
        <div className="studio-ctl">
          <select value={caseId} onChange={e => { setCaseId(e.target.value); navigate(`/studio/${e.target.value}`); }} disabled={running}>
            {(cases.data || []).map((c: any) => <option key={c.case_id} value={c.case_id}>{c.case_id === LAB ? "★ " : ""}{c.name}</option>)}
          </select>
          <label className="pace" title="Pauses between stages so a viewer can follow. Reported stage times are the real compute times.">
            <input type="checkbox" checked={pace} onChange={e => setPace(e.target.checked)} disabled={running} /> Presentation pace
          </label>
          <button className="btn primary lg run-btn" onClick={run} disabled={running || !can("pipeline:run")}>
            <Icon name={running ? "refresh" : "play"} />{running ? `Running · ${done}/${total}` : "Run assurance pipeline"}
          </button>
        </div>
      </div>

      <div className="run-strip">
        <div className="run-prog big"><i style={{ width: `${(done / total) * 100}%` }} /></div>
        <div className="run-stats">
          <span><b>{done}</b>/{total} stages</span>
          <span><b>{computeMs.toFixed(0)}</b> ms compute</span>
          <span><b>{(elapsed / 1000).toFixed(1)}</b> s on screen{pace ? " (paced)" : ""}</span>
          <span><b className={feed.length ? "t-bad" : ""}>{feed.length}</b> findings</span>
          {chained !== undefined && <span className={`chip ${chained ? "ok" : "bad"}`}>{chained ? "✓ every stage consumed the previous stage's output" : "✕ stage chaining broken"}</span>}
        </div>
      </div>

      {toast && <div className="toast"><Icon name="bolt" /> {toast}</div>}
      {error && <div className="alert bad mb">{error}</div>}

      <div className="studio-grid">
        {/* ---------------- left: attack lab + lineage */}
        <aside className="studio-left">
          {isLab && lab.data && (
            <div className="card lab">
              <div className="lab-h">
                <div><div className="eyebrow">Attack Lab</div><h3>Attack the sandbox</h3></div>
                <button className="btn sm" disabled={!!labBusy || running || !lab.data.active.length} onClick={() => labAction("reset", "Sandbox restored to the clean, signed baseline.")}>
                  <Icon name="refresh" size={13} />Reset
                </button>
              </div>
              <p className="tiny muted">Each attack edits the stored inputs exactly as an adversary would. DRISHTRA is not told which one — the pipeline must find it.</p>
              {lab.data.scenarios.map((s: any) => {
                const hit = result && s.active && s.expected_checks.some((c: string) => caught[c]);
                const missed = result && s.active && !hit;
                return (
                  <div key={s.id} className={`atk ${s.active ? "on" : ""} ${hit ? "hit" : ""}`}>
                    <div className="atk-top">
                      <span className={`layer ${s.layer}`}>{LAYER_OF[s.layer]}</span>
                      <b>{s.title}</b>
                    </div>
                    <div className="atk-d">{s.attack}</div>
                    <div className="atk-f">
                      {hit ? <span className="caught">✓ Caught at stage {s.expected_stage.slice(6, 8)} · {s.expected_checks.filter((c: string) => caught[c]).map((c: string) => c.split("_")[0]).join(", ")}</span>
                        : missed ? <span className="t-bad">Not detected</span>
                        : s.active ? <span className="armed">● Injected — run the pipeline</span>
                        : <button className="btn sm danger-ghost" disabled={!!labBusy || running} onClick={() => labAction(`${s.id}/inject`, `Injected: ${s.title}. Run the pipeline and see whether it is caught.`)}>Inject</button>}
                    </div>
                  </div>
                );
              })}
              {result && lab.data.active.length > 0 && (
                <div className="score">
                  <b>{lab.data.scenarios.filter((s: any) => s.active && s.expected_checks.some((c: string) => caught[c])).length}</b> of <b>{lab.data.active.length}</b> injected attacks caught
                </div>
              )}
            </div>
          )}
          <Lineage stages={stages} hit={assetsHit} converged={assurance?.convergence} />
        </aside>

        {/* ---------------- center: pipeline */}
        <section className="pipe-col">
          {!stages.length && !running && (
            <div className="card pipe-empty">
              <Icon name="flow" size={28} />
              <h3>Ready to run</h3>
              <p className="muted small">{isLab ? "Inject one or more attacks on the left (or none, for a clean baseline), then run the pipeline." : "Run the pipeline on this case to stream every stage live."}</p>
              <button className="btn primary" onClick={run} disabled={!can("pipeline:run")}><Icon name="play" />Run assurance pipeline</button>
            </div>
          )}
          {stages.length > 0 && PHASES.map(ph => (
            <div key={ph.name} className="phase-block">
              <div className="phase-h"><b>{ph.name}</b><span>{ph.tag}</span></div>
              {ph.stages.map(i => {
                const s = stages[i];
                if (!s) return null;
                const st = s.status ? (s.status === "SUCCESS" && (s.output_summary?.checks_executed || []).some((c: any) => c.outcome === "FINDING") ? "FINDING" : s.status) : i === current ? "RUNNING" : "QUEUED";
                const nf = (s.output_summary?.checks_executed || []).reduce((a: number, c: any) => a + (c.findings?.length || 0), 0);
                return (
                  <div key={s.stage_id} id={`srow-${i}`} className={`srow ${st} ${open === i ? "open" : ""}`}>
                    <button className="srow-h" onClick={() => s.status && setOpen(open === i ? null : i)}>
                      <span className="sn">{st === "SUCCESS" ? "✓" : st === "FINDING" ? "!" : st === "FAILED" ? "✕" : String(i + 1).padStart(2, "0")}</span>
                      <span className="snm">{s.stage_name}</span>
                      {st === "RUNNING" && <span className="spin-t">executing…</span>}
                      {nf > 0 && <span className="sbadge">{nf} finding{nf > 1 ? "s" : ""}</span>}
                      {s.status && <span className="sms mono">{(s.duration_ms || 0).toFixed(1)} ms</span>}
                      {s.output_summary?.output_digest && <span className="sdg mono" title={s.output_summary.output_digest}>{short(s.output_summary.output_digest, 10)}</span>}
                    </button>
                    {st === "RUNNING" && <div className="scan" />}
                    {open === i && s.status && <StageDetail s={s} prev={stages[i - 1]} />}
                  </div>
                );
              })}
            </div>
          ))}
        </section>

        {/* ---------------- right: verdict + feed */}
        <aside className="studio-right">
          <VerdictCard running={running} done={done} total={total} verdict={verdict} assurance={assurance} stages={stages} caseId={caseId} />
          <div className="card feed">
            <div className="feed-h"><b>Findings, as they are discovered</b><span className="tiny muted">{feed.length}</span></div>
            {!feed.length && <div className="tiny muted" style={{ padding: "10px 0" }}>{running ? "Watching every check…" : "No findings yet."}</div>}
            {feed.map(f => (
              <div key={f.key} className="fitem" onClick={() => navigate(`/findings/${f.key}`)}>
                <Sev s={f.severity || "HIGH"} />
                <div><div className="fit">{(f.title || f.check).replace(/_/g, " ").toLowerCase()}</div>
                  <div className="tiny muted mono">{f.asset} · stage {f.stage.slice(6, 8)} · {f.check.split("_")[0]}</div></div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ stage detail */
function StageDetail({ s, prev }: { s: Stage; prev?: Stage }) {
  const o = s.output_summary || {}, inp = s.input_summary || {};
  const checks: any[] = o.checks_executed || [];
  const rows: [string, React.ReactNode][] = [];
  if (o.contributors) rows.push(["Contributors", o.contributors.join(", ")]);
  if (o.record_sets) rows.push(["Record sets read from vault", <Digests m={o.record_sets} />]);
  if (o.canonical_sets) rows.push(["Canonical records", <Digests m={o.canonical_sets} />]);
  if (o.models) rows.push(["Registered models", <Digests m={Object.fromEntries(Object.entries(o.models).map(([k, v]: any) => [k, v.registered_sha256]))} />]);
  if (o.digest_inputs) {
    rows.push(["Registered vs delivered", <div className="cmp">{Object.entries(o.digest_inputs).map(([m, v]: any) => {
      const reg = inp.registered?.[m];
      const ok = reg && reg === v.supplied_sha256;
      return <div key={m} className={`cmp-r ${ok ? "ok" : "bad"}`}><b>{m}</b><span className="mono">{short(reg, 14)}</span><span>{ok ? "=" : "≠"}</span><span className="mono">{short(v.supplied_sha256, 14)}</span><em>{ok ? "match" : "MISMATCH"}</em></div>;
    })}</div>]);
  }
  if (o.bindings) rows.push(["Runtime bindings", Object.entries(o.bindings).map(([r, b]: any) => `${r} → ${b.model_id}`).join(" · ")]);
  if (o.attestations) rows.push(["Signed attestations", Object.entries(o.attestations).map(([k, v]: any) => `${k} (${v.signer}${v.key_resolved ? ", key ✓" : ""})`).join(" · ")]);
  if (o.verification) rows.push(["Verification", <div className="vchips">{Object.entries(o.verification).map(([k, v]: any) => <span key={k} className={`vchip ${v === "VERIFIED" ? "ok" : "bad"}`}>{k} · {String(v).replace(/_/g, " ").toLowerCase()}</span>)}</div>]);
  if (o.nodes !== undefined) rows.push(["Evidence graph", `${o.nodes} nodes · ${o.edges} edges · ${o.converged ? `converged on layers ${o.layers?.join(", ")}` : "no convergence"}`]);
  if (o.outcomes) rows.push(["Check outcomes", Object.entries(o.outcomes).map(([k, v]) => `${v} ${k.replace(/_/g, " ").toLowerCase()}`).join(" · ")]);
  if (o.recommended_disposition) rows.push(["Assurance case", <><b>{String(o.status).replace(/_/g, " ")}</b> → recommended <b>{o.recommended_disposition}</b> ({o.assurance_id})</>]);
  if (o.event_hash) rows.push(["Ledger event", <span className="mono">{short(o.event_hash, 24)} · chain {o.chain_status}</span>]);
  if (o.chaining_checks_passed !== undefined) rows.push(["Stage chaining", o.chaining_checks_passed ? "All producer → consumer digests match" : "BROKEN"]);
  const prevOut = prev?.output_summary?.output_digest;
  return (
    <div className="sdetail">
      {(prevOut || o.output_digest) && (
        <div className="chainline mono">
          {prevOut && <span>in ← {short(prevOut, 16)}</span>}
          {o.output_digest && <span>out → {short(o.output_digest, 16)}</span>}
        </div>
      )}
      {rows.map(([k, v]) => <div key={k} className="kv"><span>{k}</span><div>{v}</div></div>)}
      {checks.length > 0 && (
        <table className="t ct">
          <thead><tr><th>Check</th><th>Asset</th><th>Outcome</th><th>What it found</th></tr></thead>
          <tbody>{checks.map((c, i) => (
            <tr key={i}><td className="mono">{c.check_id}</td><td className="mono">{c.asset_id}</td>
              <td><span className={`oc ${c.outcome}`}>{c.outcome.replace(/_/g, " ")}</span></td>
              <td className="small">{c.detail}</td></tr>
          ))}</tbody>
        </table>
      )}
      {(s.warnings || []).map((w, i) => <div key={i} className="w tiny">⚠ {w}</div>)}
      {(s.errors || []).map((w, i) => <div key={i} className="alert bad small">{w}</div>)}
    </div>
  );
}
function Digests({ m }: { m: Record<string, string> }) {
  return <div className="dg">{Object.entries(m).map(([k, v]) => <span key={k}><b>{k}</b> <span className="mono">{short(v, 12)}</span></span>)}</div>;
}

/* ------------------------------------------------------------------ lineage */
function Lineage({ stages, hit, converged }: { stages: Stage[]; hit: Set<string>; converged?: any }) {
  const contributors: string[] = stages[1]?.output_summary?.contributors || [];
  const datasets = Object.keys(stages[2]?.output_summary?.record_sets || {});
  const models = Object.keys(stages[5]?.output_summary?.models || {});
  const runtimes = Object.keys(stages[8]?.output_summary?.bindings || {});
  const infs = Object.keys(stages[9]?.output_summary?.attestations || {});
  const conv = new Set<string>((converged?.contributors || []).map((c: any) => c.contributor_id));
  const cols: [string, string[]][] = [["Contributor", contributors], ["Dataset", datasets], ["Model", models], ["Runtime", runtimes], ["Inference", infs]];
  return (
    <div className="card lin">
      <div className="eyebrow">Lineage under assessment</div>
      {!stages.length && <div className="tiny muted mt-s">Appears as the pipeline discovers each asset.</div>}
      <div className="lin-cols">
        {cols.map(([k, ids]) => (
          <div key={k} className="lin-col">
            <div className="lin-k">{k}</div>
            {ids.map(id => <div key={id} className={`lin-n ${hit.has(id) ? "bad" : ""} ${conv.has(id) ? "conv" : ""}`}>{id}</div>)}
            {!ids.length && stages.length > 0 && <div className="lin-n ghost">…</div>}
          </div>
        ))}
      </div>
      {converged?.converged && <div className="conv-note">{converged.explanation}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ verdict */
function VerdictCard({ running, done, total, verdict, assurance, stages, caseId }: any) {
  const m: Record<string, [string, string]> = {
    QUARANTINE_RECOMMENDED: ["bad", "QUARANTINE"], REVIEW_REQUIRED: ["warn", "REVIEW"],
    INCONCLUSIVE: ["info", "INCONCLUSIVE"], VERIFIED: ["ok", "ACCEPT"],
  };
  if (!verdict) {
    return (
      <div className={`card verdict-live ${running ? "busy" : ""}`}>
        <div className="eyebrow">Machine recommendation</div>
        <div className="vl-big muted-big">{running ? "Assessing…" : "—"}</div>
        <div className="tiny muted">{running ? `Stage ${Math.min(done + 1, total)} of ${total}. The verdict is computed only after every stage reports.` : "Run the pipeline to compute an evidence-based recommendation."}</div>
      </div>
    );
  }
  const [cls, word] = m[verdict.status] || ["info", verdict.recommended_disposition];
  const outcomes = stages[13]?.output_summary?.outcomes || {};
  return (
    <div className={`card verdict-live ${cls} pop`}>
      <div className="eyebrow">Machine recommendation</div>
      <div className="vl-big">{word}</div>
      <div className="vl-sub">{String(verdict.status).replace(/_/g, " ")}</div>
      {assurance?.convergence?.explanation && <p className="small mt-s">{assurance.convergence.explanation}</p>}
      <div className="vl-oc">
        <span className="ok">{outcomes.PASS || 0} passed</span>
        <span className="bad">{outcomes.FINDING || 0} findings</span>
        <span className="muted">{(outcomes.NOT_APPLICABLE || 0) + (outcomes.NOT_TESTED || 0)} n/a or not tested</span>
      </div>
      <div className="tiny muted mt-s">A recommendation only. A reviewer must sign the decision.</div>
      <Link to={`/cases/${caseId}`} className="btn sm mt-s">Open case · Why? <Icon name="arrow" size={13} /></Link>
    </div>
  );
}
