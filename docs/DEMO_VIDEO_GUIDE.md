# DRISHTRA — 3-minute demo video guide

A ready-made cut recorded from the running app is in `demo_video/DRISHTRA_judge_demo_3min.mp4` (3:01, captions, visible cursor, typed sign-ins, soft synthesised score). Use it as-is, or record narration over it, or follow the shot list below to record your own.

The goal: in under three minutes a judge should believe three things.

1. **The pipeline is real.** Every stage consumes the previous stage's exact output, and you can see it happen.
2. **The verdict is explainable.** One click goes from "QUARANTINE" to the contributor, the evidence, the counter-evidence and the limits.
3. **The decision is governed.** A human signs it, the wrong roles cannot, and nobody can quietly rewrite history.

Everything shown is the running product on synthetic data. Say so once, early. Judges trust a team that labels its demo data.

---

## Before you record (10 minutes)

**Use a fresh local database for every take.** Your `.env` points at Neon. For the video, override it so the badge truthfully reads *Air-gapped mode*, and so every take starts clean:

```powershell
cd backend
Remove-Item -Recurse -Force demo_take, ..\demo_take.db -ErrorAction SilentlyContinue
$env:DATABASE_URL = "sqlite:///./demo_take.db"
$env:BASE_STORAGE_DIR = "./demo_take"
$env:DEMO_MODE = "true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On macOS or Linux, use `export VAR=value` instead of `$env:VAR = "value"`.

Then set up the screen:

| Item | Setting |
|---|---|
| Screen | 1920×1080, browser zoom **110 %**, full-screen (F11) or hide the bookmarks bar |
| Browser | Chrome, a fresh profile, notifications off, no extensions visible |
| Tabs | Pre-open five tabs: landing · `#/login?as=ml.analyst` · `?as=sec.analyst` · `?as=reviewer` · `?as=auditor` |
| Theme | The home page is always dark. Login and every console are light by default; the moon icon switches a console to dark. |
| Terminal | A second window with `python scripts/golden_demo.py` typed and ready (font 16 pt, dark) |
| Recorder | OBS: 1920×1080, 60 fps, CQP 18–20, mic noise suppression on |
| Mouse | Turn on cursor highlighting. Move slowly, and **stop moving while you speak about something**. |

**Rehearse twice without recording.** The second run is always 30 % faster.

---

## Shot list and narration

Target length **2:45**. The bracketed times are cumulative. Narration is written to be read at a calm pace (about 150 words per minute). Cut anything that runs long, and don't speed up your voice.

### 1 · The question  [0:00 – 0:18]

**Screen:** landing page hero. Let the headline animate in. Don't scroll for 3 seconds.

> "An AI model says *armoured vehicle, 94 % confident*. Every dashboard is green.
> But that model was trained on data from a subcontractor, built by a vendor, and run on an edge device.
> **Can we trust the result if we can't trust the pipeline that produced it?** That's what DRISHTRA answers."

### 2 · Why existing tools miss it  [0:18 – 0:36]

**Screen:** scroll slowly through *Chapter 01*. The four story steps change as you scroll: poisoned batch → backdoored model → tampered record.

> "Here the failure is spread across the lifecycle. The training batch was poisoned. The model's hash is genuine, but its behaviour has a backdoor. One output was altered after signing. Each tool sees one fragment. Nobody sees the chain."

### 3 · ★ WOW 1 — the core pipeline  [0:36 – 1:05]

**Screen:** keep scrolling into *Chapter 03 · The core pipeline*. Scroll at a steady speed so the big stage counter runs **01 → 18** and the digest panel shows "matches previous output ✓". Pause on stage 18 for one second.

> "DRISHTRA runs an 18-stage assurance pipeline. Ingest, verify the data, verify the model, verify every inference, correlate, assure.
> The key is **chaining**. Each stage records the digest of what it consumed, and it must equal the previous stage's output. A stage with nothing to work on says *SKIPPED*, never *SUCCESS*. Nothing is assumed to pass."

Then click **Enter system** and sign in as `sec.analyst` by typing the username and password (keep the cursor visible). On the Security home, click **Open Pipeline Studio**.

**Screen:** Pipeline Studio on the *Attack Lab sandbox*. Click **Run assurance pipeline** (leave *Presentation pace* on). The 18 stages light up one by one, the live progress bar fills, each stage shows its real compute time and output digest, and the run ends with **ACCEPT** and *"✓ every stage consumed the previous stage's output."*

> "And this is the live product, not an animation. Each stage is streamed from the server as it executes. Clean release: every applicable check ran and passed — accept."

### 3b · ★ WOW — Attack Lab: we attack it live  [1:05 – 1:35]

**Screen:** in the Attack Lab panel, click **Inject** on *Poison the training data*, *Plant a trigger backdoor* and *Alter an output after signing*. Click **Run assurance pipeline** again.

> "Now we attack it. Poisoned training data, a backdoored model whose hash still looks genuine, and a signed output altered after signing. DRISHTRA is not told what changed."

Stages 05, 08 and 11 turn red as they run, the findings feed fills, the lineage lights up, and the verdict lands on **QUARANTINE** with *"3 independent evidence paths … trace back to contributor C-04"* and *"3 of 3 injected attacks caught"*. Click stage 11 to show the signature check table. Then click **Reset**.

> "Each attack is caught by the stage that owns that check, and the three findings converge on one contributor. Reset restores the signed baseline, and every injection is recorded in the audit ledger."

### 4 · ★ WOW 2 — convergence and "Why?"  [1:05 – 1:40]

**Screen:** Security Analyst tab → *Investigations* → **Contributor C-07 model submission**. The red **QUARANTINE RECOMMENDED** banner fills the top. Hold for 2 seconds.

> "Now the poisoned submission. The verdict is **quarantine**, and it is not a black-box score."

Click **Trace evidence**. The reverse lineage runs from the inference through the runtime, model and dataset to contributor C-07. Hover on M-04.

> "Walk it backwards. The tampered inference ran on this runtime, used model M-04, trained on dataset D-14, all supplied by contributor C-07. **Three independent detectors, on three different layers, converge on one contributor.** That's the signal."

Click **Coverage & limits** and point at a *NOT TESTED* or *Out of scope* row.

> "It also tells you what argues *against* it — the checks that passed — and what it never tested. A check that didn't run is never counted as a pass."

### 5 · ★ WOW 3 — a governed, signed decision  [1:40 – 2:15]

**Screen:** still as the Security Analyst → **Decision** tab → choose QUARANTINE → type a one-line rationale → **Sign & submit recommendation**.

> "The analyst can only *recommend*."

Switch to the **Reviewer** tab → the same case → **Decision** → QUARANTINE → rationale → **Sign & commit decision** → **Verify signatures** (a green *chain valid* bar appears).

> "Only a reviewer can decide. The decision is Ed25519-signed and hash-linked to the one before it. Even the administrator cannot make or change it. Separation of duties is enforced by the server, not hidden in the UI."

*(Optional, 4 seconds)* Switch to the **Admin** tab → *System health* → zoom on **"What you cannot do"**.

### 6 · ★ WOW 4 — history that refuses to lie  [2:15 – 2:35]

**Screen:** Auditor tab → **Verify all chains** → the *Broken* tile reads **0**.

> "The auditor recomputes every hash chain independently. Zero broken."

Cut to the **terminal** → run `python scripts/golden_demo.py`. Let the PASS lines scroll, then freeze on:
`PASS tampered model digest flips the verdict` · `PASS edited decision is detected` · `ALL STEPS PASSED (19/19)`.

> "And we attack it ourselves. Swap one model digest and the clean case flips to quarantine. Edit a stored decision and verification breaks. Nineteen of nineteen steps pass on every build."

*(Alternative if you skip the terminal: on the landing page's Ledger chapter, click **Tamper with event #3** so the chain turns red, then **Restore**.)*

### 7 · Close  [2:35 – 2:45]

**Screen:** scroll to the landing finale — **"Trust should be explainable."** — with the in-scope and out-of-scope lists visible.

> "DRISHTRA. One host, no internet needed, five role consoles, and every claim traceable to evidence. Not another detector — the assurance layer that shows *why* a result can be trusted, and proves who decided."

---

## Wow moments — why these four

| # | Moment | What the judge concludes |
|---|---|---|
| 1 | Stage counter 01→18, then the **live replay** of a real run | "The pipeline is real, ordered and chained — not slides." |
| 2 | **Reverse lineage** to C-07, plus counter-evidence and limits | "It explains itself, and it is honest about gaps." |
| 3 | Analyst recommends, **only the reviewer can sign** | "Human governance is enforced, not decorative." |
| 4 | **Tamper → detected**, 19/19 PASS | "They tried to break it, and it held." |

If you must cut to two minutes, drop shot 2 and the optional admin cutaway. **Never cut the live replay or the tamper proof.**

---

## Editing tips

- **Zoom on detail.** Add a 1.3× zoom on the digest panel (shot 3), the lineage chips (shot 4) and the "Broken 0" tile (shot 6). Judges watch on laptops.
- **Captions.** Burn in short lower-thirds at each chapter, for example "18-stage chained pipeline", "Evidence convergence", "Signed human decision" and "Tamper-evident ledger". Many judges watch muted.
- **Music.** Low ambient electronic at −28 LUFS under the voice. Fade it out under the closing line.
- **Pacing.** Cut every silence longer than 0.6 s. Keep the hero headline and the QUARANTINE banner on screen for a full 2 seconds each.
- **Export.** H.264, 1080p, 12–16 Mbps, AAC 192 kbps. Check that the file is under the submission size limit.

## Honesty checklist (judges notice)

- Say **"synthetic demonstration data"** once. The console already shows a *Demo data* badge.
- Don't claim detection accuracy figures. Show *what is checked* and *what is out of scope*.
- If you record against Neon instead of local SQLite, the badge will read *Remote database · not air-gapped*. Either record locally (recommended) or don't call that take "air-gapped".
- The landing videos are labelled *Concept visualisation*. Everything else is the running product.

## Reset between takes

Stop the server, then delete `demo_take.db` (it lands in the project root) and `backend/demo_take/`. The `Remove-Item` line above does both. Start the server again with the same commands. Each take gets fresh cases, no prior decisions and a clean ledger.
