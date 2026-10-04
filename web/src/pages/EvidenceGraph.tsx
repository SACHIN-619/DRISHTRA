import { navigate } from "../router";
import { Loading, useApi } from "../ui";

const COLS = ["Contributor", "Dataset", "Model", "Runtime", "Inference"];
const W = 168, H = 64, GX = 62, GY = 22, PAD = 16;

/* Layered evidence graph. Lifecycle nodes are laid out left-to-right; each node
   carries counts of the findings, passed checks and declared limitations attached
   to it in the stored graph. Edge labels are the recorded relationship names. */
export function EvidenceGraph({ caseId }: { caseId: string }) {
  const g = useApi<any>(`/api/v1/graph/${caseId}`);
  if (g.loading || !g.data) return <Loading what="Building graph" />;
  const nodes: any[] = g.data.nodes;
  const edges: any[] = g.data.edges;
  const life = nodes.filter(n => COLS.includes(n.type));
  const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
  const attach: Record<string, { f: any[]; ok: number; lim: number }> = {};
  for (const e of edges) {
    const t = byId[e.target];
    if (!t) continue;
    const a = (attach[e.source] ||= { f: [], ok: 0, lim: 0 });
    if (t.type === "Finding") a.f.push(t);
    else if (t.type === "CounterEvidence") a.ok++;
    else if (t.type === "Limitation") a.lim++;
  }
  const pos: Record<string, { x: number; y: number }> = {};
  const colCount = COLS.map(() => 0);
  for (const n of life) {
    const c = COLS.indexOf(n.type);
    pos[n.id] = { x: PAD + c * (W + GX), y: PAD + colCount[c] * (H + GY) };
    colCount[c]++;
  }
  const width = PAD * 2 + COLS.length * W + (COLS.length - 1) * GX;
  const height = PAD * 2 + Math.max(...colCount, 1) * (H + GY) + 10;
  const lifeEdges = edges.filter(e => pos[e.source] && pos[e.target]);
  const sevRank = (f: any[]) => f.some(x => x.status === "CRITICAL") ? "crit" : f.some(x => ["HIGH", "MEDIUM"].includes(x.status)) ? "high" : f.length ? "low" : "";

  return (
    <div style={{ overflowX: "auto" }}>
      <svg className="egraph" viewBox={`0 0 ${width} ${height + 24}`} width="100%" style={{ minWidth: 760, maxWidth: width }} role="img" aria-label="Evidence graph">
        {COLS.map((c, i) => (
          <text key={c} x={PAD + i * (W + GX)} y={height + 16} fontSize="11" fill="#6b7587" style={{ textTransform: "uppercase", letterSpacing: ".1em" }}>{c}</text>
        ))}
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 10 5 0 10z" fill="#9aa4b2" />
          </marker>
        </defs>
        {lifeEdges.map(e => {
          const a = pos[e.source], b = pos[e.target];
          const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2;
          const back = x2 <= x1;
          const d = back
            ? `M${a.x + W / 2} ${a.y + H} C ${a.x + W / 2} ${a.y + H + 30}, ${b.x + W / 2} ${b.y - 30}, ${b.x + W / 2} ${b.y}`
            : `M${x1} ${y1} C ${x1 + GX / 2} ${y1}, ${x2 - GX / 2} ${y2}, ${x2} ${y2}`;
          return (
            <g key={e.id}>
              <path d={d} fill="none" stroke={e.epistemic_status === "DECLARED" ? "#b7c0cc" : "#9aa4b2"} strokeDasharray={e.epistemic_status === "DECLARED" ? "4 3" : undefined} strokeWidth={1.4} markerEnd="url(#arr)" />
              {!back && <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 5} fontSize="9.5" fill="#6b7587" textAnchor="middle">{e.relationship.replace(/_/g, " ")}</text>}
            </g>
          );
        })}
        {life.map(n => {
          const p = pos[n.id];
          const at = attach[n.id] || { f: [], ok: 0, lim: 0 };
          const sr = sevRank(at.f);
          const stroke = sr === "crit" || sr === "high" ? "#e2786d" : n.type === "Contributor" && n.status === "FLAGGED" ? "#e2786d" : at.ok ? "#8fd1ae" : "#cfd5dd";
          const fill = sr === "crit" || sr === "high" ? "#fff6f5" : "#fff";
          const clickable = ["Dataset", "Model", "Inference"].includes(n.type);
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`} style={{ cursor: clickable ? "pointer" : "default" }}
              onClick={() => clickable && navigate(`/passport/${n.id.split(":")[1]}`)}>
              <rect width={W} height={H} rx={9} fill={fill} stroke={stroke} strokeWidth={1.6} />
              <text x={10} y={18} fontSize="11.5" fontWeight={700} fontFamily="ui-monospace,Consolas,monospace" fill="#0e1726">{n.id.split(":")[1]}</text>
              <text x={10} y={34} fontSize="10.5" fill="#3c4657">{(n.label || "").length > 25 ? (n.label || "").slice(0, 24) + "…" : n.label}</text>
              <g transform="translate(10,53)" fontSize="10" fontWeight={600}>
                {at.f.length > 0 && <text fill="#b42318">● {at.f.length} finding{at.f.length > 1 ? "s" : ""}</text>}
                {at.ok > 0 && <text x={at.f.length ? 74 : 0} fill="#157a4a">✓ {at.ok}</text>}
                {at.lim > 0 && <text x={(at.f.length ? 74 : 0) + (at.ok ? 30 : 0)} fill="#6b7587">○ {at.lim}</text>}
              </g>
            </g>
          );
        })}
      </svg>
      <div className="tiny muted mt-s">● findings attached · ✓ checks that ran and passed · ○ declared limitations · dashed edges are declared (not observed) relationships · click a dataset, model or inference to open its passport.</div>
    </div>
  );
}
