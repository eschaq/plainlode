# Snapshots

Real prior Scrapingdog pulls, cached so the demo survives when the live source
is out of credits or erroring. Each file is one `list[TermSeries]` keyed by a
normalized category (e.g. `back-to-school.json`).

- Written automatically on every successful live pull (most recent wins).
- Served on a failed or empty live pull, flagged as `scrapingdog_snapshot`.
- Never fabricated. A snapshot only ever holds data from a real live pull.

Most snapshots are git-ignored (see `.gitignore`); `back-to-school.json` is
committed so a fresh clone can run the demo without live credits.

## Capture / refresh the back-to-school snapshot

With Scrapingdog credits available:

```
set -a; source .env; set +a
python -m backend.scan.trends_client
```

This does a real live pull for the back-to-school seeds and writes
`back-to-school.json`. Commit the refreshed file.
