
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

## 2026-07-08 (day 3, caught up from lost day 2) — voice fine-tune, serving pivot

### Built / changed
- finetune/build_dataset.py -> finetune/train.jsonl: 135 category-agnostic SFT examples (15 verticals), voice + format only, no external corpus. Dropped the Kaggle clothing corpus entirely (was biasing voice to one niche).
- finetune/run_sft.py: uploads dataset (plainlode-voice-v1), launches LoRA SFT via fireworks-ai SDK.
- First fine-tune: gpt-oss-20b base -> plainlode-voice. Completed. But gpt-oss LoRA requires H100+ dedicated, and H100 capacity was UNAVAILABLE at deploy time. Could not test it.
- Re-tune launched: base Llama 3.1 8B Instruct -> plainlode-voice-v2 (job plainlode-voice-0d77c), A100-servable.

### Decisions
- Corpus dropped: fine-tune is category-agnostic hand-built pairs, not Kaggle. CC0 corpus no longer part of the pitch.
- Voice base = Llama 3.1 8B Instruct (dense 8B, A100-friendly, cheapest tier). Backup: Qwen2.5 14B if 8B reads thin.
- Serverless LoRA is NOT supported on Fireworks (any base). Fine-tune can only run on a dedicated deployment.
- Serving ladder for the live URL (weeks-long judging): 1) dedicated A100 fine-tune with masked spin-up + keep-warm, 2) fallback to prompt-engineered voice on serverless gpt-oss (still AMD). Claude API never in the runtime.
- Gemma prize NOT pursued: all Tunable Gemmas are 26B+, back on the H100 capacity wall. Not worth re-fighting.
- gpt-oss H100 cold create hit "no capacity"; also cold start too long to fully mask. Reinforces the A100 + fallback plan.

### Gotchas / lessons
- SDK signatures drift; resolved each by runtime introspection (Dataset.from_file, standalone SFT job not LLM wrapper, fully-qualified accounts/eschachter/models/<name>, accelerator_type required, gpt-oss needs H100+).
- Dedicated deploy needs an explicit accelerator_type; gpt-oss rejects A100.

### Next (day 4, July 9)
1. Check plainlode-voice-0d77c completed. Deploy plainlode-voice-v2 on A100, test one back-to-school briefing, tear down. Judge if the voice ships.
2. Wire ScanResult -> voice -> fixed report format.
3. Frontend (masked spin-up) + Railway deploy.

Time: ~[fill in] hrs.
