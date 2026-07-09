"""Print the Plainlode run log as a readable table.

Reads data/run_log.jsonl (append-only, one scan per line) and prints ts,
category, source, and kept_count so recent runs are reviewable at a glance.

Run from the repo root:  python -m backend.scan.read_log
"""

import json
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RUN_LOG_PATH = os.path.join(_REPO_ROOT, "data", "run_log.jsonl")


def read_entries(path=RUN_LOG_PATH):
    """Load the run log as a list of dicts, skipping any unreadable lines."""
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue  # skip a corrupt line rather than crash the reader
    return entries


def main():
    entries = read_entries()
    if not entries:
        print(f"No runs logged yet ({RUN_LOG_PATH})")
        return
    print(f"{'ts':26}  {'category':18}  {'source':22}  {'kept':>4}")
    print("-" * 76)
    for e in entries:
        print(f"{e.get('ts', ''):26}  {e.get('category', ''):18}  "
              f"{e.get('source', ''):22}  {e.get('kept_count', 0):>4}")
    print(f"\n{len(entries)} runs logged")


if __name__ == "__main__":
    main()
