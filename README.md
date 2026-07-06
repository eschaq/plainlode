# Plainlode

**The signal, mined plain.**

Plainlode is a market-intelligence engine that scans live market signal and returns a decision-first briefing in plain language for small e-commerce owners. It reads the noisy outside world and hands a solo store owner one clear call on what to sell or stock next, then argues against its own recommendation by naming the single live signal that would kill it.

Built for the **AMD Developer Hackathon: ACT II** (Track 3, Unicorn), July 6-11 2026. Runs on **Fireworks AI, on AMD Instinct** hardware.

> Status: active build. Setup and usage sections grow as the pieces land.

## The idea

A solo WooCommerce owner has more live market signal than they can read and no analyst to read it, so they end up guessing. Everyone else in this space reports internal profit, on Shopify, in a dashboard. Plainlode does the opposite: external market opportunity, WooCommerce-first, delivered as a decision rather than a chart.

The novel behavior is the self-arguing recommendation. The briefing does not just make a call. It states the one piece of live evidence that would reverse that call, so the reader knows exactly what to watch.

## Architecture

```
Live demand signal            Scrapingdog Google Trends API
        |
        v
Cheap-tier scan filter        Fireworks serverless, on AMD Instinct
        |
        v
Fine-tuned report voice       LoRA adapter, Fireworks dedicated deployment, on AMD Instinct
        |
        v
Briefing                      Findings, then Options, then a Recommended
                              action that names the signal that would kill it
```

Two design choices worth calling out. Facts come from live retrieval, not from training, so the briefing stays current at near-zero marginal cost. The fine-tune teaches voice and format only. And rising demand is derived from the trend slope, since the live source exposes interest-over-time rather than a ready-made rising feed.

## Stack

- Backend: FastAPI (Python)
- Runtime model: Fireworks AI on AMD Instinct (cheap-tier scan model plus a fine-tuned report-voice LoRA)
- Live data: Scrapingdog Google Trends API
- Fine-tune corpus: Kaggle e-commerce reviews (CC0), teaches voice only
- Frontend: React + Tailwind
- Hosting: Railway
- License: MIT

## Setup

Requires Python 3.11+ and a Scrapingdog API key.

```bash
git clone https://github.com/eschaq/plainlode.git
cd plainlode
python3 -m venv .venv
source .venv/bin/activate
pip install requests
cp .env.example .env      # then fill in SCRAPINGDOG_API_KEY
```

Load the environment and run the day-one source check:

```bash
set -a; source .env; set +a
python spike.py
```

Full application setup (backend API, frontend, hosted URL) lands here as those pieces are built.

## License

MIT. See [LICENSE](LICENSE).
