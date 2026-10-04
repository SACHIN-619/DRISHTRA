import { Fragment, useMemo, useState } from "react";
import { useAuth } from "../auth";
import { Link, navigate } from "../router";
import {
  Card, COV_GLYPH, Empty, ErrorBox, Icon, Kpi, Loading, PageHead, Pill, Raw, Sev, ago, human, label, short, useApi, when,
} from "../ui";
import { Chain } from "./CaseView";

/* ------------------------------------------------------------------ Cases list */
export function CasesPage() {
  const cases = useApi<any[]>("/api/v1/cases");
  const { can } = useAuth();
  const queue = useApi<any>(can("evidence:read") ? "/api/v1/assurance/queue" : null);
  const byCase = useMemo(() => Object.fromEntries((queue.data?.items || []).map((i: any) => [i.case_id, i])), [queue.data]);
  return (
    <div>
      <PageHead eyebrow="Workspace" title="Cases" sub="Each case groups the contributors, datasets, models, runtimes and inferences assessed together."
        actions={can("case:create") && <Link to="/intake" className="btn primary"><Icon name="upload" />New case / ingest</Link>} />
      <Card flush>
        {cases.loading ? <Loading /> : <ErrorBox error={cases.error} />}
        <div className="table-wrap"><table className="t">
          <thead><tr><th>Case</th><th>Status</th><th>Machine recommendation</th><th>Coverage</th><th>Findings</th><th>Updated</th></tr></thead>
          <tbody>
            {(cases.data || []).map(c => {
              const q = byCase[c.case_id];
              return (
                <tr key={c.case_id} className="click" onClick={() => navigate(`/cases/${c.case_id}`)}>
                  <td><b>{c.name}</b><div className="tiny muted mono">{c.case_id}</div></td>
                  <td><Pill s={c.status} /></td>
                  <td>{q ? <><Pill s={q.recommended_disposition} />{q.legacy_policy && <span className="pill muted plain" style={{ marginLeft: 4 }}>v1 policy</span>}</> : <span className="muted small">{can("evidence:read") ? "Not assessed" : "—"}</span>}</td>
                  <td className="small">{q?.coverage_percent != null ? `${q.coverage_percent}%` : "—"}</td>
                  <td className="small">{q ? <SevCounts c={q.severity_counts} /> : "—"}</td>
                  <td className="small muted">{ago(c.updated_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      </Card>
    </div>
  );
}

export function SevCounts({ c }: { c: Record<string, number> }) {
  if (!c) return <>—</>;
  const parts = ["CRITICAL", "HIGH", "MEDIUM"].filter(k => c[k]);
  if (!parts.length) return <span className="muted">none ≥ medium</span>;
  return <span className="row" style={{ gap: 4 }}>{parts.map(k => <span key={k} className={`sev ${k}`} style={{ minWidth: 0 }}>{c[k]} {k[0]}</span>)}</span>;
}

/* ------------------------------------------------------------------ Findings */
export function FindingsPage() {
  const f = useApi<any[]>("/api/v1/findings");
  const [sev, setSev] = useState("ALL");
  const [layer, setLayer] = useState("ALL");
  const rank: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 };
  const rows = (f.data || []).filter(x => (sev === "ALL" || x.severity === sev) && (layer === "ALL" || x.asset_type === layer))
    .sort((a, b) => (rank[a.severity] ?? 5) - (rank[b.severity] ?? 5));
  return (
    <div>
      <PageHead eyebrow="AI integrity findings" title="Findings"
        sub="Produced by detectors on datasets, models and inferences. Platform security events (logins, denials) are kept separately." />
      <div className="row mb">
        <select value={sev} onChange={e => setSev(e.target.value)} style={{ width: 160 }}>{["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map(s => <option key={s}>{s}</option>)}</select>
        <select value={layer} onChange={e => setLayer(e.target.value)} style={{ width: 160 }}>{["ALL", "DATASET", "MODEL", "INFERENCE"].map(s => <option key={s}>{s}</option>)}</select>
        <span className="muted small">{rows.length} finding(s)</span>
      </div>
      <Card flush>
        {f.loading ? <Loading /> : <ErrorBox error={f.error} />}
        <div className="table-wrap"><table className="t">
          <thead><tr><th>Severity</th><th>Finding</th><th>Asset</th><th>Detector</th><th>Case</th><th></th></tr></thead>
          <tbody>
            {rows.map(x => (
              <tr key={x.finding_id} className="click" onClick={() => navigate(`/findings/${x.finding_id}`)}>
                <td><Sev s={x.severity} /></td>
                <td><b>{human(x.finding_type)}</b><div className="tiny muted">{x.explanation.slice(0, 120)}{x.explanation.length > 120 ? "…" : ""}</div></td>
                <td><span className="tag">{x.asset_type}</span> <span className="mono small">{x.asset_id}</span></td>
                <td className="small muted">{x.detector_id}</td>
                <td className="mono tiny">{x.case_id}</td>
                <td><span className="small" style={{ color: "var(--brand-2)" }}>Why? →</span></td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ Why flagged */
export function WhyPage({ findingId }: { findingId: string }) {
  const w = useApi<any>(`/api/v1/findings/${findingId}/why-flagged`);
  if (w.loading) return <Loading />;
  if (w.error) return <ErrorBox error={w.error} />;
  const d = w.data;
  const f = d.finding;
  const rec = d.recommendation || {};
  return (
    <div>
      <PageHead eyebrow={`Finding ${f.finding_id}`} title={d.question}
        sub={<span className="row"><Sev s={f.severity} /><b>{human(f.type)}</b><span className="muted">{f.detector_id} · {f.deterministic ? "deterministic" : `confidence ${f.confidence}`}</span></span>}
        actions={<><Link to={`/cases/${f.case_id}`} className="btn"><Icon name="flow" />Open case</Link><Link to={`/passport/${f.asset_id}`} className="btn"><Icon name="passport" />Passport</Link></>} />
      <div className={`verdict ${["CRITICAL", "HIGH"].includes(f.severity) ? "bad" : f.severity === "MEDIUM" ? "warn" : "info"}`} style={{ gridTemplateColumns: "1fr" }}>
        <div><div className="q">Answer{["LOW", "INFO"].includes(f.severity) ? " · informational, below the policy's evidence threshold" : ""}</div><div className="state" style={{ fontSize: 20 }}>{d.answer}</div><div className="claim">{f.explanation}</div></div>
      </div>
      <Card title="Trace: result → contributor" className="mt"><Chain passport={{ lineage: d.lineage, evidence: Object.values(d.evidence_by_layer || {}).flat() }} /></Card>
      <div className="grid g-main mt">
        <div className="stack">
          <Card title="Evidence along this lineage" hint={`${d.independent_paths} independent lifecycle layer(s) carry findings`}>
            {["INFERENCE", "MODEL", "DATASET"].filter(l => d.evidence_by_layer?.[l]).map(l => (
              <div key={l} className="mb">
                <h3>{human(l)}</h3>
                <ul className="list-clean">
                  {d.evidence_by_layer[l].map((e: any) => (
                    <li key={e.finding_id}><div className="row"><Sev s={e.severity} /><b className="small">{human(e.type)}</b><span className="tag">{e.asset_id}</span>
                      {e.finding_id === f.finding_id && <span className="pill info plain">this finding</span>}</div>
                      <div className="tiny muted mt-s">{e.explanation}</div></li>
                  ))}
                </ul>
              </div>
            ))}
          </Card>
          <Card title="Detector limitations">{f.limitations ? <p className="small">{f.limitations}</p> : <Empty>None stated.</Empty>}</Card>
        </div>
        <div className="stack">
          <Card title="Counter-evidence" hint="Checks on this lineage that ran and passed">
            {(d.counter_evidence || []).length === 0 ? <Empty>None.</Empty> :
              <ul className="list-clean">{d.counter_evidence.map((c: any, i: number) => <li key={i} className="small"><span className="check-ok">✓</span> {c.label} <span className="tag">{c.asset_id}</span></li>)}</ul>}
          </Card>
          <Card title="Not tested / limitations">
            {(d.limitations || []).length === 0 ? <Empty>None.</Empty> : <ul className="list-clean tiny">{d.limitations.slice(0, 8).map((l: string, i: number) => <li key={i}>{l}</li>)}</ul>}
          </Card>
          <Card title="Recommendation">
            <div className="row"><Pill s={rec.recommended_disposition} /> <span className="small muted">machine · {label(rec.machine_status)}</span></div>
            <div className="row mt-s">{rec.human_disposition ? <><Pill s={rec.human_disposition} /><span className="small muted">decided by {rec.decided_by}</span></> : <span className="small muted">No human decision yet.</span>}</div>
          </Card>
        </div>
      </div>
      <Raw data={d} />
    </div>
  );
}

/* ------------------------------------------------------------------ Passport */
export function PassportPage({ assetId }: { assetId: string }) {
  const p = useApi<any>(`/api/v1/passports/${assetId}`);
  if (p.loading) return <Loading />;
  if (p.error) return <ErrorBox error={p.error} />;
  const d = p.data;
  const id = d.identity;
  const rec = d.recommendation;
  const final = rec.human_disposition;
  const st = final || rec.recommended_disposition;
  return (
    <div>
      <PageHead eyebrow={`Assurance passport · ${id.asset_type}`} title={id.name || assetId}
        sub={<span className="row"><span className="mono">{assetId}</span><span className="tag">{id.evidence_label}</span><Link to={`/cases/${id.case_id}`}>{id.case_id}</Link></span>}
        actions={<button className="btn" onClick={() => { const b = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = `${d.passport_id}.json`; a.click(); }}><Icon name="doc" />Export signed passport</button>} />
      <div className="grid g-main">
        <div className="stack">
          <div className={`verdict ${final ? (final === "ACCEPT" ? "ok" : final === "REVIEW" ? "warn" : "bad") : rec.machine_status === "VERIFIED" ? "ok" : rec.machine_status === "INCONCLUSIVE" ? "info" : rec.recommended_disposition === "QUARANTINE" ? "bad" : "warn"}`} style={{ gridTemplateColumns: "1fr" }}>
            <div><div className="q">{final ? "Human disposition" : "Machine recommendation"}</div><div className="state">{label(st)}</div><div className="claim">{rec.claim}</div>
              {final && <div className="small muted mt-s">Decided by {rec.decided_by} · {when(rec.decided_at)} · machine recommended {rec.recommended_disposition}</div>}</div>
          </div>
          <Card title="Lineage"><Chain passport={d} /></Card>
          <Card title="Integrity by layer">
            <div className="layers">
              {Object.entries(d.integrity).map(([k, v]: any) => (
                <div className="layer" key={k}><div className="n">{k}</div><div className="s"><span className={`dot ${v.state === "VERIFIED" ? "ok" : v.state === "FINDING" ? "bad" : v.state === "INCOMPLETE" ? "warn" : "info"}`} />{label(v.state)}</div><div className="tiny muted">{v.assets.join(", ")}</div></div>
              ))}
            </div>
          </Card>
          <Card title="Evidence" hint="Findings on this asset and everything upstream of it">
            {d.evidence.length === 0 ? <Empty>No findings.</Empty> : (
              <ul className="list-clean">{d.evidence.map((e: any) => (
                <li key={e.finding_id} className="row between"><span className="row"><Sev s={e.severity} /><b className="small">{human(e.type)}</b><span className="tag">{e.asset_id}</span></span><Link to={`/findings/${e.finding_id}`}>Why? →</Link></li>
              ))}</ul>
            )}
          </Card>
        </div>
        <div className="stack">
          <Card title="Identity">
            <dl className="kv">
              {Object.entries(id).filter(([k]) => !["asset_id", "case_id", "name", "evidence_label"].includes(k)).map(([k, v]: any) => (
                <Fragment key={k}><dt>{human(k)}</dt><dd className={String(v).length > 30 ? "mono tiny" : ""}>{String(v ?? "—")}</dd></Fragment>
              ))}
              <dt>Source</dt><dd>{d.source?.name} <span className="tag">{d.source?.id}</span></dd>
            </dl>
          </Card>
          <Card title="Checks on this asset">
            {d.coverage.map((c: any) => (
              <div className="cov-row" key={c.check_id}><div className={`cov-ico ${c.outcome}`}>{COV_GLYPH[c.outcome]}</div><div><div className="small"><b>{c.label}</b></div><div className="tiny muted">{c.detail}</div></div><Pill s={c.outcome} /></div>
            ))}
          </Card>
          <Card title="Counter-evidence">
            {d.counter_evidence.length === 0 ? <Empty>None.</Empty> : <ul className="list-clean">{d.counter_evidence.map((c: any, i: number) => <li key={i} className="small"><span className="check-ok">✓</span> {c.label} <span className="tag">{c.asset_id}</span></li>)}</ul>}
          </Card>
          <Card title="Limitations">{d.limitations.length === 0 ? <Empty>None declared.</Empty> : <ul className="list-clean tiny">{d.limitations.map((l: string, i: number) => <li key={i}>{l}</li>)}</ul>}</Card>
          <Card title="Passport integrity">
            <dl className="kv"><dt>Digest</dt><dd className="mono tiny">{d.passport_digest}</dd><dt>Signer key</dt><dd className="mono tiny">{short(d.signer_key_fingerprint, 24)}</dd><dt>Issued</dt><dd>{when(d.issued_at)}</dd></dl>
          </Card>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Coverage statement */
export function CoverageStatementPage({ publicView }: { publicView?: boolean }) {
  const s = useApi<any>("/api/v1/system/coverage-statement");
  if (s.loading) return <Loading />;
  const d = s.data;
  if (!d) return <ErrorBox error={s.error} />;
  const layers = ["DATASET", "MODEL", "INFERENCE"];
  return (
    <div>
      {!publicView && <PageHead eyebrow={d.policy_version} title="Coverage statement" sub="What DRISHTRA checks, what each check needs, and what is out of scope. Published so nobody mistakes silence for safety." />}
      <div className="grid g3">
        {layers.map(l => (
          <Card key={l} title={human(l)}>
            <ul className="list-clean">{d.checks.filter((c: any) => c.layer === l).map((c: any) => (
              <li key={c.check_id}><div className="small"><b>{c.label}</b> <span className="tiny muted mono">{c.check_id}</span></div><div className="tiny muted">{c.description}</div></li>
            ))}</ul>
          </Card>
        ))}
      </div>
      <div className="grid g2 mt">
        <Card title="Coverage states">
          <ul className="list-clean">{Object.entries(d.states).map(([k, v]: any) => <li key={k} className="row" style={{ alignItems: "flex-start" }}><div className={`cov-ico ${k}`}>{COV_GLYPH[k]}</div><div><b className="small">{label(k)}</b><div className="tiny muted">{v}</div></div></li>)}</ul>
        </Card>
        <div className="stack">
          <Card title="Model access assumptions">
            <ul className="list-clean">{Object.entries(d.access_assumptions).map(([k, v]: any) => <li key={k} className="small"><span className="tag">{k}</span> {v}</li>)}</ul>
          </Card>
          <Card title="Out of scope (declared)">
            <ul className="list-clean small">{d.out_of_scope.map((o: string) => <li key={o}><span className="muted">○</span> {o}</li>)}</ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Assets */
export function AssetsPage() {
  const d = useApi<any[]>("/api/v1/datasets");
  const m = useApi<any[]>("/api/v1/models");
  const i = useApi<any[]>("/api/v1/inferences");
  const [tab, setTab] = useState("d");
  return (
    <div>
      <PageHead eyebrow="Registry" title="Assets" sub="Every dataset, model and inference is an identifiable, hashed asset with a passport." />
      <div className="grid g3 mb">
        <Kpi label="Datasets" value={d.data?.length ?? "—"} />
        <Kpi label="Models" value={m.data?.length ?? "—"} />
        <Kpi label="Inference attestations" value={i.data?.length ?? "—"} foot={`${(i.data || []).filter(x => x.verification_status !== "VERIFIED").length} not verified`} />
      </div>
      <div className="tabs">{[["d", "Datasets"], ["m", "Models"], ["i", "Inferences"]].map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      <Card flush>
        <div className="table-wrap"><table className="t">
          {tab === "d" && <><thead><tr><th>Dataset</th><th>Format</th><th>Samples</th><th>Contributor</th><th>Digest</th><th>Case</th></tr></thead>
            <tbody>{(d.data || []).map(x => <tr key={x.dataset_id} className="click" onClick={() => navigate(`/passport/${x.dataset_id}`)}><td><b>{x.name}</b><div className="tiny mono muted">{x.dataset_id}</div></td><td><span className="tag">{x.format}</span></td><td>{x.sample_count}</td><td className="mono small">{x.contributor_id}</td><td><span className="hash">{short(x.sha256)}</span></td><td className="mono tiny">{x.case_id}</td></tr>)}</tbody></>}
          {tab === "m" && <><thead><tr><th>Model</th><th>Format</th><th>Access</th><th>Contributor</th><th>Registered digest</th><th>Case</th></tr></thead>
            <tbody>{(m.data || []).map(x => <tr key={x.model_id} className="click" onClick={() => navigate(`/passport/${x.model_id}`)}><td><b>{x.name}</b><div className="tiny mono muted">{x.model_id} · v{x.version}</div></td><td><span className="tag">{x.format}</span></td><td><span className="tag">{x.access_level}</span></td><td className="mono small">{x.contributor_id}</td><td><span className="hash">{short(x.weight_sha256)}</span></td><td className="mono tiny">{x.case_id}</td></tr>)}</tbody></>}
          {tab === "i" && <><thead><tr><th>Inference</th><th>Model</th><th>Signer</th><th>Nonce</th><th>Verification</th><th>Case</th></tr></thead>
            <tbody>{(i.data || []).map(x => <tr key={x.inference_id} className="click" onClick={() => navigate(`/passport/${x.inference_id}`)}><td><b className="mono">{x.inference_id}</b><div className="tiny muted">seq {x.sequence}</div></td><td className="mono small">{x.model_id}</td><td className="small">{x.signer}</td><td className="mono tiny">{x.nonce}</td><td><Pill s={x.verification_status} /></td><td className="mono tiny">{x.case_id}</td></tr>)}</tbody></>}
        </table></div>
      </Card>
    </div>
  );
}
