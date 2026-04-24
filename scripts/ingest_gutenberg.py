#!/usr/bin/env python3
"""Convert a Project Gutenberg-style text file into poem JSON.

This is intentionally conservative. Gutenberg texts vary a lot by collection,
so this script creates a reviewable first pass instead of pretending parsing is
perfect.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path


START_MARKERS = (
    "*** START OF THE PROJECT GUTENBERG EBOOK",
    "*** START OF THIS PROJECT GUTENBERG EBOOK",
)
END_MARKERS = (
    "*** END OF THE PROJECT GUTENBERG EBOOK",
    "*** END OF THIS PROJECT GUTENBERG EBOOK",
)


@dataclass
class Poem:
    title: str
    author: str
    text: str
    source: str


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Local .txt file or URL")
    parser.add_argument("--author", required=True)
    parser.add_argument("--source", default="Project Gutenberg")
    parser.add_argument("--min-lines", type=int, default=4)
    parser.add_argument("--max-lines", type=int, default=80)
    parser.add_argument("--out", default="data/poems.generated.json")
    args = parser.parse_args()

    raw_text = read_input(args.input)
    body = strip_gutenberg_boilerplate(raw_text)
    poems = split_poems(body, args.author, args.source, args.min_lines, args.max_lines)

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([poem_to_json(poem) for poem in poems], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(poems)} poem candidates to {output_path}")
    return 0


def read_input(value: str) -> str:
    if value.startswith(("http://", "https://")):
        request = urllib.request.Request(
            value,
            headers={"User-Agent": "poetry-tok-ingest/0.1 (+local development)"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    return Path(value).read_text(encoding="utf-8", errors="replace")


def strip_gutenberg_boilerplate(text: str) -> str:
    lines = normalize_newlines(text).splitlines()
    start_index = 0
    end_index = len(lines)

    for index, line in enumerate(lines):
      if any(marker in line for marker in START_MARKERS):
          start_index = index + 1
          break

    for index, line in enumerate(lines[start_index:], start=start_index):
      if any(marker in line for marker in END_MARKERS):
          end_index = index
          break

    return "\n".join(lines[start_index:end_index]).strip()


def split_poems(text: str, author: str, source: str, min_lines: int, max_lines: int) -> list[Poem]:
    chunks: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if is_probable_title(line):
            if current_title and current_lines:
                chunks.append((current_title, current_lines))
            current_title = clean_title(line)
            current_lines = []
            continue

        if current_title:
            current_lines.append(line)

    if current_title and current_lines:
        chunks.append((current_title, current_lines))

    poems: list[Poem] = []
    for title, lines in chunks:
        poem_text = trim_blank_edges("\n".join(lines))
        poem_lines = [line for line in poem_text.splitlines() if line.strip()]
        if min_lines <= len(poem_lines) <= max_lines:
            poems.append(Poem(title=title, author=author, text=poem_text, source=source))

    return poems


def is_probable_title(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 72:
        return False
    if re.search(r"[.!?,;:]$", stripped):
        return False
    if not re.search(r"[A-Za-z]", stripped):
        return False
    if stripped.startswith(("CHAPTER ", "BOOK ", "PART ")):
        return False
    upperish = stripped.upper() == stripped
    roman = bool(re.fullmatch(r"[IVXLCDM]+", stripped))
    numbered = bool(re.fullmatch(r"\d+\.?", stripped))
    return upperish and not roman and not numbered


def clean_title(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().title())


def trim_blank_edges(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def poem_to_json(poem: Poem) -> dict[str, object]:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{poem.author}-{poem.title}".lower()).strip("-")
    return {
        "id": slug,
        "title": poem.title,
        "author": poem.author,
        "text": poem.text,
        "source": poem.source,
        "lineCount": len([line for line in poem.text.splitlines() if line.strip()]),
        "tags": [],
    }


if __name__ == "__main__":
    sys.exit(main())
