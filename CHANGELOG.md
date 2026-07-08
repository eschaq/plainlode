
## 2026-07-08 — Day 2: scan orchestrator + live AMD filter (build-order step 1 done)

### Built / changed
- backend/scan/scan.py: run_scan(seeds, category, geo) orchestrator. Live pull -> rank -> filter seam -> typed ScanResult.
- backend/scan/fireworks_client.py: complete(prompt, max_tokens). Reads FIREWORKS_API_KEY + FIREWORKS_MODEL, clear named errors if missing. Defensive extract: message.content -> reasoning_content -> stringified message, never raises on shape, returns "" on failure.
- backend/scan/filter.py: real cheap-tier model call on Fireworks (gpt-oss-20b, serverless, AMD Instinct). Judges each above-floor finding keep/drop with a plain-language reason. Every failure path falls back to keeping findings, so the scan never crashes on the model step. Below-floor terms bypass the model and stay displayed.
- backend/prompts/scan_filter.txt: filter prompt, [[CATEGORY]]/[[FINDINGS]] tokens so JSON braces don't collide with substitution.
- Added Finding.reason (str).

### Decisions
- Demo category LOCKED: back to school, hero term "school supplies" (live riser, +25.9%, above floor). Kill signal: seasonal peak in late August. Real self-arguing money shot on live data.
- Scan model: gpt-oss-20b, Fireworks serverless on AMD Instinct. No Gemma on the serverless list, so the Gemma prize does not open via the scan filter; revisit only if a Gemma base is Tunable for the voice LoRA.

### Gotchas / lessons
- gpt-oss reasoning ate a flat 512-token budget before the JSON closed: 512 -> 0 parsed, 1024 -> 5 parsed. Scaled to max(1024, 320*findings). Without it the filter looked green while never running. max_tokens is a ceiling billed per token, so scaling up is safe.
- Filter runs only on above-floor findings, so it never re-decides what the volume floor already excluded.

### Fireworks / budget
- First real token spend against the $50 credit. A few hundred tokens per scan, trivial so far.

### Next
- Fine-tune the report-voice LoRA (CC0 Kaggle corpus) on a Fireworks dedicated deployment. Needs the $100 AMD credit for per-GPU-hour; confirm approval landed.
- Wire ScanResult -> fine-tuned voice -> fixed report format (findings / options / recommended action + the signal that would kill it).

Time: ~[fill in] hrs.
