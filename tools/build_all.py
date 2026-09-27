"""Rebuild every sheet listed in tools/sheets.json into sheets/<dir>/ and
write the home page (index.html) that links to them.

Usage (from the tuf folder): python tools/build_all.py
"""
import html
import json
from pathlib import Path

from build_sheet import build_page

ROOT = Path(__file__).resolve().parent.parent

HOME = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSA Sheets Backup</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--line:#e3e6ea;--text:#1b1f24;--muted:#66707a;--accent:#e8590c;--ok:#2f9e44}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111214;--card:#1a1c1f;--line:#2c2f34;--text:#e8eaed;--muted:#9aa1a9;--accent:#ff7a2f;--ok:#51cf66}}
:root[data-theme=dark]{--bg:#111214;--card:#1a1c1f;--line:#2c2f34;--text:#e8eaed;--muted:#9aa1a9;--accent:#ff7a2f;--ok:#51cf66}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:40px 16px 64px}
h1{margin:0 0 4px;font-size:30px}
.sub{margin:0 0 28px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px}
a.card{display:flex;flex-direction:column;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;color:inherit;text-decoration:none;transition:border-color .15s,transform .15s}
a.card:hover{border-color:var(--accent);transform:translateY(-2px)}
a.card h2{margin:0;font-size:19px}
a.card p{margin:0;color:var(--muted);font-size:14px;flex:1}
.meta{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
.progress{height:8px;background:var(--line);border-radius:99px;overflow:hidden}
.progress>div{height:100%;background:var(--ok);width:0}
.pct{font-size:13px;font-variant-numeric:tabular-nums}
.pct:empty{display:none}
footer{margin-top:32px;color:var(--muted);font-size:13px}
</style>
</head>
<body>
<div class="wrap">
<h1>DSA Sheets Backup</h1>
<p class="sub">Offline copies of the takeuforward sheets for personal study. Progress, notes and revision marks are saved per sheet in this browser.</p>
<div class="grid">
__CARDS__
</div>
<footer>Use Export progress on each sheet to keep a backup of your progress and notes.</footer>
</div>
<script>
// Chrome and Edge share localStorage across local files, so progress can be shown here.
// Other browsers may keep it per file, in which case the bars stay empty.
document.querySelectorAll("a.card").forEach(c => {
  let data = null;
  try { data = JSON.parse(localStorage.getItem("tuf-progress:" + c.dataset.slug) || "null"); } catch (e) {}
  if (!data) return;
  const done = Object.keys(data.done || (data.star || data.notes ? {} : data)).length;
  const total = +c.dataset.total, pct = total ? Math.round(100 * done / total) : 0;
  c.querySelector(".progress>div").style.width = pct + "%";
  const rev = Object.keys(data.star || {}).length, notes = Object.keys(data.notes || {}).length;
  c.querySelector(".pct").textContent = `${done} / ${total} done (${pct}%)` + (rev ? ` \\u00b7 \\u2605 ${rev}` : "") + (notes ? ` \\u00b7 ${notes} notes` : "");
});
</script>
</body>
</html>
"""


def main():
    config = json.loads((ROOT / "tools" / "sheets.json").read_text(encoding="utf-8"))
    cards = []
    for s in config:
        out = ROOT / "sheets" / s["dir"]
        stats = build_page(ROOT / s["src"], out, s["title"],
                           snapshots=ROOT / s["snapshots"] if s.get("snapshots") and (ROOT / s["snapshots"]).exists() else None,
                           archived=s.get("archived", "Jan 2025"),
                           intro=ROOT / s["intro"] if s.get("intro") else None,
                           step_label=s.get("step_label", "Step"),
                           home="../../index.html")
        unit = s.get("step_label", "Step").lower() + "s"
        cards.append(
            f'<a class="card" href="sheets/{html.escape(s["dir"])}/index.html" data-slug="{stats["slug"]}" data-total="{stats["items"]}">'
            f'<h2>{html.escape(s["title"])}</h2><p>{html.escape(s.get("blurb", ""))}</p>'
            f'<span class="meta">{stats["items"]} {html.escape(s.get("item_label", "problems"))} &middot; {stats["steps"]} {unit} &middot; {stats["videos"]} videos &middot; archived {html.escape(s.get("archived", ""))}</span>'
            f'<div class="progress"><div></div></div><span class="pct"></span></a>')
    (ROOT / "index.html").write_text(HOME.replace("__CARDS__", "\n".join(cards)), encoding="utf-8")
    print(f"Wrote {ROOT / 'index.html'} with {len(cards)} sheets")


if __name__ == "__main__":
    main()
