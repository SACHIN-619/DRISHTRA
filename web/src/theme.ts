// Console colour theme. Light is the default operational look; dark is optional. The public home page is always dark.
import { useState } from "react";

export type Theme = "dark" | "light";
const KEY = "drishtra.theme";

export function storedTheme(): Theme {
  try { const v = localStorage.getItem(KEY); if (v === "light" || v === "dark") return v; } catch { /* storage unavailable */ }
  return "light";
}
export function applyTheme(t: Theme) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem(KEY, t); } catch { /* storage unavailable */ }
}
export function useTheme(): [Theme, () => void] {
  const [t, setT] = useState<Theme>(storedTheme);
  const toggle = () => { const n: Theme = t === "dark" ? "light" : "dark"; applyTheme(n); setT(n); };
  return [t, toggle];
}
