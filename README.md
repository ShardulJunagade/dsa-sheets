# DSA Sheets

A personal study index for Striver's A2Z DSA Sheet, SDE Sheet and System Design
sheet, rebuilt from archived data after the original pages changed. Each sheet
lists the problems in order and links out to the YouTube videos, archived
takeuforward articles (Wayback Machine) and practice problems on LeetCode, GFG
and Coding Ninjas. All credit for the curation goes to takeuforward / Striver.

Open `index.html` locally, or use the GitHub Pages site.

## Progress

Done marks, revision stars and notes are saved in your browser's localStorage,
separately for each sheet. Use **Export progress** / **Import progress** on a
sheet to back them up or move them to another browser or device.

## Rebuilding

```
python tools/build_all.py
```

Sheets are configured in `tools/sheets.json`. `tools/resolve_snapshots.py`
finds a Wayback Machine snapshot that still contains each article's text, since
the live article pages now return 404.
