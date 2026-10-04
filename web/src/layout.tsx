import { useAuth, ROLE_LABEL, Role } from "./auth";
import { Icon, Logo, useApi } from "./ui";
import { useTheme } from "./theme";

type NavItem = [string, string, string]; // path, label, icon
export const NAV: Record<Role, { title: string; items: NavItem[] }[]> = {
  ML_ANALYST: [
    { title: "ML Operations", items: [["/ml", "Overview", "home"], ["/studio", "Pipeline Studio", "bolt"], ["/intake", "Ingest assets", "upload"], ["/cases", "Cases & runs", "flow"]] },
    { title: "Assets", items: [["/assets", "Asset registry", "database"], ["/findings", "Findings", "alert"]] },
    { title: "Reference", items: [["/coverage", "Coverage statement", "layers"]] },
  ],
  SECURITY_ANALYST: [
    { title: "Security Operations", items: [["/security", "Overview", "home"], ["/studio", "Pipeline Studio", "bolt"], ["/cases", "Investigations", "search"], ["/findings", "Findings", "alert"]] },
    { title: "Correlation", items: [["/contributors", "Contributor risk", "graph"], ["/assets", "Assets", "database"]] },
    { title: "Platform", items: [["/security/events", "Platform security", "lock"], ["/coverage", "Coverage statement", "layers"]] },
  ],
  REVIEWER_SUPERVISOR: [
    { title: "Assurance Review", items: [["/review", "Review center", "gavel"], ["/review/history", "Decision history", "ledger"]] },
    { title: "Evidence", items: [["/cases", "All cases", "flow"], ["/findings", "Findings", "alert"], ["/coverage", "Coverage statement", "layers"]] },
  ],
  AUDITOR: [
    { title: "Audit Assurance", items: [["/audit", "Audit center", "check"], ["/audit/platform", "Platform ledger", "ledger"], ["/review/history", "Decision history", "gavel"]] },
    { title: "Read-only", items: [["/cases", "Cases", "flow"], ["/findings", "Findings", "alert"], ["/coverage", "Coverage statement", "layers"]] },
  ],
  ADMINISTRATOR: [
    { title: "Administration", items: [["/admin", "System health", "pulse"], ["/admin/users", "Users & roles", "users"], ["/admin/events", "Ledger & security events", "lock"]] },
    { title: "Platform", items: [["/cases", "Case registry", "flow"], ["/coverage", "Coverage statement", "layers"]] },
  ],
};

export function Shell({ path, children }: { path: string; children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const health = useApi<any>("/health");
  const [theme, toggleTheme] = useTheme();
  if (!user) return null;
  const groups = NAV[user.role];
  const isActive = (p: string) => path === p || (p !== "/" && path.startsWith(p + "/") && !groups.some(g => g.items.some(([q]) => q !== p && path.startsWith(q) && q.length > p.length)));
  const initials = user.full_name.split(" ").map(s => s[0]).slice(0, 2).join("");
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><Logo /><div><b>DRISHTRA</b><small>AI assurance fabric</small></div></div>
        {groups.map(g => (
          <div key={g.title}>
            <div className="nav-title">{g.title}</div>
            <nav className="nav">
              {g.items.map(([p, l, i]) => (
                <a key={p} href={`#${p}`} className={isActive(p) ? "active" : ""}><Icon name={i} />{l}</a>
              ))}
            </nav>
          </div>
        ))}
        <div className="sidebar-foot">
          <div>{user.capabilities?.mission}</div>
          <div className="mt-s" style={{ color: "#6f8799" }}>Signed in as <b style={{ color: "#c9d6e0" }}>{user.username}</b></div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <span className={`badge-airgap ${health.data?.database_location === "remote" || health.data?.air_gapped_mode === false ? "net" : ""}`}><Icon name="lock" size={13} />{health.data?.database_location === "remote" ? "Remote database · not air-gapped" : health.data?.air_gapped_mode === false ? "Network enabled" : "Air-gapped mode"}</span>
          {health.data?.demo_mode && <span className="badge-demo" title="Synthetic demonstration data and accounts are enabled">Demo data</span>}
          <span className="muted small">Access scope: <b>{user.access_scope}</b> (prototype classification)</span>
          <div className="spacer" />
          <button className="theme-btn" onClick={toggleTheme} title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"} aria-label="Toggle colour theme">
            <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
          </button>
          <div className="userchip">
            <div style={{ textAlign: "right" }}><div className="strong small">{user.full_name}</div><div className="tiny muted">{ROLE_LABEL[user.role]}</div></div>
            <div className="avatar">{initials}</div>
            <button className="btn ghost sm" onClick={logout} title="Sign out"><Icon name="logout" /></button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
