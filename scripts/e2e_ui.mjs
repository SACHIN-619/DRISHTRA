// End-to-end UI check of the governed flow, in a real browser.
//
//   1. start a fresh demo node      (cd backend && uvicorn app.main:app --port 8000)
//   2. npm i -D playwright && npx playwright install chromium   (once)
//   3. node scripts/e2e_ui.mjs [http://localhost:8000] [--shots out_dir]
//
// Exits non-zero on the first failed expectation or any page error.
// Run it against a FRESH demo database: it signs a real recommendation and decision.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const args = process.argv.slice(2);
const BASE = (args.find(a => a.startsWith("http")) || "http://localhost:8000").replace(/\/$/, "") + "/";
const shotsIdx = args.indexOf("--shots");
const SHOTS = shotsIdx >= 0 ? args[shotsIdx + 1] : null;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const PASSWORD = "Drishtra@2026";
const CASE = "#/cases/CASE-2026-DRISHTRA-DEMO";

const browser = await chromium.launch();
const pageErrors = [];
let step = 0, failed = 0;

async function check(name, fn) {
  step++;
  try { await fn(); console.log(`  PASS ${String(step).padStart(2)}  ${name}`); }
  catch (e) { failed++; console.log(`  FAIL ${String(step).padStart(2)}  ${name}\n         ${String(e.message).split("\n")[0]}`); }
}
function expect(cond, msg) { if (!cond) throw new Error(msg); }
async function shot(page, name) { if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: false }); }

async function newPage() {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on("pageerror", e => pageErrors.push(e.message));
  return page;
}
async function signIn(user) {
  const page = await newPage();
  await page.goto(`${BASE}#/login?as=${user}`);
  await page.waitForSelector('input[autocomplete="username"]');
  await page.fill('input[autocomplete="username"]', user);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click("form button.lbtn.pri");
  await page.waitForSelector(".shell", { timeout: 10000 });
  return page;
}
async function openDecisionTab(page) {
  await page.goto(BASE + CASE);
  await page.waitForSelector(".tabs");
  await page.click('.tabs button:has-text("Decision")');
}

console.log(`DRISHTRA UI end-to-end  ->  ${BASE}\n`);

// ---------------------------------------------------------------- public
const pub = await newPage();
await check("landing renders the question and the 18-stage pipeline", async () => {
  await pub.goto(BASE);
  await pub.waitForSelector("text=Can we trust an AI result", { timeout: 10000 });
  await pub.waitForSelector("#pipeline");
  await shot(pub, "01_landing");
});
await check("in-browser ledger: tampering breaks the chain, restore repairs it", async () => {
  await pub.locator("text=Tamper with event #3").scrollIntoViewIfNeeded();
  await pub.click("text=Tamper with event #3");
  await pub.waitForSelector("text=CHAIN BROKEN", { timeout: 5000 });
  await shot(pub, "02_ledger_broken");
  await pub.click("button:has-text('Restore')");
  await pub.waitForSelector("text=CHAIN VALID", { timeout: 5000 });
});
await check("wrong password is refused", async () => {
  await pub.goto(`${BASE}#/login`);
  await pub.fill('input[autocomplete="username"]', "reviewer");
  await pub.fill('input[type="password"]', "wrong-password-1");
  await pub.click("form button.lbtn.pri");
  await pub.waitForSelector(".dlogin .err", { timeout: 5000 });
});

// ---------------------------------------------------------------- separation of duties
const sec = await signIn("sec.analyst");
await check("security analyst signs a QUARANTINE recommendation", async () => {
  await openDecisionTab(sec);
  await sec.click('button:has-text("QUARANTINE")');
  await sec.fill("textarea", "Signature failure on I-883, replay on I-884, backdoor behaviour on M-04 and poisoned D-14 all trace to C-07.");
  await sec.click('button:has-text("Sign & submit recommendation")');
  await sec.waitForSelector("text=RECOMMENDATION", { timeout: 8000 });
  await shot(sec, "03_recommendation");
});

await check("Pipeline Studio streams a clean run to ACCEPT", async () => {
  await sec.goto(`${BASE}#/studio/CASE-2026-ATTACK-LAB`);
  await sec.waitForSelector(".run-btn");
  await sec.uncheck(".pace input");
  await sec.click(".run-btn");
  await sec.waitForSelector(".verdict-live.pop", { timeout: 30000 });
  expect((await sec.textContent(".verdict-live .vl-big")).trim() === "ACCEPT", "clean sandbox was not ACCEPT");
  expect(await sec.locator(".srow.SUCCESS").count() === 18, "not all 18 stages succeeded");
  await shot(sec, "02b_studio_clean");
});
await check("Attack Lab: injected attacks are caught by their stages and flip the verdict", async () => {
  for (const t of ["Swap the model weights", "Alter an output after signing"]) {
    await sec.locator(".atk", { hasText: t }).locator("button:has-text('Inject')").click();
    await sec.waitForSelector(`.atk.on:has-text("${t}")`);
  }
  await sec.click(".run-btn");
  await sec.waitForSelector(".verdict-live.pop", { timeout: 30000 });
  expect((await sec.textContent(".verdict-live .vl-big")).trim() === "QUARANTINE", "verdict did not flip");
  expect(await sec.locator(".atk.hit").count() === 2, "not every injected attack was caught");
  await shot(sec, "02c_studio_attacked");
  await sec.click(".lab-h button:has-text('Reset')");
  await sec.waitForFunction(() => !document.querySelector(".atk.on"));
});

const ml = await signIn("ml.analyst");
await check("ML analyst cannot open the reviewer console", async () => {
  await ml.goto(`${BASE}#/review`);
  await ml.waitForSelector("text=Not part of your role", { timeout: 5000 });
});
await check("ML analyst can trace a finding to its 'Why?' explanation", async () => {
  await ml.goto(`${BASE}#/findings`);
  await ml.waitForSelector("table.t tbody tr");
  await ml.click("table.t tbody tr >> nth=0");
  await ml.waitForTimeout(800);
  expect((await ml.content()).toLowerCase().includes("why"), "Why page did not open");
});

const rev = await signIn("reviewer");
await check("reviewer signs the binding disposition", async () => {
  await openDecisionTab(rev);
  await rev.click('button:has-text("QUARANTINE")');
  await rev.fill("textarea", "Three independent evidence paths converge on C-07. Block downstream use and request a vendor response.");
  await rev.click('button:has-text("Sign & commit decision")');
  await rev.waitForSelector("text=DISPOSITION", { timeout: 8000 });
  await rev.click('button:has-text("Verify signatures")');
  await rev.waitForTimeout(800);
  await shot(rev, "04_decision");
});

const aud = await signIn("auditor");
await check("auditor verifies every chain with zero broken", async () => {
  await aud.goto(`${BASE}#/audit`);
  await aud.click('button:has-text("Verify all chains")');
  await aud.waitForFunction(() => {
    const k = [...document.querySelectorAll(".kpi")].find(e => e.querySelector(".label")?.textContent?.trim().toLowerCase() === "broken");
    return k && k.querySelector(".value")?.textContent?.trim() === "0";
  }, null, { timeout: 15000 });
  await shot(aud, "05_audit");
});

const adm = await signIn("admin");
await check("administrator sees diagnostics but has no Decision power", async () => {
  await adm.goto(`${BASE}#/admin`);
  await adm.waitForSelector("text=System diagnostics");
  await adm.goto(BASE + CASE);
  await adm.waitForTimeout(1000);
  const decide = await adm.locator('button:has-text("Sign & commit decision")').count();
  expect(decide === 0, "administrator was offered a decision button");
});

await check("no uncaught page errors", async () => {
  expect(pageErrors.length === 0, pageErrors.slice(0, 3).join(" | "));
});

await browser.close();
console.log(`\n${failed ? "FAILED" : "ALL PASSED"}  (${step - failed}/${step})`);
process.exit(failed ? 1 : 0);
