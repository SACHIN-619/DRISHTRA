import { useEffect } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { applyTheme, storedTheme } from "./theme";
applyTheme(storedTheme());
import { AuthProvider, ROLE_HOME, useAuth } from "./auth";
import { Shell } from "./layout";
import { match, navigate, usePath } from "./router";
import { Loading } from "./ui";
import { CaseView } from "./pages/CaseView";
import { StudioPage } from "./pages/Studio";
import {
  AdminHome, AuditHome, ContributorsPage, DecisionHistoryPage, IntakePage, MLHome, PlatformLedgerPage,
  ReviewHome, SecurityHome, UsersPage,
} from "./pages/Homes";
import { FirstLogin, Login } from "./pages/Public";
import { Landing } from "./pages/Landing";
import { AssetsPage, CasesPage, CoverageStatementPage, FindingsPage, PassportPage, WhyPage } from "./pages/Shared";

type R = [string, (p: Record<string, string>) => JSX.Element, string?]; // pattern, render, required permission
const ROUTES: R[] = [
  ["/ml", () => <MLHome />, "pipeline:run"],
  ["/studio", () => <StudioPage />, "pipeline:run"],
  ["/studio/:id", p => <StudioPage caseId={p.id} />, "pipeline:run"],
  ["/intake", () => <IntakePage />, "dataset:ingest"],
  ["/security", () => <SecurityHome />, "disposition:recommend"],
  ["/security/events", () => <PlatformLedgerPage />, "security_events:read"],
  ["/contributors", () => <ContributorsPage />, "evidence:read"],
  ["/review", () => <ReviewHome />, "disposition:decide"],
  ["/review/history", () => <DecisionHistoryPage />, "evidence:read"],
  ["/audit", () => <AuditHome />, "audit:verify"],
  ["/audit/platform", () => <PlatformLedgerPage />, "audit:read"],
  ["/admin", () => <AdminHome />, "system:diagnostics"],
  ["/admin/users", () => <UsersPage />, "user:manage"],
  ["/admin/events", () => <PlatformLedgerPage admin />, "user:manage"],
  ["/cases", () => <CasesPage />, "asset:read"],
  ["/cases/:id", p => <CaseView caseId={p.id} />, "asset:read"],
  ["/findings", () => <FindingsPage />, "evidence:read"],
  ["/findings/:id", p => <WhyPage findingId={p.id} />, "evidence:read"],
  ["/passport/:id", p => <PassportPage assetId={p.id} />, "evidence:read"],
  ["/assets", () => <AssetsPage />, "asset:read"],
  ["/coverage", () => <CoverageStatementPage />],
];

function App() {
  const full = usePath();
  const [path, anchor] = full.split("#");
  const { user, ready, can } = useAuth();

  useEffect(() => {
    if (anchor) setTimeout(() => document.getElementById(anchor)?.scrollIntoView({ behavior: "smooth" }), 50);
  }, [anchor, path]);

  if (!ready) return <Loading what="Starting" />;
  if (path === "/" || path === "") return <Landing />;
  if (path.split("?")[0] === "/login") {
    if (user && !user.must_change_password) { navigate(ROLE_HOME[user.role]); return null; }
    return <Login />;
  }
  if (!user) { navigate("/login"); return null; }
  if (user.must_change_password || path === "/first-login") {
    if (!user.must_change_password) { navigate(ROLE_HOME[user.role]); return null; }
    return <FirstLogin />;
  }
  for (const [pattern, render, perm] of ROUTES) {
    const params = match(pattern, path);
    if (params) {
      return (
        <Shell path={path}>
          {perm && !can(perm)
            ? <div className="card"><div className="empty"><h2>Not part of your role</h2><p className="mt-s">This area requires <span className="tag">{perm}</span>. Your console has what your role needs.</p><a className="btn mt" href={`#${ROLE_HOME[user.role]}`}>Go to my console</a></div></div>
            : render(params)}
        </Shell>
      );
    }
  }
  return <Shell path={path}><div className="card"><div className="empty">Page not found. <a href={`#${ROLE_HOME[user.role]}`}>Back to your console</a></div></div></Shell>;
}

createRoot(document.getElementById("root")!).render(<AuthProvider><App /></AuthProvider>);
