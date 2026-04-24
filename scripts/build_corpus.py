#!/usr/bin/env python3
"""Merge reviewed poem JSON files into the app corpus."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="Poem JSON files to merge")
    parser.add_argument("--out", default="data/poems.json")
    args = parser.parse_args()

    poems: list[dict[str, object]] = []
    used_ids: set[str] = set()
    for input_path in args.inputs:
        for poem in json.loads(Path(input_path).read_text(encoding="utf-8")):
            poem["id"] = unique_id(str(poem["id"]), used_ids)
            poems.append(poem)

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(poems, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(poems)} poems to {output_path}")
    return 0


def unique_id(value: str, used_ids: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    base_slug = slug
    suffix = 2
    while slug in used_ids:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    used_ids.add(slug)
    return slug


if __name__ == "__main__":
    raise SystemExit(main())
