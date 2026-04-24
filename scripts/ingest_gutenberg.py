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
from string import capwords


START_MARKERS = (
    "*** START OF THE PROJECT GUTENBERG EBOOK",
    "*** START OF THIS PROJECT GUTENBERG EBOOK",
)
END_MARKERS = (
    "*** END OF THE PROJECT GUTENBERG EBOOK",
    "*** END OF THIS PROJECT GUTENBERG EBOOK",
)

TAG_KEYWORDS = {
    "nature": ("tree", "flower", "rose", "lamb", "bird", "green", "sun", "moon", "garden", "spring"),
    "childhood": ("child", "children", "boy", "girl", "infant", "school", "nurse", "mother", "father"),
    "spiritual": ("god", "angel", "divine", "holy", "soul", "priest", "church", "heaven"),
    "city": ("london", "street", "thames", "palace"),
    "grief": ("weep", "sorrow", "tears", "lost", "fear", "woe"),
    "love": ("love", "kiss", "heart", "desire"),
    "anger": ("wrath", "angry", "cruelty", "jealousy", "terror"),
    "dream": ("dream", "sleep", "night"),
}

SECTION_TITLES = {
    "life",
    "love",
    "nature",
    "time and eternity",
}


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
    parser.add_argument(
        "--exclude-title",
        action="append",
        default=[],
        help="Title to exclude from generated output. Can be passed more than once.",
    )
    parser.add_argument("--min-lines", type=int, default=4)
    parser.add_argument("--max-lines", type=int, default=80)
    parser.add_argument("--out", default="data/poems.generated.json")
    parser.add_argument(
        "--split-mode",
        choices=("auto", "title", "numbered"),
        default="auto",
        help="How to split poems. 'auto' falls back to numbered parsing when title parsing finds little.",
    )
    args = parser.parse_args()

    raw_text = read_input(args.input)
    body = strip_gutenberg_boilerplate(raw_text)
    poems = split_poems(body, args.author, args.source, args)

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    output_path.write_text(
        json.dumps([poem_to_json(poem, existing_ids) for poem in poems], indent=2, ensure_ascii=False) + "\n",
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


def split_poems(text: str, author: str, source: str, args: argparse.Namespace) -> list[Poem]:
    excluded_titles = set(normalize_title(title) for title in args.exclude_title)
    if args.split_mode == "numbered":
        return split_numbered_poems(text, author, source, args.min_lines, args.max_lines, excluded_titles)
    poems = split_title_poems(text, author, source, args.min_lines, args.max_lines, excluded_titles)
    if args.split_mode == "auto" and len(poems) < 5:
        numbered_poems = split_numbered_poems(text, author, source, args.min_lines, args.max_lines, excluded_titles)
        if len(numbered_poems) > len(poems):
            return numbered_poems
    return poems


def split_title_poems(
    text: str,
    author: str,
    source: str,
    min_lines: int,
    max_lines: int,
    excluded_titles: set[str],
) -> list[Poem]:
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
        if normalize_title(title) in excluded_titles:
            continue
        if is_front_matter(title, poem_text):
            continue
        if min_lines <= len(poem_lines) <= max_lines:
            poems.append(Poem(title=title, author=author, text=poem_text, source=source))

    return poems


def split_numbered_poems(
    text: str,
    author: str,
    source: str,
    min_lines: int,
    max_lines: int,
    excluded_titles: set[str],
) -> list[Poem]:
    lines = text.splitlines()
    chunks: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if is_roman_marker(line):
            next_index = next_nonblank_index(lines, index + 1)
            next_line = lines[next_index].strip() if next_index is not None else ""
            if normalize_title(next_line.rstrip(".")) in SECTION_TITLES:
                index += 1
                continue
            if current_title and current_lines:
                chunks.append((current_title, current_lines))
            title, body_start = numbered_poem_title(lines, index, next_index)
            current_title = title
            current_lines = []
            index = body_start
            continue
        if current_title:
            current_lines.append(line)
        index += 1

    if current_title and current_lines:
        chunks.append((current_title, current_lines))

    poems: list[Poem] = []
    for title, lines in chunks:
        poem_text = trim_blank_edges("\n".join(lines))
        poem_lines = [line for line in poem_text.splitlines() if line.strip()]
        if normalize_title(title) in excluded_titles:
            continue
        if min_lines <= len(poem_lines) <= max_lines:
            poems.append(Poem(title=title, author=author, text=poem_text, source=source))
    return poems


def is_roman_marker(line: str) -> bool:
    return bool(re.fullmatch(r"\s{0,24}[IVXLCDM]+\.", line))


def next_nonblank_index(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def numbered_poem_title(lines: list[str], marker_index: int, next_index: int | None) -> tuple[str, int]:
    fallback_title = ""
    if next_index is not None:
        fallback_title = first_line_title(lines[next_index].strip())

    if next_index is not None and is_numbered_poem_title(lines[next_index]):
        title = clean_title(lines[next_index])
        body_start = next_index + 1
        return title, body_start

    marker = lines[marker_index].strip().rstrip(".")
    title = fallback_title or f"Poem {marker}"
    return title, marker_index + 1


def first_line_title(line: str) -> str:
    title = re.sub(r"\s+", " ", line.strip())
    title = title.rstrip(" ,;:-")
    if len(title) > 54:
        title = title[:51].rstrip() + "..."
    return title


def is_numbered_poem_title(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 72:
        return False
    if not re.search(r"[A-Za-z]", stripped):
        return False
    title_candidate = stripped.rstrip(".")
    if normalize_title(title_candidate) in SECTION_TITLES:
        return False
    return title_candidate.upper() == title_candidate


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
    return capwords(re.sub(r"\s+", " ", line.strip().rstrip(".")))


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip()).casefold()


def is_front_matter(title: str, text: str) -> bool:
    normalized = normalize_title(title)
    if normalized.startswith("by "):
        return True
    if "london:" in text.casefold() or "guildford:" in text.casefold():
        return True
    return False


def trim_blank_edges(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def poem_to_json(poem: Poem, existing_ids: set[str]) -> dict[str, object]:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{poem.author}-{poem.title}".lower()).strip("-")
    base_slug = slug
    suffix = 2
    while slug in existing_ids:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    existing_ids.add(slug)
    return {
        "id": slug,
        "title": poem.title,
        "author": poem.author,
        "text": poem.text,
        "source": poem.source,
        "lineCount": len([line for line in poem.text.splitlines() if line.strip()]),
        "tags": infer_tags(poem),
    }


def infer_tags(poem: Poem) -> list[str]:
    searchable = f"{poem.title}\n{poem.text}".casefold()
    tags = [
        tag
        for tag, keywords in TAG_KEYWORDS.items()
        if any(keyword in searchable for keyword in keywords)
    ]
    line_count = len([line for line in poem.text.splitlines() if line.strip()])
    if line_count <= 12:
        tags.append("short")
    elif line_count <= 32:
        tags.append("medium")
    else:
        tags.append("long")
    return tags


if __name__ == "__main__":
    sys.exit(main())
