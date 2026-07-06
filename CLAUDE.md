# Plainlode — Claude Code context

Read this file at the start of every Claude Code session. Update the Build State section at the end of every session (SOP Phase 4.5). The Project Brief below is the source of truth carried over from the Claude.ai project.

---

## Build State (update every session)

**Day 1, July 6.** Day-one spike complete (SOP Phase 3.3):

- Scrapingdog Google Trends TIMESERIES pull: PASS, live and verified (53 timeline points on a real e-commerce query).
- Rising/related queries via Scrapingdog: not available. The API exposes only TIMESERIES/GEO_MAP/GEO_MAP_0. Deriving "rising" from the TIMESERIES slope instead. This is the concept-lock fallback, now the core path, and it is in-scope core, not creep.
- Kaggle nicapotato reviews license: CC0-1.0, cleared for the fine-tune corpus (Phase 8 gate, original + MIT-compliant).
- Fireworks serverless call: parked. Waiting on the automatic $50 credit and a real model id from the launch-day (July 6) revealed list. The placeholder `llama-v3p1-8b-instruct` 404s, which is expected.

**Current step:** building the live-scan module (`backend/scan/`), build order step 1. The scan is standalone and terminal-testable before any FastAPI route is added. This reorders Phase 4.2 on purpose so the live pull is proven against the real API before an HTTP layer exists.

**Next:** ranker (slope-derived rising), then the scan orchestrator with the cheap-tier model-filter seam (Fireworks serverless, stubbed until the credit lands).

## Stack (SOP Phase 3.2, with the Phase 1.3 override)

- Backend: FastAPI (Python). Scan data layer is stdlib + `requests`, pandas where it earns it.
- Runtime model: Fireworks-on-AMD, NOT the Claude API. Cheap-tier scan model on Fireworks serverless; report-voice LoRA on a Fireworks dedicated deployment. Claude is the dev spine only (Claude Code). It is never a product runtime dependency.
- Frontend: React + Tailwind (later; Native.Builder prototype path is in the brief).
- Hosting: Railway, always-on, no cold start.
- Repo: public GitHub (eschaq/plainlode), MIT.

## Folder structure

```
backend/
  scan/
    models.py         # TrendPoint, TermSeries, Finding, ScanResult
    trends_client.py  # Scrapingdog TIMESERIES pull, batched <=5 queries/call
    ranker.py         # slope-derived rising (next)
    filter.py         # cheap-tier model-filter seam, Fireworks, stubbed (next)
    scan.py           # orchestrator: seeds in -> ranked ScanResult out (next)
  prompts/            # voice/format prompt templates (.txt), later
data/                 # seed terms, snapshot fallback
frontend/             # React, later
spike.py              # throwaway day-one verification, not product code
```

## Session rules for Claude Code

- The scan data layer takes no LLM calls. Model calls belong only in the filter seam and the report-voice layer, both Fireworks, both added later.
- Keep modules small and readable. `requests` + stdlib for the scan client, no extra abstractions.
- Prompt templates live in `backend/prompts/` as `.txt` files (Phase 4.4). Analysis temperature 0.2 to 0.3.
- Never hardcode keys. Read from the environment. `.env` is sourced before running (`set -a; source .env; set +a`), so no python-dotenv.
- End each session with a CHANGELOG.md entry: what changed, why, gotchas, what is next (Phase 4.5).

---

## Project Brief (source of truth)

This is the Plainlode Project, my entry for the AMD Developer Hackathon: ACT II (Track 3, Unicorn), July 6-11 2026. Plainlode is a market-intelligence engine that scans live market signal and returns a decision-first briefing in plain language for small e-commerce owners. Tagline: "The signal, mined plain."

I am Eban Schachter. Marketing Analytics Manager at Cox Automotive by day. I run DataWisdomSolutions (DWS) and build under DataWisdom Labs. Dev stack: Chromebook Plus + Crostini + Claude Code + VS Code. GitHub: eschaq. HBDI strongly D-quadrant, strategic and holistic, low sequential. I work from Lee's Summit, Missouri.

This build sits under my Hackathons protected stream. It is also the general multi-source engine that my Reddit scraper (Flywheel Stream 05) becomes at scale, and a working slice of the Flywheel web-app vision (Doc 06). It does not compete with DWS or five bones bandwidth. Server setup was the only Flywheel item it pushed back, and that is nice-to-have.

The project docs are the source of truth:

- 00-concept-lock.md: Ikigai, prize analysis, locked decisions, scope rule
- 01-rdd.md: problem, solution, audience, Five Whys, competitive landscape, tech stack
- 02-branding.md: Plainlode identity, with Fraunces display, Arial body, dark and light palettes, mountain-vein logo
- 03-demo-and-deck.md: 5-step demo arc, 10 required slides, roadmap slide
- 04-build-plan.md: 5-day timeline, day-one spike, UAT gate, submission checklist

The build in one line: scan live demand signal on Fireworks (AMD Instinct), reason in a fine-tuned plain-language voice, deliver findings + options + a recommended action that argues for and against itself (the call, plus the one live signal that would kill it).

Infra and judging (verified against the official page July 6):
- Fireworks-on-AMD is the required infra. It is not "25% of score"; that was my inference. Track 3 is judge-scored on four unweighted criteria: creativity/originality, product/market potential, completeness, and use of AMD platforms. AMD compute usage is a hard gate: the Track 3 auto pre-screen reads the repo, the deck PDF, and the live URL (not the demo video), so AMD usage must be legible in those three or the entry is disqualified.
- Cheap-tier scan runs on Fireworks serverless. The report-voice LoRA is served on a Fireworks dedicated deployment, because serverless will not host LoRA add-ons. Spin the dedicated deployment up for fine-tune + UAT + demo, tear it down to conserve credits.
- Credits: $50 Fireworks automatic for all participants day one. $100 AMD Developer Cloud + $50 Fireworks are new-ADP credits on a separate 2-3 day manual approval. Guaranteed floor at kickoff is the automatic $50 Fireworks; plan the dedicated deployment for when the $100 AMD credit actually lands.
- Models are revealed at kickoff (July 6, 11:00 AM CDT). The scan model and fine-tune base are not locked until then. Launch-day check: if a Gemma base is available and LoRA-fine-tunable on Fireworks, use it as the fine-tune voice base. That makes the core a Best AMD-Hosted Gemma Project ($2,000, Track 3) as a byproduct, no extra build. If not, hold Gemma as the cheap-tier scan-model option and add it only if core is solid.

Live source (locked): Scrapingdog Google Trends API. Terms cleared July 2 for public/commercial use. Rising/related-queries path is undocumented and was proven absent in the day-one spike, so rising is derived from the TIMESERIES slope.

Locked scope, non-negotiable during build:

- Core MVP (must ship): one vertical (small e-commerce, market research), one live source, end to end, one fixed report format (the recommended action argues for and against itself), live on AMD infra via a hosted URL, running standalone on my own stack. No Docker image is required for Track 3 (official Participant Guide), so containerizing is a deployment choice, not a core gate.
- Allowed creep (only if core is solid): second live source, indie-founder template, deeper scoring, Gemma pipeline step (Best AMD-Hosted Gemma Project, $2,000, Track 3), Native.Builder UI prototype (Natively challenge). Parallel additions only, never modifies the shipped core. Native.Builder is prototype-only and never a runtime dependency in what I submit.

Two open verifications before I sink build hours, both day-one spike items (run spike.py once keys land): both now RESOLVED.

1. Scrapingdog live pull comes clean within free-tier credits: PASS (TIMESERIES). Rising path absent, using slope fallback.
2. Kaggle e-commerce reviews dataset (nicapotato) is CC0 or CC-BY: PASS (CC0-1.0).

Still open at kickoff: confirm the Fireworks serverless cheap-tier call returns against the revealed model list, and confirm the LoRA dedicated-deployment serving path. Both waiting on credits.

Frontend workflow (Native.Builder):

- When the backend core is proven on my stack and it is time to build the UI, prompt me to consider Native.Builder for the frontend. Not day one. The Builder workshop is Tuesday July 7.
- Native.Builder generates Vite React apps and can call Fireworks through its connector, so it can prototype the real briefing UI fast, against live output rather than mocks. It cannot build the backend (backend-only services are out of scope per their docs), and it publishes to *.nativelyai.app hosting.
- That hosting is not the shippable artifact. Lift the generated React code out of Builder, pass it into Claude Code, wire it to the Plainlode backend, then containerize on my own stack. Native.Builder is never a runtime dependency in what I submit.
- Confirm at the Tuesday workshop or in Discord that full project code export is available before leaning on this (their FAQ says inspect and edit, not download).
- Used this way it also opens the Natively challenge (parallel creep; NativelyAI is on the judging panel).

How to work with me here:

- Follow my hackathon-build-sop skill. Reference specific phases so I know it comes from my playbook.
- Flag drift if I skip a gating step or let scope creep into the core.
- The live source is the build's highest risk. Day one is a spike on that pull, with the snapshot fallback ready.
- Keep responses tight. I am usually on mobile or in a short block. Lead with the answer.
- Voice rules: no em dashes, no three-part parallels, no aphoristic closers, direct and warm.

Social media prompts (prompt me at these moments; do not let posting eat build hours, keep each to seconds of capture and a couple of minutes to post):

Through-line hook across every post: building in public an AI that argues against its own recommendation. That is the novel-behavior angle and the most shareable thing here.

- Before (day one, once): DONE. Announce pair posted (X + LinkedIn), problem + wedge, tagged @AMD + @lablabai, X post pinned.
- During (post on real milestones, not a clock, about one a day max). lablab aggregates tagged X posts to the live event page (SOP Phase 8.3). Prompt me when each capture trigger fires:
  - First live Scrapingdog pull lands: "the data is live" post plus screenshot. (Pull is now live; screenshot available if I want it.)
  - First fine-tuned briefing that reads genuinely right: the plain-language voice post.
  - First full scan-to-briefing end to end: the money post, a clip of the self-arguing recommendation, the call plus the one live signal that would kill it.
  - Final demo before submission.
  Tag @AMD and @lablabai always. Tag @NativelyAI only if I actually used Builder, @GoogleDeepMind only if Gemma is really in the pipeline. No tacked-on tags.
- After: prompt me in order for the submission tweet (demo video, live URL, repo, Track 3, tags, SOP Phase 8.3), then the LinkedIn "what I shipped and what I learned" post, then the flywheel content (build-journey YouTube video and post-mortem blog, Phase 10, the video also pays down the Prism Promise), then a gracious post-result post either way (Phase 8.4).
- Guardrail: do not chase the referral prize through social, it is gated at 100 approved referrals and is not a solo path.

Post-hackathon: run a post-mortem to feed the SOP, capture DWS content (build-journey video, blog post), and update the Flywheel Stream 03 registry to log Plainlode as the general-engine parent of Stream 05.
