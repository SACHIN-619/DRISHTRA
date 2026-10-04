import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

/* ------------------------------------------------------------------ data hook */
export function useApi<T = any>(path: string | null, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true); setError(null);
    try { setData(await api<T>(path)); } catch (e: any) { setError(e.message || String(e)); }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => { load(); }, [load]);
  return { data, error, loading, reload: load, setData };
}

/* ------------------------------------------------------------------ icons */
const P: Record<string, string> = {
  home: "M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  shield: "M12 3 4 6v6c0 4.6 3.4 8.6 8 9.7 4.6-1.1 8-5.1 8-9.7V6z",
  database: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zm0 0v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  cpu: "M7 7h10v10H7zM9 1v4M15 1v4M9 19v4M15 19v4M1 9h4M1 15h4M19 9h4M19 15h4",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7z",
  flow: "M4 6h6v4H4zM14 14h6v4h-6zM7 10v4h10",
  search: "M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14zm10 17-4.3-4.3",
  graph: "M5 6a2 2 0 1 0 0 .1M19 6a2 2 0 1 0 0 .1M12 18a2 2 0 1 0 0 .1M6.5 7.5l4.5 9M17.5 7.5l-4.5 9M7 6h10",
  gavel: "m14 4 6 6M11 7l6 6M4 20l7-7M9 9l6-6 6 6-6 6z",
  ledger: "M6 3h12v18H6zM9 7h6M9 11h6M9 15h4",
  check: "M5 12.5 10 17l9-10",
  users: "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-3.9 3.1-7 7-7s7 3.1 7 7M17 3.5a4 4 0 0 1 0 7.5M22 21c0-3.2-2-5.9-5-6.7",
  alert: "M12 3 2 20h20zM12 10v4M12 17v.1",
  pulse: "M3 12h4l3-7 4 14 3-7h4",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16",
  doc: "M7 3h7l5 5v13H7zM14 3v5h5",
  lock: "M6 11h12v10H6zM8 11V8a4 4 0 0 1 8 0v3",
  logout: "M15 4h4v16h-4M10 16l-4-4 4-4M6 12h10",
  layers: "m12 3 9 5-9 5-9-5zM3 13l9 5 9-5",
  passport: "M6 3h12v18H6zM12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM9 17h6",
  play: "M7 4v16l13-8z",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6",
  eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  x: "M6 6l12 12M18 6 6 18",
  sun: "M12 4V2m0 20v-2m8-8h2M2 12h2m13.66-5.66 1.41-1.41M4.93 19.07l1.41-1.41m0-11.32L4.93 4.93m14.14 14.14-1.41-1.41M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  arrow: "M5 12h14M13 6l6 6-6 6",
};
export function Icon({ name, size = 16 }: { name: keyof typeof P | string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={P[name] || P.doc} /></svg>
  );
}
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 2 4 7v8c0 7.2 5.1 13.4 12 15 6.9-1.6 12-7.8 12-15V7z" fill="#135f8c" />
      <circle cx="16" cy="15" r="5.5" fill="none" stroke="#7dd3c0" strokeWidth="2.2" />
      <circle cx="16" cy="15" r="1.8" fill="#7dd3c0" />
    </svg>
  );
}

/* ------------------------------------------------------------------ status vocabulary */
type Tone = "ok" | "warn" | "bad" | "info" | "muted";
const TONE: Record<string, [Tone, string]> = {
  VERIFIED: ["ok", "Verified"], PASS: ["ok", "Passed"], ACCEPT: ["ok", "Accept"], ACCEPTED: ["ok", "Accepted"],
  VALID: ["ok", "Valid"], ACTIVE: ["ok", "Active"], SUCCESS: ["ok", "Success"], COMPLETED: ["ok", "Completed"],
  REVIEW: ["warn", "Review"], REVIEW_REQUIRED: ["warn", "Review required"], UNDER_REVIEW: ["warn", "Under review"],
  PARTIAL: ["warn", "Partial"], INCOMPLETE: ["warn", "Incomplete"], AWAITING_DECISION: ["info", "Awaiting decision"],
  QUARANTINE: ["bad", "Quarantine"], QUARANTINED: ["bad", "Quarantined"], QUARANTINE_RECOMMENDED: ["bad", "Quarantine recommended"],
  FINDING: ["bad", "Finding"], BROKEN: ["bad", "Broken"], FAILED: ["bad", "Failed"], DISABLED: ["muted", "Disabled"],
  TAMPERED: ["bad", "Tampered"], INVALID_SIGNATURE: ["bad", "Invalid signature"], REPLAY_DETECTED: ["bad", "Replay detected"],
  INCONCLUSIVE: ["info", "Inconclusive"], NOT_TESTED: ["muted", "Not tested"], NOT_APPLICABLE: ["muted", "Not applicable"],
  SKIPPED: ["muted", "Skipped"], UNVERIFIED: ["muted", "Unverified"], NOT_ASSESSED: ["muted", "Not assessed"],
  DENIED: ["bad", "Denied"], FAILURE: ["bad", "Failure"], BOUND: ["info", "Bound"],
};
export function tone(s?: string | null): Tone { return (s && TONE[s]?.[0]) || "muted"; }
export function label(s?: string | null): string {
  if (!s) return "—";
  return TONE[s]?.[1] || s.replace(/_/g, " ").toLowerCase().replace(/^\w/, c => c.toUpperCase());
}
export function Pill({ s, text, dashed }: { s?: string | null; text?: string; dashed?: boolean }) {
  const t = tone(s);
  return <span className={`pill ${t} ${dashed || s === "NOT_TESTED" ? "dashed" : ""}`}>{text || label(s)}</span>;
}
export function Sev({ s }: { s: string }) { return <span className={`sev ${s}`}>{s}</span>; }
export function Dot({ s }: { s?: string | null }) { return <span className={`dot ${tone(s)}`} />; }
export const COV_GLYPH: Record<string, string> = {
  VERIFIED: "✓", PASS: "✓", FINDING: "!", PARTIAL: "◐", INCONCLUSIVE: "?", INCOMPLETE: "◐", NOT_TESTED: "", NOT_APPLICABLE: "–",
};

/* ------------------------------------------------------------------ formatters */
export function short(h?: string | null, n = 12) { return h ? (h.length > n ? h.slice(0, n) + "…" : h) : "—"; }
export function when(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
export function ago(iso?: string | null) {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}
export function human(t?: string | null) { return (t || "").replace(/_/g, " ").toLowerCase().replace(/^\w/, c => c.toUpperCase()); }

/* ------------------------------------------------------------------ building blocks */
export function Card({ title, hint, actions, children, flush, className }: {
  title?: React.ReactNode; hint?: React.ReactNode; actions?: React.ReactNode; children: React.ReactNode; flush?: boolean; className?: string;
}) {
  return (
    <section className={`card ${className || ""}`}>
      {(title || actions) && (
        <div className="card-h">
          <div><h2>{title}</h2>{hint && <div className="hint">{hint}</div>}</div>
          {actions && <div className="row">{actions}</div>}
        </div>
      )}
      <div className={`card-b ${flush ? "flush" : ""}`}>{children}</div>
    </section>
  );
}
export function Kpi({ label: l, value, foot, tone: t }: { label: string; value: React.ReactNode; foot?: string; tone?: Tone }) {
  return <div className={`card kpi ${t || ""}`}><div className="label">{l}</div><div className="value">{value}</div>{foot && <div className="foot">{foot}</div>}</div>;
}
export function PageHead({ eyebrow, title, sub, actions }: { eyebrow?: string; title: string; sub?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="page-head">
      <div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{sub && <div className="sub">{sub}</div>}</div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}
export const Loading = ({ what = "Loading" }: { what?: string }) => <div className="loading">{what}…</div>;
export const Empty = ({ children }: { children: React.ReactNode }) => <div className="empty">{children}</div>;
export const ErrorBox = ({ error }: { error: string | null }) => error ? <div className="alert bad">{error}</div> : null;

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} role="dialog" aria-label={title}>
        <div className="card-h"><h2>{title}</h2><button className="btn ghost sm" onClick={onClose} aria-label="Close"><Icon name="x" /></button></div>
        <div className="card-b">{children}</div>
      </div>
    </div>
  );
}

export function Meter({ pct }: { pct: number }) { return <div className="meter"><i style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} /></div>; }

export function Raw({ data, label: l = "Show raw JSON" }: { data: any; label?: string }) {
  return <details className="mt-s"><summary>{l}</summary><pre className="raw">{JSON.stringify(data, null, 2)}</pre></details>;
}
