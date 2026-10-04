import { useEffect, useState } from "react";

// Hash router: works from any static host and from the FastAPI catch-all.
export function usePath(): string {
  const [path, setPath] = useState(() => window.location.hash.slice(1) || "/");
  useEffect(() => {
    const on = () => { setPath(window.location.hash.slice(1) || "/"); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return path;
}

export function navigate(to: string) { window.location.hash = to; }

export function match(pattern: string, path: string): Record<string, string> | null {
  const p = pattern.split("/").filter(Boolean);
  const a = path.split("?")[0].split("/").filter(Boolean);
  if (p.length !== a.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < p.length; i++) {
    if (p[i].startsWith(":")) params[p[i].slice(1)] = decodeURIComponent(a[i]);
    else if (p[i] !== a[i]) return null;
  }
  return params;
}

export function Link({ to, children, className }: { to: string; children: React.ReactNode; className?: string }) {
  return <a href={`#${to}`} className={className}>{children}</a>;
}
