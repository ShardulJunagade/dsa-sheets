# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal study backup of takeuforward's DSA sheets (Striver's A2Z, SDE, System Design). takeuforward
redesigned its site, and these sheets and articles are gone from it. The sheets are rebuilt from Wayback
Machine captures of the site's backend API as static, self-contained HTML pages. They track progress
(done / revision star / notes) in the browser. The repo is published with GitHub Pages
(`ShardulJunagade/dsa-sheets`, served from the root of `main`; `.nojekyll` is present).

## Commands

```
python tools/build_all.py        # rebuild every sheet + the home page (run from anywhere)
python tools/resolve_snapshots.py sources/<name>.raw.json sources/<name>.snapshots.json [--seed other.snapshots.json] [--retry-missing]
python tools/build_sheet.py <raw.json> <out_dir> "<Title>" [...]   # one-off build of a single sheet
```

There is no test suite, linter or package manifest. The tools use only the Python standard library.
To check page behaviour, earlier sessions used jsdom under node (for DOM and logic) and headless Edge
screenshots (for layout; Edge is at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`).

## Data flow

```
sources/<name>.raw.json          archived API response (the sheet's source of truth)
sources/<name>.snapshots.json    article path -> Wayback timestamp (made by resolve_snapshots.py)
sources/system-design.intro.html optional intro text (git-ignored)
tools/sheets.json                list of sheets: dir, title, src, snapshots, archived, step_label, ...
        │  tools/build_all.py → build_sheet.build_page()
        ▼
sheets/<dir>/index.html   single file: the sheet data is embedded as JSON, CSS and JS are inline
sheets/<dir>/sheet.json   the same normalized data (steps → groups → items)
sheets/<dir>/intro.js     only if an intro exists (git-ignored, so it's shown locally but not published)
index.html                home page with a card per sheet
```

`sheets/` and `index.html` are **generated but committed**, because Pages serves them. Change the
tools or sources, then rebuild. Never hand-edit the generated files.

## Key design points (spread across files)

- **Two input shapes.** `build_sheet.build()` normalizes both into `steps → groups → items`:
  - Flat: `{"sheetData": [{step_no, head_step_no, topics}]}`, used by SDE and System Design. Each
    step becomes one unnamed group.
  - Grouped: `[{step_no, step_title, sub_steps: [{sub_step_title, topics}]}]`, used by A2Z. Groups
    render as "Lec N".
- **Link cleanup.** YouTube links become `https://www.youtube.com/watch?v=ID` (with `&t=` kept).
  Practice links come from `lc_link` / `gfg_link` / `cs_link`, labelled by host.
  `difficulty` 0/1/2 maps to Easy/Medium/Hard.
- **Article links.** All the takeuforward article URLs now 404. From about Sep 2024 the site was a JS
  shell, so its archive captures have no article text. Only earlier captures (mostly 2023 to
  Mar 2024) do. Each value in `snapshots.json` means:
  - `"<timestamp>"`: a capture that was verified to contain the article.
  - `false`: every candidate was checked and none has the article. The link goes to the `/web/*/`
    capture list and renders as a muted "Archive" link.
  - `null` or missing: not verified yet. The link falls back to `DEFAULT_SNAPSHOT` (20240301).
- **Resolver behaviour.** `resolve_snapshots.py` is slow on purpose: one worker and a 1.5 s pause
  between requests, because the archive refuses connections under load.
  - It holds an OS lock (`<out>.lock`) so only one run works on a results file at a time.
  - It re-reads the file before every save and merges, with the order of precedence
    timestamp > false > null, so overlapping runs can't erase results.
  - Reruns skip anything already resolved. `--seed` reuses another sheet's results (most SDE
    articles are also in A2Z).
  - Background runs have outlived their sessions as orphaned `python.exe` processes before. Check
    for them before starting a new run.
- **Progress storage.** Progress is stored in localStorage under `tuf-progress:<slug>`, where the
  slug is `slugify(title)`.
  - Changing a sheet's `title` in `sheets.json` orphans users' saved progress.
  - The stored value is `{done, star, notes}`. `load()` also accepts the older format, a plain map
    of done IDs.
  - Export/import uses the same shape plus `sheet` and `exported` fields. Import replaces what's in
    the browser rather than merging, and drops IDs that aren't in the sheet.
  - The home page reads these same keys, which only works where file:// pages share storage
    (Chrome and Edge).

## Publishing constraints

- Never commit `console/` (the user's saved takeuforward pages, for local reference only) or the
  intro/FAQ text. Both are covered by `.gitignore`.
- Before pushing, check that no copied page text is staged, e.g.
  `git grep --cached -l -e "billions of dollars" -e "Key Highlights"`.
- Committed sources hold only titles, IDs and links.

## Adding another sheet

The archived API captures are listed by
`https://web.archive.org/cdx/search/cdx?url=backend.takeuforward.org/api/sheets/*`. Examples are
`sheets/core/{CN,DBMS,OS}_Sheet`, `sheets/cp-sheet/`, and `sheets/single/{blind_75,strivers_79_sheet,...}`.

1. Pick the latest capture from before the redesign.
2. Fetch it with `id_` (`/web/<ts>id_/<url>`). The response may be gzipped; `load_json()` handles that.
3. Save it to `sources/`.
4. Add an entry to `tools/sheets.json`.
5. Run the resolver.
6. Run `build_all.py`.

A new response shape needs a branch in `build()`.
