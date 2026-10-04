# DRISHTRA frontend (`web/`)

The DRISHTRA console: React 19 + TypeScript, bundled by esbuild into `web/dist`. The FastAPI backend serves `web/dist` directly, so you need Node.js only to change the UI, not to run the product. Nothing is fetched from a CDN: fonts, videos and code all ship with the app, so it works fully offline under a strict Content-Security-Policy (`default-src 'self'`).

> `web/` is the frontend that runs. The older `frontend/` prototype is not used by the product.

## Screens

| Route | Who | What |
|---|---|---|
| `#/` | public | **Home** (dark, cinematic): the problem, the 18-stage pipeline walk-through, convergence, the decision gate, a live in-browser hash-chain tamper demo, and role entry points |
| `#/login` | public | Light sign-in. `#/login?as=<user>` pre-fills a demo account when the server is in demo mode |
| `#/ml` · `#/security` · `#/review` · `#/audit` · `#/admin` | per role | Five role consoles, each answering its own question |
| `#/studio`, `#/studio/<case>` | ML & Security Analyst | **Pipeline Studio**: the real pipeline streamed live, stage by stage. Includes the **Attack Lab** on the sandbox case |
| `#/cases/<id>` | evidence readers | Assurance case: verdict, Why?, trace evidence (reverse lineage + evidence graph), coverage & limits, decision, pipeline run, audit ledger |
| `#/findings/<id>` | evidence readers | "Why was this flagged?": evidence, counter-evidence, limits |
| `#/passport/<asset>` | evidence readers | Signed assurance passport of a dataset, model or inference |
| `#/intake` | ML Analyst | Trust-boundary upload (COCO / YOLO / archives) |
| `#/admin/users`, `#/admin/events` | Administrator | User management, governance ledger |

Routes the signed-in role is not permitted to use show "Not part of your role". The server enforces the same permissions independently.

**Themes:** the home page is always dark. The login page and every console are light by default; the moon/sun button in the top bar toggles a console's theme, and the browser remembers the choice.

## Develop

```bash
cd web
npm install            # once
npm run watch          # rebuild on change; run the backend and open http://localhost:8000
npm run build          # production bundle → web/dist (commit it: the backend serves it)
npm run typecheck
```

`build.mjs` bundles `src/main.tsx`, copies `index.html` and the favicon, and copies `src/media` and `src/fonts` into `dist/`.

## Source map

```
src/
  main.tsx        routes + permission gating
  api.ts          same-origin API client (token in sessionStorage)
  auth.tsx        session, role → home, permission checks
  layout.tsx      role navigation, top bar (air-gap / remote-database badge, theme toggle)
  theme.ts        light/dark console theme
  ui.tsx          shared components (cards, pills, KPIs, icons)
  motion.tsx      dependency-free scroll/reveal/count-up/tilt effects for the home page
  styles.css      console design system (light tokens + dark overrides, Studio styles)
  landing.css     home page (dark) styles
  pages/
    Landing.tsx   home page
    Public.tsx    sign-in, first-login password change
    Homes.tsx     the five role consoles, intake, users, ledgers, decision history
    Studio.tsx    Pipeline Studio + Attack Lab
    CaseView.tsx  assurance case
    EvidenceGraph.tsx, Shared.tsx  graph, cases, findings, Why?, passport, coverage
  media/          home page videos (labelled "concept visualisation" in the UI) and posters
  fonts/          Inter (SIL Open Font License, see fonts/LICENSE-Inter.txt)
```

## Browser end-to-end check

From the repository root, with a fresh demo backend on port 8000:

```bash
npm i -D playwright && npx playwright install chromium   # once
node scripts/e2e_ui.mjs http://localhost:8000 --shots e2e_shots
```

It covers:
- the home page and the in-browser tamper demo
- sign-in
- a recommendation
- a Pipeline Studio clean run
- Attack Lab detection
- role gating
- the reviewer's decision
- the auditor's verification
- the administrator's limits
