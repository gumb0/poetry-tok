# Poetry Tok

A first-pass prototype for a TikTok-style poem reader and recommender.

The current version is intentionally dependency-light:

- `index.html`, `styles.css`, and `app.js` run directly in a browser.
- `data/poems.json` contains the current app corpus.
- Likes/dislikes are stored in `localStorage`.
- Recommendations are based on poem tags and author preference for now.
- `scripts/ingest_gutenberg.py` creates reviewable poem JSON from Gutenberg-style text files.

## Run Locally

Open `index.html` in a browser, or run a small local server:

```bash
python3 -m http.server 5173
```

Then open `http://localhost:5173`.

## Ingest Poems

Project Gutenberg mostly provides full books or collections, so ingestion is a cleanup workflow, not a perfect one-shot import.

Prefer downloading from Gutenberg mirrors or offline files for bulk work. For a single local text file:

```bash
python3 scripts/ingest_gutenberg.py ./raw/dickinson.txt \
  --author "Emily Dickinson" \
  --out data/dickinson.generated.json
```

For the first real corpus candidate, use William Blake's Project Gutenberg ebook `1934`:

```bash
python3 scripts/ingest_gutenberg.py "https://www.gutenberg.org/ebooks/1934.txt.utf-8" \
  --author "William Blake" \
  --source "Project Gutenberg ebook 1934" \
  --exclude-title "Songs Of Innocence" \
  --exclude-title "Songs Of Experience" \
  --out data/blake-songs.generated.json
```

The generated JSON should be manually reviewed before being added to the app corpus.

For a reviewed corpus file, write to `data/poems.json`. Generated scratch files matching `data/*.generated.json` are ignored by git.

## Recommendation Roadmap

The MVP recommender should evolve in stages:

1. Tag-based recommendations from likes/dislikes.
2. Server-side user profiles with `seen`, `liked`, and `disliked` interactions.
3. Poem embeddings stored in Postgres with `pgvector`.
4. Hybrid scoring: embedding similarity, author/theme diversity, dislike avoidance, and exploration.

## Content Notes

Project Gutenberg is a practical source for public-domain classics in the United States, but each text still needs source and copyright review for your target markets. Avoid copying modern poems from sites such as Poetry Foundation or Poets.org unless you have permission or a compatible license.
