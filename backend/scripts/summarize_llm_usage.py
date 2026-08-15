#!/usr/bin/env python3
"""Summarize numeric LLM usage events written by AIProcessor."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
    "reasoning_tokens",
)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def summarize(path: Path) -> dict[str, Any]:
    totals: dict[str, int] = {"request_count": 0, **{field: 0 for field in FIELDS}}
    by_model: dict[str, dict[str, int]] = defaultdict(
        lambda: {"request_count": 0, **{field: 0 for field in FIELDS}}
    )
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            model = str(event.get("model") or "unknown")
            for bucket in (totals, by_model[model]):
                bucket["request_count"] += 1
                for field in FIELDS:
                    bucket[field] += _as_int(event.get(field))
    return {"totals": totals, "by_model": dict(by_model)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.path), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
