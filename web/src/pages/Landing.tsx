import { useEffect, useMemo, useState } from "react";
import "../landing.css";
import { ROLE_HOME, useAuth } from "../auth";
import { Link } from "../router";
import { CountUp, Reveal, SplitWords, Tilt, useInView, usePageProgress, usePointerGlow, useScrollProgress } from "../motion";
import { Icon, Logo, useApi } from "../ui";

/* Every claim on this page maps to something the product does today. Demo
   identifiers (C-07, D-14, M-04, R-02, I-883) are the synthetic demo case. */

export function Landing() {
  const { user } = useAuth();
  const enter = user ? ROLE_HOME[user.role] : "/login";
  const page = usePageProgress();
  const [solid, setSolid] = useState(false);
  useEffect(() => {
    const on = () => setSolid(window.scrollY > 40);
    on(); window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });

  return (
    <div className="lp">
      <div className="lp-progress" style={{ width: `${page * 100}%` }} />
      <nav className={`lp-nav ${solid ? "solid" : ""}`}>
        <div className="wrap in">
          <div className="brand"><Logo size={26} />DRISHTRA</div>
          <div className="links">
            {[["problem", "Problem"], ["pipeline", "Pipeline"], ["evidence", "Evidence"], ["decision", "Governance"], ["ledger", "Ledger"], ["architecture", "Architecture"]].map(([id, l]) =>
              <a key={id} href={`#/#${id}`} onClick={e => { e.preventDefault(); go(id); }}>{l}</a>)}
          </div>
          <div className="sp" />
          <span className="chip-air"><i />OFFLINE-FIRST</span>
          <Link to={enter} className="lbtn pri sm">{user ? "Open console" : "Enter system"}<Icon name="arrow" size={14} /></Link>
        </div>
      </nav>

      <Hero enter={enter} onPipeline={() => go("pipeline")} />
      <Problem />
      <Compare />
      <Pipeline />
      <Convergence />
      <Balance />
      <Passport />
      <Decision />
      <Ledger />
      <Architecture />
      <Roles />
      <Final enter={enter} />
    </div>
  );
}

/* =============================================================== HERO */
function Hero({ enter, onPipeline }: { enter: string; onPipeline: () => void }) {
  const glow = usePointerGlow<HTMLElement>();
  const tiles = [
    ["Contributor", "C-07", "untrusted vendor", "var(--amber)"],
    ["Dataset", "D-14", "4 findings", "var(--red)"],
    ["Model", "M-04", "digest ✓ · behaviour ✗", "var(--amber)"],
    ["Runtime", "R-02", "config bound", "var(--mint)"],
    ["Inference", "I-883", "signature invalid", "var(--red)"],
  ];
  return (
    <header className="hero2" ref={glow as any}>
      <div className="bgv"><video src="/media/background_video.mp4" poster="/media/background_video.jpg" autoPlay muted loop playsInline /></div>
      <div className="grid-bg" />
      <div className="wrap">
        <Reveal><span className="eyebrow">SIH26228 · Trustworthy computer-vision assurance</span></Reveal>
        <h1>
          <SplitWords text="Can we trust an AI result if we cannot trust the pipeline that produced it?"
            highlight={["pipeline", "that", "produced"]} stagger={45} />
        </h1>
        <Reveal delay={500}>
          <p className="lede">
            Datasets, models and inference records arrive from many contributors. DRISHTRA verifies each of them,
            connects the evidence across the whole lifecycle, and turns it into an assurance case that a human signs —
            fully offline.
          </p>
        </Reveal>
        <Reveal delay={700}>
          <div className="ctas">
            <Link to={enter} className="lbtn pri">Enter the system <Icon name="arrow" size={16} /></Link>
            <button className="lbtn" onClick={onPipeline}><Icon name="play" size={14} />Watch the pipeline</button>
          </div>
        </Reveal>
        <Reveal delay={900}>
          <div className="telemetry">
            {tiles.map(([k, v, s, c], i) => (
              <div key={k} className="tile" style={{ ["--c" as any]: c, ["--d" as any]: `${i * 0.35}s` }}>
                <div className="scan" />
                <div className="k">{k}</div><div className="v">{v}</div><div className="s">{s}</div>
              </div>
            ))}
          </div>
          <div className="tele-note">DEMO CASE · SYNTHETIC DATA · ONE LINEAGE, FIVE ASSETS, THREE INDEPENDENT EVIDENCE PATHS</div>
        </Reveal>
      </div>
      <div className="scrollhint">SCROLL<i /></div>
    </header>
  );
}

/* =============================================================== PROBLEM */
const STORY = [
  { c: "var(--mint)", no: "01 · LOOKS FINE", t: "The detector is 94% confident. The output is plausible.",
    p: "Nothing on the screen is wrong. Accuracy metrics are green. This is exactly when nobody asks where the result came from.", stat: "OUTPUT · ARMOURED_VEHICLE · 0.94", alert: null },
  { c: "var(--amber)", no: "02 · UPSTREAM", t: "The training batch was quietly poisoned.",
    p: "Subcontracted batch B-221 carries exact duplicates, near-duplicate floods, a conflicting label and out-of-distribution frames.", stat: "D-14 · 4 DATASET FINDINGS", alert: ["DATASET D-14", "POISONING INDICATORS"] },
  { c: "var(--red)", no: "03 · THE MODEL", t: "The weights are genuine. The behaviour is not.",
    p: "M-04's SHA-256 matches its registration — a hash check passes. Yet a small corner patch flips 'armoured vehicle' to 'civilian vehicle' at 96% confidence.", stat: "M-04 · DIGEST ✓ · TRIGGER ✗", alert: ["MODEL M-04", "BACKDOOR BEHAVIOUR"] },
  { c: "var(--red)", no: "04 · THE OUTPUT", t: "One record was altered after signing. Another is a replay.",
    p: "I-883's stored output no longer matches its Ed25519 signature. I-884 reuses an earlier nonce. Each tool sees one fragment — nobody sees the chain.", stat: "I-883 TAMPERED · I-884 REPLAY", alert: ["INFERENCE I-883", "TAMPERED RECORD"] },
];
function Problem() {
  const { ref, p } = useScrollProgress<HTMLDivElement>();
  const idx = Math.min(STORY.length - 1, Math.floor(p * STORY.length * 0.999));
  const s = STORY[idx];
  return (
    <section id="problem" className="sticky-wrap" ref={ref} style={{ height: "380vh" }}>
      <div className="sticky">
        <div className="wrap">
          <span className="eyebrow">Chapter 01 · The silent failure</span>
          <div className="story" style={{ marginTop: 28 }}>
            <div>
              <div className="story-steps">
                {STORY.map((st, i) => (
                  <div key={i} className={`story-step ${i === idx ? "on" : ""}`} style={{ ["--c" as any]: st.c }}>
                    <div className="no">{st.no}</div>
                    <h3>{st.t}</h3>
                    <p>{st.p}</p>
                    <div className="stat">{st.stat}</div>
                  </div>
                ))}
              </div>
              <div className="story-rail">
                {STORY.map((_, i) => {
                  const local = Math.min(1, Math.max(0, p * STORY.length - i));
                  return <i key={i}><b style={{ transform: `scaleX(${local})` }} /></i>;
                })}
              </div>
            </div>
            <div className="screen hud-corners">
              <video src="/media/problem_video.mp4" poster="/media/problem_video.jpg" autoPlay muted loop playsInline />
              <div className="ov" />
              <div className="hud"><span className="tag-hud">Concept visualisation</span><span className="tag-hud" style={{ color: s.c, borderColor: s.c }}>{s.no}</span></div>
              {STORY.map((st, i) => st.alert && (
                <div key={i} className={`alert-box ${i === idx ? "on" : ""}`} style={{ ["--c" as any]: st.c }}>
                  ⚠ {st.alert[0]}<b>{st.alert[1]}</b>
                </div>
              ))}
              <div className="cap">EVERY CHECK IS LOCAL · THE FAILURE IS IN THE CONNECTIONS</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== COMPARE */
function Compare() {
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.3 });
  return (
    <section className="sec">
      <div className="wrap">
        <Reveal><span className="eyebrow">Chapter 02 · Paradigm shift</span></Reveal>
        <h2 className="sec-title"><SplitWords text="Existing tools answer narrow questions. DRISHTRA answers the one that matters." highlight={["one", "that", "matters."]} /></h2>
        <Reveal delay={150}><p className="sec-lead">We don't replace hash checks, dataset scanners or audit logs. We compose them into one evidence chain — so a finding in the data, a deviation in the model and a broken signature on an output are recognised as the same story.</p></Reveal>
        <div className="compare" ref={ref}>
          <div className="isol">
            {[["Dataset scanner", "flags one dataset", "finding"], ["Model scanner", "inspects one file", "finding"], ["Signature check", "verifies one record", "verified"], ["Audit log", "lists events", "history"]].map(([a, b, c], i) => (
              <Reveal key={a} delay={i * 90}><div className="box"><div><b>{a}</b><br /><span>{b}</span></div><em>{c}</em></div></Reveal>
            ))}
            <Reveal delay={400}><div className="mono" style={{ fontSize: 11, color: "var(--tx-3)", textAlign: "center", marginTop: 4 }}>USEFUL CONTROLS · DISCONNECTED CONTEXT</div></Reveal>
          </div>
          <div className={`bridge ${inView ? "in" : ""}`}>
            <svg viewBox="0 0 120 300" width="120" height="300">
              {[40, 110, 180, 250].map((y, i) => <path key={i} d={`M0 ${y} C 60 ${y}, 60 150, 120 150`} stroke="#00e5ff" strokeWidth="1.6" fill="none" opacity=".7" style={{ transitionDelay: `${i * 150}ms` }} />)}
            </svg>
          </div>
          <Reveal delay={300}>
            <div className="pnl glow fabric hud-corners">
              <div className="row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <b style={{ color: "#fff" }}>DRISHTRA assurance fabric</b><span className="tag-hud">one evidence chain</span>
              </div>
              <div className="flow-line" />
              <div className="row4">
                {[["Ingest", "trust boundary"], ["Model", "digest + behaviour"], ["Runtime", "config bound"], ["Inference", "signed + fresh"]].map(([k, v]) => <div className="node" key={k}><div className="k">{k.toUpperCase()}</div><div className="v">{v}</div></div>)}
              </div>
              <div className="flow-line" />
              <div className="row4" style={{ gridTemplateColumns: "1.4fr 1fr 1fr" }}>
                <div className="node" style={{ borderColor: "rgba(255,181,71,.5)", background: "rgba(255,181,71,.06)" }}><div className="k" style={{ color: "var(--amber)" }}>CORRELATE</div><div className="v">evidence + counter-evidence</div></div>
                <div className="node" style={{ borderColor: "rgba(180,156,255,.5)", background: "rgba(180,156,255,.06)" }}><div className="k" style={{ color: "var(--violet)" }}>HUMAN</div><div className="v">signed decision</div></div>
                <div className="node" style={{ borderColor: "rgba(78,222,163,.5)", background: "rgba(78,222,163,.06)" }}><div className="k" style={{ color: "var(--mint)" }}>LEDGER</div><div className="v">hash-chained</div></div>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== PIPELINE */
const PHASES = [
  { n: "Ingest", d: "nothing trusted on arrival", stages: [0, 1, 2, 3] },
  { n: "Verify data", d: "D1–D7 battery", stages: [4] },
  { n: "Verify model", d: "identity + behaviour", stages: [5, 6, 7] },
  { n: "Verify inference", d: "binding, signature, replay", stages: [8, 9, 10] },
  { n: "Correlate", d: "graph + counter-evidence", stages: [11, 12, 13] },
  { n: "Assure", d: "assurance case", stages: [14] },
  { n: "Audit & export", d: "ledger, report, trace", stages: [15, 16, 17] },
];
const STAGES: [string, string, "ok" | "find" | "skip"][] = [
  ["Case validation", "The case exists, is classified and is the unit everything else is bound to.", "ok"],
  ["Contributor verification", "Every dataset and model must trace to a registered contributor — no orphans enter.", "ok"],
  ["Dataset ingestion", "Canonical records are loaded from the vault — the stored artifact, never a value typed in at run time.", "ok"],
  ["Normalization", "COCO / YOLO become one canonical record format. Malformed rows are counted, not silently dropped.", "ok"],
  ["Dataset integrity scan", "Exact & near duplicates, label conflicts, class balance, annotation validity, drift, out-of-distribution.", "find"],
  ["Model registration", "Each model carries the digest its contributor declared at registration.", "ok"],
  ["Model identity (D8A)", "The delivered artifact's SHA-256 is compared with the registered one. Substitution fails here.", "ok"],
  ["Behavioural probes (D8B)", "Black-box probes: does a small trigger patch flip the prediction? White-box analysis is declared out of scope.", "find"],
  ["Runtime binding", "The runtime configuration digest is bound to the model it serves.", "ok"],
  ["Attestation ingestion", "Signed inference records are collected and each signer key is resolved from the vault.", "ok"],
  ["Signature & replay (D9)", "Ed25519 over input, model, config and output digests; nonce freshness; claimed model = registered model.", "find"],
  ["Evidence normalization", "Every detector speaks one evidence contract — that is what lets them be correlated.", "ok"],
  ["Cross-lifecycle graph", "Contributor → dataset → model → runtime → inference, with findings attached where they occur.", "ok"],
  ["Counter-evidence", "Only checks that actually ran and passed can argue against the concern. Absence of a finding proves nothing.", "ok"],
  ["Assurance case", "Claim, evidence, counter-evidence, coverage, limitations, recommendation. The machine recommends; it never decides.", "ok"],
  ["Audit commitment", "The run is committed to a SHA-256 hash chain: H(n) = SHA-256(H(n−1) ‖ event).", "ok"],
  ["Machine report", "A machine-readable report is generated from the stored case, not from the UI.", "ok"],
  ["Trace & export", "pipeline_trace.json records every stage's input and output digest — proof the chain is unbroken.", "ok"],
];
function hexOf(seed: number) {
  let h = 2166136261 ^ seed;
  let s = "";
  for (let i = 0; i < 16; i++) { h = Math.imul(h ^ (h >>> 13), 16777619) >>> 0; s += (h & 0xffff).toString(16).padStart(4, "0"); }
  return s.slice(0, 64);
}
function Pipeline() {
  const { ref, p } = useScrollProgress<HTMLDivElement>();
  const idx = Math.min(17, Math.floor(p * 18 * 0.999));
  const [name, desc, st] = STAGES[idx];
  const phaseIdx = PHASES.findIndex(ph => ph.stages.includes(idx));
  const inD = idx === 0 ? "case:CASE-2026-DRISHTRA-DEMO" : hexOf(idx - 1 + 7);
  const outD = hexOf(idx + 7);
  return (
    <section id="pipeline" className="sticky-wrap" ref={ref} style={{ height: "560vh" }}>
      <div className="sticky">
        <div className="wrap" style={{ width: "100%" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 20, flexWrap: "wrap" }}>
            <div>
              <span className="eyebrow">Chapter 03 · The core pipeline</span>
              <h2 className="sec-title" style={{ fontSize: "clamp(30px,3.4vw,46px)" }}>18 stages. Every one consumes the last one's <span className="grad">exact output.</span></h2>
            </div>
            <span className="tag-hud">scroll to run</span>
          </div>
          <div className="pipe" style={{ marginTop: 34 }}>
            <div className="phases">
              {PHASES.map((ph, i) => (
                <div key={ph.n} className={`phase ${i < phaseIdx ? "done" : i === phaseIdx ? "on" : ""}`}>
                  <div className="i">{i < phaseIdx ? "✓" : i + 1}</div>
                  <div><b>{ph.n}</b><small>{ph.d}</small></div>
                </div>
              ))}
            </div>
            <div className="stage-big">
              <div className="count">STAGE</div>
              <div className="num">{String(idx + 1).padStart(2, "0")}<small>/ 18</small></div>
              <h3>{name}</h3>
              <p>{desc}</p>
              <div className={`st ${st}`}>{st === "find" ? "● FINDINGS PRODUCED" : st === "skip" ? "○ SKIPPED — NO INPUT" : "✓ COMPLETED"}</div>
              <div className="rail18">
                {STAGES.map((s, i) => <i key={i} className={i < idx ? (s[2] === "find" ? "find" : "done") : i === idx ? "on" : ""} />)}
              </div>
            </div>
            <div className="pnl glow digest hud-corners">
              <div className="h"><span>Stage chaining</span><span>illustrative digests</span></div>
              <div className="ln"><span>INPUT · from stage {String(Math.max(1, idx)).padStart(2, "0")}</span><code>{inD}</code></div>
              <div className="link">▼ MATCHES PREVIOUS OUTPUT ✓</div>
              <div className="ln"><span>OUTPUT · stage {String(idx + 1).padStart(2, "0")}</span><code>{outD}</code></div>
              <div className="emit">
                {idx === 4 && <>Emits <b>4 findings</b> on D-14 · passes on D-01</>}
                {idx === 6 && <>M-04 digest <b>matches</b> registration → counter-evidence</>}
                {idx === 7 && <>Trigger patch flips class at <b>96%</b> → HIGH finding</>}
                {idx === 10 && <>I-883 signature <b>invalid</b> · I-884 nonce <b>replayed</b></>}
                {idx === 14 && <>Recommendation: <b style={{ color: "var(--red)" }}>QUARANTINE</b> · coverage 100%</>}
                {idx === 15 && <>Event committed · chain <b>VALID</b></>}
                {![4, 6, 7, 10, 14, 15].includes(idx) && <>Recorded in the stage trace with its timing and warnings.</>}
              </div>
            </div>
          </div>
          <p className="mono" style={{ color: "var(--tx-3)", fontSize: 11, marginTop: 26, letterSpacing: ".06em" }}>
            A STAGE WITH NOTHING TO WORK ON REPORTS “SKIPPED” — NEVER “SUCCESS”. ITS CHECKS APPEAR AS NOT TESTED, NEVER AS PASSES.
          </p>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== CONVERGENCE */
function Convergence() {
  const { ref, p } = useScrollProgress<HTMLDivElement>();
  const step = Math.floor(p * 9);
  const nodes = [
    { id: "C-07", l: "Contributor", x: 20, f: 0 },
    { id: "D-14", l: "Dataset", x: 220, f: 4 },
    { id: "M-04", l: "Model", x: 420, f: 1 },
    { id: "R-02", l: "Runtime", x: 620, f: 0 },
    { id: "I-883", l: "Inference", x: 820, f: 1 },
  ];
  return (
    <section id="evidence" className="sticky-wrap" ref={ref} style={{ height: "320vh" }}>
      <div className="sticky">
        <div className="wrap" style={{ width: "100%" }}>
          <span className="eyebrow">Chapter 04 · Cross-lifecycle evidence</span>
          <h2 className="sec-title" style={{ fontSize: "clamp(30px,3.6vw,50px)" }}>One finding is noise. <span className="grad-red">Three that converge</span> is a story.</h2>
          <p className="sec-lead">Walk the lineage of a single result backwards. Each layer was checked by a different detector — and they all point at the same contributor.</p>
          <div className="pnl glow hud-corners" style={{ padding: "28px 24px", marginTop: 34 }}>
            <svg className="conv-svg" viewBox="0 0 1000 260">
              {nodes.slice(0, -1).map((n, i) => (
                <path key={i} className={`e ${step > i + 1 ? "vis" : ""}`} d={`M${n.x + 160} 110 L${nodes[i + 1].x} 110`} />
              ))}
              <path className={`back ${step >= 7 ? "vis" : ""}`} d="M900 160 C 900 240, 100 240, 100 160" />
              {nodes.map((n, i) => {
                const vis = step > i;
                const bad = step >= 6 && (n.f > 0 || n.id === "C-07");
                return (
                  <g key={n.id} className={`n ${vis ? "vis on" : ""} ${bad ? "bad" : ""}`}>
                    <rect x={n.x} y={70} width={160} height={80} rx={12} />
                    <text x={n.x + 16} y={100} fontSize="11" className="lbl">{n.l.toUpperCase()}</text>
                    <text x={n.x + 16} y={126} fontSize="20" fontWeight="700">{n.id}</text>
                    {n.f > 0 && <g className={`f ${step > i + 1 || step >= 6 ? "vis" : ""}`}>
                      <rect x={n.x + 92} y={56} width={64} height={22} rx={11} fill="#ff5d6c" />
                      <text x={n.x + 124} y={71} fontSize="11" textAnchor="middle" fontWeight="700">{n.f} finding{n.f > 1 ? "s" : ""}</text>
                    </g>}
                  </g>
                );
              })}
              <g className={`ok ${step >= 5 ? "vis" : ""}`}>
                <rect x={430} y={168} width={140} height={24} rx={12} fill="rgba(78,222,163,.12)" stroke="#4edea3" />
                <text x={500} y={184} fontSize="11" fill="#4edea3" textAnchor="middle" fontFamily="ui-monospace,monospace">✓ digest matches</text>
              </g>
              <g className={`ok ${step >= 5 ? "vis" : ""}`}>
                <rect x={630} y={168} width={140} height={24} rx={12} fill="rgba(78,222,163,.12)" stroke="#4edea3" />
                <text x={700} y={184} fontSize="11" fill="#4edea3" textAnchor="middle" fontFamily="ui-monospace,monospace">✓ config bound</text>
              </g>
              <text x={500} y={30} fontSize="12" fill="#6b8199" textAnchor="middle" fontFamily="ui-monospace,monospace" className={`ok ${step >= 7 ? "vis" : ""}`}>REVERSE LINEAGE · 3 INDEPENDENT LAYERS → ONE CONTRIBUTOR</text>
            </svg>
            <div className="conv-legend">
              <span><i style={{ background: "#ff5d6c" }} />finding from a detector</span>
              <span><i style={{ background: "#4edea3" }} />counter-evidence: a check that ran and passed</span>
              <span><i style={{ border: "1px dashed #ff5d6c" }} />convergence back to the contributor</span>
            </div>
          </div>
          <div className={`verdict-pop ${step >= 8 ? "vis" : ""}`}>
            <b>QUARANTINE RECOMMENDED</b>
            <span style={{ color: "var(--tx-2)", fontSize: 14 }}>Dataset, model and inference evidence converge on C-07 — and the genuine digest is shown, not hidden.</span>
          </div>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== BALANCE */
function Balance() {
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.3 });
  return (
    <section className="sec">
      <div className="wrap">
        <Reveal><span className="eyebrow">Chapter 05 · Epistemic honesty</span></Reveal>
        <h2 className="sec-title"><SplitWords text="It says what it knows, what argues against it, and what it never tested." highlight={["never", "tested."]} /></h2>
        <div className="bal">
          <Reveal><div className="pnl col"><h3><span style={{ color: "var(--red)" }}>▲</span> Evidence</h3><ul>
            <li>Signature invalid · I-883<span>CRITICAL</span></li><li>Nonce replay · I-884<span>CRITICAL</span></li><li>Trigger susceptibility · M-04<span>HIGH</span></li><li>Near-duplicate flood · D-14<span>HIGH</span></li></ul></div></Reveal>
          <Reveal delay={120}><div className="pnl col"><h3><span style={{ color: "var(--mint)" }}>✓</span> Counter-evidence</h3><ul>
            <li>Weight digest matches · M-04<span>PASSED</span></li><li>Class balance · D-14<span>PASSED</span></li><li>Signature valid · I-001<span>PASSED</span></li><li>Annotation validity · D-14<span>PASSED</span></li></ul></div></Reveal>
          <Reveal delay={240}><div className="pnl col"><h3><span style={{ color: "var(--tx-3)" }}>○</span> Declared limits</h3><ul>
            <li>White-box trigger reconstruction<span>OUT OF SCOPE</span></li><li>SAR / thermal modalities<span>OUT OF SCOPE</span></li><li>Physical adversarial patches<span>OUT OF SCOPE</span></li><li>Adaptive attackers<span>OUT OF SCOPE</span></li></ul></div></Reveal>
        </div>
        <div ref={ref}>
          <Reveal><div className="pnl meter2">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 10 }}>
              <div><span className="eyebrow">Coverage · demo case</span><div style={{ color: "var(--tx-2)", marginTop: 6 }}>12 of 12 applicable checks ran. A check that did not run is <b style={{ color: "#fff" }}>NOT TESTED</b> — never a pass.</div></div>
              <div style={{ fontFamily: "InterDisplay", fontSize: 48, color: "#fff", fontWeight: 700 }}><CountUp to={100} suffix="%" /></div>
            </div>
            <div className="bar"><i style={{ width: inView ? "100%" : "0%" }} /></div>
          </div></Reveal>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== PASSPORT */
function Passport() {
  return (
    <section className="sec">
      <div className="wrap pass-wrap">
        <div>
          <Reveal><span className="eyebrow">Chapter 06 · Portable attestation</span></Reveal>
          <h2 className="sec-title"><SplitWords text="Every asset carries a signed assurance passport." highlight={["signed"]} /></h2>
          <Reveal delay={150}><p className="sec-lead">Identity, lineage, per-layer integrity, evidence, counter-evidence, coverage and the human decision — in one document whose digest is signed by the node key, so an exported copy can be checked later.</p></Reveal>
        </div>
        <Reveal delay={200}>
          <Tilt className="pnl glow pass hud-corners">
            <div className="top">
              <div><span className="tag-hud">Passport · M-04</span><h3 style={{ fontSize: 22, marginTop: 10 }}>Subcontracted detector M-04</h3></div>
              <div className="seal"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#00e5ff" strokeWidth="1.5"><path d="M12 3 4 6v6c0 4.6 3.4 8.6 8 9.7 4.6-1.1 8-5.1 8-9.7V6z" /><path d="m8.5 12 2.5 2.5 4.5-5" /></svg></div>
            </div>
            <div className="grid2">
              {[["Format", "ONNX · YOLOv8s"], ["Access", "BLACK_BOX"], ["Contributor", "C-07 (synthetic)"], ["Trained from", "D-14 v1.0.0"]].map(([k, v]) => <div className="f" key={k}><span>{k}</span><b>{v}</b></div>)}
            </div>
            <div className="lay">
              <div style={{ ["--c" as any]: "var(--red)" }}>DATASET<b>FINDING</b></div>
              <div style={{ ["--c" as any]: "var(--red)" }}>MODEL<b>FINDING</b></div>
              <div style={{ ["--c" as any]: "var(--mint)" }}>DIGEST<b>VERIFIED</b></div>
            </div>
            <div className="dig">PASSPORT DIGEST · SHA-256 · SIGNED ED25519<br /><span style={{ color: "#cfe7ff" }}>9fef1e90b8a238397612a5412eb484ec3d5ca8c8045dff9b318584016a2a3003</span></div>
          </Tilt>
        </Reveal>
      </div>
    </section>
  );
}

/* =============================================================== DECISION */
function Decision() {
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.45 });
  return (
    <section id="decision" className="sec">
      <div className="wrap">
        <Reveal><span className="eyebrow">Chapter 07 · Human governance</span></Reveal>
        <h2 className="sec-title"><SplitWords text="The machine investigates. An authorised human decides." highlight={["authorised", "human", "decides."]} /></h2>
        <div className="decide" ref={ref}>
          <Reveal>
            <div className="screen hud-corners" style={{ height: "100%" }}>
              <video src="/media/trust_question_visual.mp4" poster="/media/trust_question_visual.jpg" autoPlay muted loop playsInline />
              <div className="ov" />
              <div className="hud"><span className="tag-hud">Concept visualisation</span></div>
            </div>
          </Reveal>
          <Reveal delay={150}>
            <div className="pnl glow gate hud-corners">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><b style={{ color: "#fff" }}>Disposition gate</b><span className="tag-hud">case C-07 submission</span></div>
              <div className="kv"><span>Machine recommendation</span><b style={{ color: "var(--red)" }}>QUARANTINE</b></div>
              <div className="kv"><span>Security analyst</span><b>recommended QUARANTINE</b></div>
              <div className="kv"><span>Reviewer / supervisor</span><b>decides — with a written rationale</b></div>
              <div className="btns"><div>ACCEPT</div><div>REVIEW</div><div className={inView ? "sel" : ""}>QUARANTINE</div></div>
              <div className={`stamp ${inView ? "vis" : ""}`} style={{ transitionDelay: "700ms" }}>✓ SIGNED · HASH-LINKED</div>
              <ul style={{ margin: 0, paddingLeft: 18, color: "var(--tx-2)", fontSize: 13.5 }}>
                <li>Analysts recommend; only a reviewer decides — enforced by the server.</li>
                <li>Whoever started the evaluation cannot sign it off.</li>
                <li>Administrators manage users and cannot decide anything.</li>
                <li>A later decision supersedes — it never overwrites.</li>
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== LEDGER (real SHA-256 in the browser) */
const EVENTS = ["CASE_CREATED · demo_bootstrap", "DATASET_SCANNED · D-14", "MODEL_SCANNED · M-04", "INFERENCE_VERIFIED · I-883", "DISPOSITION_RECOMMENDED · analyst", "DISPOSITION_QUARANTINE · reviewer"];
async function sha256(s: string) {
  if (!crypto?.subtle) return hexOf(s.length * 131 + s.charCodeAt(0));
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
}
function Ledger() {
  const [events, setEvents] = useState(EVENTS);
  const [stored, setStored] = useState<string[]>([]);
  const [live, setLive] = useState<string[]>([]);
  const compute = async (evs: string[]) => {
    const out: string[] = []; let prev = "0".repeat(64);
    for (const e of evs) { prev = await sha256(prev + e); out.push(prev); }
    return out;
  };
  useEffect(() => { compute(EVENTS).then(h => { setStored(h); setLive(h); }); }, []);
  useEffect(() => { compute(events).then(setLive); }, [events]);
  const firstBad = useMemo(() => live.findIndex((h, i) => stored[i] && h !== stored[i]), [live, stored]);
  const tamper = () => setEvents(e => e.map((x, i) => i === 2 ? "MODEL_SCANNED · M-04 (finding removed)" : x));
  return (
    <section id="ledger" className="sec">
      <div className="wrap">
        <Reveal><span className="eyebrow">Chapter 08 · Tamper-evident history</span></Reveal>
        <h2 className="sec-title"><SplitWords text="Change one event. Watch the history refuse to lie." highlight={["refuse", "to", "lie."]} /></h2>
        <Reveal delay={150}><p className="sec-lead">Each event's hash includes the previous hash. This demo computes real SHA-256 in your browser: edit event 3 and every later link breaks — exactly what the auditor's “verify all chains” detects on the server.</p></Reveal>
        <div className="chain2">
          {events.map((e, i) => {
            const broken = firstBad >= 0 && i >= firstBad;
            return (
              <Reveal key={i} delay={i * 80}>
                <div className={`blk ${broken ? (i === firstBad ? "edited broken" : "broken") : ""}`}>
                  <div className="t">#{i + 1}</div>
                  <div className="a">{e}</div>
                  <div className="h">H = <b>{(live[i] || "").slice(0, 10)}…</b></div>
                </div>
              </Reveal>
            );
          })}
        </div>
        <div className="ledger-ctl">
          <button className="lbtn sm" onClick={tamper}>Tamper with event #3</button>
          <button className="lbtn sm" onClick={() => setEvents(EVENTS)}>Restore</button>
          <span className={`res ${firstBad >= 0 ? "bad" : "ok"}`}>{firstBad >= 0 ? `CHAIN BROKEN at #${firstBad + 1} → ${events.length - firstBad} events no longer verify` : "CHAIN VALID · all events verify"}</span>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== ARCHITECTURE */
function Architecture() {
  const layers: [string, string, boolean?][] = [
    ["Trust boundary", "Untrusted files: type, size, traversal and decompression checks; SHA-256 on arrival"],
    ["Canonical assets", "COCO / YOLO → canonical records · registered model digests · signer keys"],
    ["Detectors D1–D9", "Pluggable, one evidence contract: replace a detector, the fabric still works"],
    ["Evidence fabric", "Cross-lifecycle graph · counter-evidence · coverage · limitations"],
    ["Assurance case", "Versioned policy turns evidence into a recommendation"],
    ["Human decision", "Recommend → decide, signed and append-only", true],
    ["Ledgers", "Case, decision and platform hash chains, independently verifiable"],
  ];
  return (
    <section id="architecture" className="sec">
      <div className="wrap">
        <Reveal><span className="eyebrow">Chapter 09 · Deployment</span></Reveal>
        <h2 className="sec-title"><SplitWords text="One host. No cloud required. No CDN. No external API by default." highlight={["No", "required.", "default."]} /></h2>
        <div className="arch">
          <div className="stack">
            {layers.map(([a, b, h], i) => <Reveal key={a} delay={i * 80} y={18}><div className={`layer2 ${h ? "human" : ""}`}><b>{a}</b><span>{b}</span></div></Reveal>)}
          </div>
          <Reveal delay={300}>
            <div className="pnl offline hud-corners">
              <div className="x">✕</div>
              <h3 style={{ marginTop: 10 }}>Internet not required</h3>
              <p style={{ color: "var(--tx-2)", fontSize: 14, marginTop: 8 }}>The console, fonts and videos are served by the same process. A test fails the build if the demo pipeline opens any outbound connection.</p>
              <div className="mono" style={{ fontSize: 11, color: "var(--tx-3)", marginTop: 14, textAlign: "left" }}>
                ✓ SQLite vault (PostgreSQL optional)<br />✓ PBKDF2 · JWT · RBAC<br />✓ Ed25519 node key<br />✓ CSP: default-src 'self'
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

/* =============================================================== ROLES */
function Roles() {
  const roles: [string, string, string, string][] = [
    ["ML Analyst", "What assets need my attention?", "upload", "ml.analyst"],
    ["Security Analyst", "Where is the threat, and how is it connected?", "search", "sec.analyst"],
    ["Reviewer", "Which decisions need my authorisation?", "gavel", "reviewer"],
    ["Auditor", "Can I prove the history is intact?", "check", "auditor"],
    ["Administrator", "Is the platform securely governed?", "users", "admin"],
  ];
  return (
    <section className="sec">
      <div className="wrap">
        <Reveal><span className="eyebrow">Chapter 10 · Role-aware consoles</span></Reveal>
        <h2 className="sec-title"><SplitWords text="Five roles. Five consoles. One shared truth." highlight={["One", "shared", "truth."]} /></h2>
        <div className="roles">
          {roles.map(([r, q, ic, u], i) => (
            <Reveal key={r} delay={i * 80}>
              <Link to={`/login?as=${u}`} className="role">
                <div className="ic"><Icon name={ic} size={18} /></div>
                <h3>{r}</h3>
                <div className="q">{q}</div>
                <div className="go">ENTER →</div>
              </Link>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =============================================================== FINAL */
function Final({ enter }: { enter: string }) {
  const caps = useApi<any>("/api/v1/system/coverage-statement");
  return (
    <>
      <section className="final">
        <div className="wrap">
          <Reveal><span className="eyebrow" style={{ justifyContent: "center" }}>DRISHTRA · Digital Reliability & Integrity Shield for Trusted AI</span></Reveal>
          <h2 style={{ marginTop: 24 }}><SplitWords text="Trust should be explainable." highlight={["explainable."]} /></h2>
          <Reveal delay={300}><p className="sec-lead" style={{ margin: "22px auto 0" }}>Not another detector. Not another dashboard. A cross-lifecycle assurance layer that shows why a result can be trusted — and proves who decided.</p></Reveal>
          <Reveal delay={450}><div style={{ display: "flex", gap: 14, justifyContent: "center", marginTop: 34, flexWrap: "wrap" }}>
            <Link to={enter} className="lbtn pri">Enter the system <Icon name="arrow" size={16} /></Link>
          </div></Reveal>
          <div className="scope">
            <Reveal><div className="pnl"><span className="eyebrow">In scope today</span><ul>
              <li>✓ COCO and YOLO datasets · pixel hashing when images are supplied</li>
              <li>✓ ONNX / PyTorch / TorchScript models · digest + black-box behaviour</li>
              <li>✓ Ed25519-signed inference records · replay and model-binding checks</li>
              <li>✓ {caps.data ? caps.data.checks.length : 11} published checks, each with a stated purpose</li>
            </ul></div></Reveal>
            <Reveal delay={120}><div className="pnl"><span className="eyebrow" style={{ color: "var(--amber)" }}>Declared out of scope</span><ul>
              {(caps.data?.out_of_scope || ["White-box trigger reconstruction", "SAR and thermal imagery", "Physical adversarial patches"]).slice(0, 5).map((o: string) => <li key={o}>○ {o}</li>)}
            </ul></div></Reveal>
          </div>
        </div>
      </section>
      <footer className="lp-foot"><div className="wrap" style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <span>DRISHTRA · PROTOTYPE FOR SIH26228 · SYNTHETIC DEMONSTRATION DATA</span><span>OFFLINE-FIRST · RBAC · HASH-CHAINED LEDGERS</span>
      </div></footer>
    </>
  );
}
