import { useEffect, useState } from "react";
import { api } from "../api";
import { ROLE_HOME, ROLE_LABEL, Role, useAuth } from "../auth";
import { Link, navigate } from "../router";
import { Icon, Logo, useApi } from "../ui";

/* ================================================================== Login */
const DEMO: [string, Role, string][] = [
  ["ml.analyst", "ML_ANALYST", "Intake · run assurance"],
  ["sec.analyst", "SECURITY_ANALYST", "Threats · recommend"],
  ["reviewer", "REVIEWER_SUPERVISOR", "Decide · sign"],
  ["auditor", "AUDITOR", "Verify every chain"],
  ["admin", "ADMINISTRATOR", "Users · platform"],
];
const DEMO_PASSWORD = "Drishtra@2026";

function queryParam(name: string): string | null {
  const q = window.location.hash.split("?")[1];
  return q ? new URLSearchParams(q).get(name) : null;
}

export function Login() {
  const { login } = useAuth();
  const health = useApi<any>("/health");
  const demo = !!health.data?.demo_mode;
  const [u, setU] = useState(() => queryParam("as") || "");
  const [p, setP] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // ?as=<demo user> pre-fills the demo password only when the server says demo mode is on.
  useEffect(() => { if (demo && u && DEMO.some(d => d[0] === u) && !p) setP(DEMO_PASSWORD); }, [demo]);
  const submit = async (e?: any) => {
    e?.preventDefault(); setErr(null); setBusy(true);
    try {
      const user = await login(u, p);
      navigate(user.must_change_password ? "/first-login" : ROLE_HOME[user.role]);
    } catch (er: any) { setErr(er.message); }
    setBusy(false);
  };
  return (
    <div className="dlogin">
        <div className="side">
          <Link to="/" className="dl-brand"><Logo /><b>DRISHTRA</b></Link>
          <div>
            <span className="eyebrow">Role-aware access</span>
            <h2 className="dl-title">Every role gets its own console, because every role answers a <span className="hl-grad">different question.</span></h2>
          </div>
          <div className="dl-window">
            <video src="/media/trust_question_visual.mp4" poster="/media/trust_question_visual.jpg" autoPlay muted loop playsInline />
            <div className="bar"><i /><i /><i /></div>
            <div className="cap">Concept visualisation · human-governed decision</div>
          </div>
          <ul className="dl-roles">
            {[["ML Analyst", "What assets need my attention?"], ["Security Analyst", "Where is the threat, and how is it connected?"], ["Reviewer", "Which decisions need my authorisation?"], ["Auditor", "Can I prove the history is intact?"], ["Administrator", "Is the platform securely governed?"]].map(([r, q]) => (
              <li key={r}><b>{r}</b><span>{q}</span></li>
            ))}
          </ul>
          <div className="dl-foot">Roles are assigned by an administrator and enforced by the server on every request. There is no self-registration, and no one can approve their own recommendation.</div>
        </div>
        <div className="formside">
          <form className="box" onSubmit={submit}>
            <Link to="/" className="dl-back">← Back to overview</Link>
            <h1 className="dl-h1">Sign in</h1>
            <p className="dl-lead">Use the account your administrator issued to you.</p>
            <label>Username<input value={u} onChange={e => setU(e.target.value)} autoComplete="username" autoFocus required /></label>
            <label>Password<input type="password" value={p} onChange={e => setP(e.target.value)} autoComplete="current-password" required /></label>
            {err && <div className="err">{err}</div>}
            <button className="lbtn pri" style={{ justifyContent: "center" }} disabled={busy}>{busy ? "Signing in…" : <>Sign in <Icon name="arrow" size={16} /></>}</button>
            {demo && (
              <div className="demo">
                <div className="dl-demo-h"><span className="dot" />Demonstration mode · synthetic data</div>
                <div className="dl-demo-s">Pick a role — password for all demo accounts is <code>{DEMO_PASSWORD}</code>. Open each role in its own tab to walk the full flow.</div>
                <div className="rolebtn">
                  {DEMO.map(([name, role, hint]) => (
                    <button type="button" key={name} className={u === name ? "sel" : ""} onClick={() => { setU(name); setP(DEMO_PASSWORD); }}>
                      {ROLE_LABEL[role]}<small>{hint}</small>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="dl-meta">{health.data ? <>Node online · v{health.data.version || "2"}{health.data.air_gapped_mode ? " · air-gapped" : ""}</> : "Connecting to node…"}</div>
          </form>
        </div>
    </div>
  );
}

/* ================================================================== First login */
export function FirstLogin() {
  const { user, setSession } = useAuth();
  const [cur, setCur] = useState("");
  const [n1, setN1] = useState("");
  const [n2, setN2] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const submit = async (e: any) => {
    e.preventDefault(); setErr(null);
    if (n1 !== n2) { setErr("The new passwords do not match."); return; }
    try {
      const r = await api<any>("/api/v1/auth/change-password", { body: { current_password: cur, new_password: n1 } });
      setSession(r.access_token, r.user); navigate(ROLE_HOME[r.user.role as Role]);
    } catch (er: any) { setErr(er.message); }
  };
  return (
    <div className="dlogin" style={{ gridTemplateColumns: "1fr" }}><div className="formside">
      <form className="box" onSubmit={submit}>
        <h1 className="dl-h1">Set your password</h1>
        <p className="dl-demo-s">{user ? `Welcome, ${user.full_name}. ` : ""}Your account was created with a temporary password. Choose a new one to continue (at least 10 characters, mixing three of: lowercase, uppercase, digits, symbols).</p>
        <label>Temporary password<input type="password" value={cur} onChange={e => setCur(e.target.value)} required /></label>
        <label>New password<input type="password" value={n1} onChange={e => setN1(e.target.value)} required minLength={10} /></label>
        <label>Repeat new password<input type="password" value={n2} onChange={e => setN2(e.target.value)} required /></label>
        {err && <div className="err">{err}</div>}
        <button className="lbtn pri" style={{ justifyContent: "center" }}>Save and continue</button>
      </form>
    </div></div>
  );
}
