"""Build an offline, single-file HTML copy of a takeuforward sheet index.

Usage: python build_sheet.py <sheet.json> <out_dir> "<Sheet Title>"
           [--snapshots snapshots.json] [--archived "Jan 2025"] [--intro intro.html]

The input JSON is the archived API response, either the flat shape
({"sheetData": [{step, topics}]}, e.g. System Design) or the grouped shape
([{step, sub_steps: [{topics}]}], e.g. A2Z). The sheet index (titles + links)
is rebuilt locally; YouTube links are normalised to plain youtube.com URLs and
takeuforward article links are pointed at their Wayback Machine snapshots,
since the live pages now 404.
"""
import argparse
import gzip
import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Fallback when an article has no resolved snapshot: Wayback redirects to the
# capture nearest this date, which is before the site became a JS shell.
DEFAULT_SNAPSHOT = "20240301000000"
DIFFICULTY = {0: "Easy", 1: "Medium", 2: "Hard"}
PRACTICE_FIELDS = [("lc_link", "LC"), ("gfg_link", "GFG"), ("cs_link", "CN")]
HOST_LABELS = [("leetcode.com", "LC"), ("geeksforgeeks.org", "GFG"), ("codingninjas.com", "CN"),
               ("naukri.com", "CN"), ("interviewbit.com", "IB"), ("spoj.com", "SPOJ"),
               ("codeforces.com", "CF"), ("hackerrank.com", "HR"), ("youtube.com", "Video")]


def load_json(path):
    raw = Path(path).read_bytes()
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass
    return json.loads(raw.decode("utf-8"))


def strip_wayback(url):
    return re.sub(r"^https?://web\.archive\.org/web/[^/]+/", "", url.strip())


def clean_youtube(url):
    if not url:
        return None
    url = strip_wayback(url)
    p = urlparse(url)
    q = parse_qs(p.query)
    if p.netloc.endswith("youtu.be"):
        vid = p.path.strip("/")
    elif "v" in q:
        vid = q["v"][0]
    else:
        return url
    out = f"https://www.youtube.com/watch?v={vid}"
    if "t" in q:
        out += f"&t={q['t'][0]}"
    return out


def clean_article(url, snapshots):
    if not url:
        return None
    url = strip_wayback(url).replace("://interviewreadyio/", "://interviewready.io/")
    if re.match(r"^https?://(www\.)?takeuforward\.org/", url):
        key = urlparse(url).path.strip("/")
        ts = snapshots.get(key) or DEFAULT_SNAPSHOT
        return f"https://web.archive.org/web/{ts}/{url}"
    return url


def practice_links(t):
    out, seen = [], set()
    for field, default in PRACTICE_FIELDS:
        url = t.get(field)
        if not url or not url.strip():
            continue
        url = strip_wayback(url)
        if url in seen:
            continue
        seen.add(url)
        host = urlparse(url).netloc.lower()
        label = next((lab for h, lab in HOST_LABELS if host.endswith(h)), default)
        out.append({"label": label, "url": url})
    return out


def item(t, snapshots):
    return {
        "id": t["id"],
        "title": (t.get("question_title") or t.get("title") or "").strip(),
        "article": clean_article(t.get("post_link"), snapshots),
        "youtube": clean_youtube(t.get("yt_link")),
        "practice": practice_links(t),
        "difficulty": DIFFICULTY.get(t.get("difficulty")),
    }


def build(data, snapshots):
    steps = []
    if isinstance(data, dict) and "sheetData" in data:
        for s in data["sheetData"]:
            steps.append({"step": s["step_no"], "name": s["head_step_no"],
                          "groups": [{"name": None, "items": [item(t, snapshots) for t in s["topics"]]}]})
    else:
        for s in data:
            groups = [{"name": g["sub_step_title"], "items": [item(t, snapshots) for t in g["topics"]]}
                      for g in s["sub_steps"]]
            steps.append({"step": s["step_no"], "name": s["step_title"], "groups": groups})
    return steps


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--line:#e3e6ea;--text:#1b1f24;--muted:#66707a;--accent:#e8590c;--accent-soft:#fff1e8;--ok:#2f9e44;--row:#fafbfc;--easy:#2f9e44;--medium:#e67700;--hard:#e03131}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111214;--card:#1a1c1f;--line:#2c2f34;--text:#e8eaed;--muted:#9aa1a9;--accent:#ff7a2f;--accent-soft:#2a1a10;--ok:#51cf66;--row:#1e2024;--easy:#51cf66;--medium:#fcc419;--hard:#ff6b6b}}
:root[data-theme=dark]{--bg:#111214;--card:#1a1c1f;--line:#2c2f34;--text:#e8eaed;--muted:#9aa1a9;--accent:#ff7a2f;--accent-soft:#2a1a10;--ok:#51cf66;--row:#1e2024;--easy:#51cf66;--medium:#fcc419;--hard:#ff6b6b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:32px 16px 64px}
header h1{margin:0 0 4px;font-size:28px}
header p{margin:0;color:var(--muted)}
header p.home{margin:0 0 12px;font-size:14px}
.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:20px 0 24px}
.bar.tools{margin-top:-12px}
.progress{flex:1;min-width:200px;height:10px;background:var(--line);border-radius:99px;overflow:hidden}
.progress>div{height:100%;background:var(--ok);width:0;transition:width .2s}
.count{font-variant-numeric:tabular-nums;color:var(--muted);font-size:14px}
.count b{font-weight:600}
button,select,input[type=search]{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:6px}
button,select{cursor:pointer}
button:hover,select:hover{border-color:var(--accent)}
input[type=search]{min-width:220px;flex:1;max-width:340px}
button[aria-pressed=true]{border-color:var(--accent);background:var(--accent-soft);color:var(--accent)}
details.step{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:12px;overflow:hidden}
summary{list-style:none;cursor:pointer;padding:14px 16px;display:flex;gap:12px;align-items:center;font-weight:600}
summary::-webkit-details-marker{display:none}
summary .num{color:var(--accent);font-variant-numeric:tabular-nums;min-width:60px}
summary .name{flex:1}
.sc{font-weight:400;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
summary::after{content:"\\25B8";color:var(--muted);transition:transform .15s}
details[open]>summary::after{transform:rotate(90deg)}
.group h3{margin:0;padding:12px 16px;font-size:14px;display:flex;gap:12px;align-items:center;border-top:1px solid var(--line);background:var(--row)}
.group h3 .lec{color:var(--accent);white-space:nowrap}
.group h3 .gname{flex:1}
.scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse}
th,td{padding:9px 14px;border-top:1px solid var(--line);text-align:left;vertical-align:middle}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600}
td.c,td.s,td.n{width:44px;text-align:center}
td.l{white-space:nowrap}
td.p a{margin-right:10px}
tr.done td.t{color:var(--muted);text-decoration:line-through}
.diff{font-size:13px;font-weight:600}
.diff.Easy{color:var(--easy)}.diff.Medium{color:var(--medium)}.diff.Hard{color:var(--hard)}
.icon{border:0;background:none;padding:2px 4px;line-height:1;color:var(--muted);cursor:pointer;opacity:.45}
.icon:hover{opacity:1;border:0;color:var(--accent)}
.star{font-size:20px}
.star.on{color:#f59f00;opacity:1}
.note-btn{font-size:16px}
.note-btn.has{color:var(--accent);opacity:1}
tr.note-row td{padding:0 14px 12px;border-top:0}
tr.note-row textarea{width:100%;min-height:80px;font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--text);resize:vertical}
input[type=checkbox]{width:18px;height:18px;accent-color:var(--ok);cursor:pointer}
a{color:var(--accent);text-decoration:none;font-weight:500}
a:hover{text-decoration:underline}
.na{color:var(--muted)}
.empty{padding:24px;text-align:center;color:var(--muted)}
.intro{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:18px 22px;margin-top:20px}
.intro h2{margin:0 0 8px;font-size:20px}
.intro p{margin:8px 0}
.intro ol,.intro ul{margin:8px 0;padding-left:22px}
.intro strong{color:var(--accent)}
footer{margin-top:28px;color:var(--muted);font-size:13px}
@media (max-width:600px){th,td{padding:8px}summary .num{min-width:auto}input[type=search]{max-width:none}}
</style>
</head>
<body>
<div class="wrap">
<header>
__HOME__
<h1>__TITLE__</h1>
<p>Offline backup of the takeuforward sheet index (archived __ARCHIVED__). Progress is saved in this browser.</p>
</header>
__INTRO__
<div class="bar">
<div class="progress"><div id="pb"></div></div>
<span class="count" id="total"></span>
<span class="count" id="diffs"></span>
<span class="count" id="stars"></span>
</div>
<div class="bar tools">
<input type="search" id="q" placeholder="Search problems" aria-label="Search problems">
<select id="diff" aria-label="Filter by difficulty"><option value="">All difficulties</option><option>Easy</option><option>Medium</option><option>Hard</option></select>
<select id="status" aria-label="Filter by status"><option value="">All</option><option value="todo">Not done</option><option value="done">Done</option></select>
<button id="onlyStar" aria-pressed="false">&#9733; Revision only</button>
<button id="expand">Expand all</button>
</div>
<div class="bar tools">
<button id="export">Export progress</button>
<button id="import">Import progress</button>
<input type="file" id="importFile" accept="application/json,.json" hidden>
<button id="reset">Reset progress</button>
</div>
<main id="sheet"></main>
<footer>Article links for takeuforward pages open their Wayback Machine snapshot. Practice links (LeetCode, GFG, Coding Ninjas, etc.) and YouTube go to the original sites.</footer>
</div>
<script>
const SHEET = __DATA__;
const SLUG = "__SLUG__";
const KEY = "tuf-progress:" + SLUG;
const ITEMS = SHEET.flatMap(s => s.groups.flatMap(g => g.items));
const HAS_PRACTICE = ITEMS.some(t => t.practice.length);
const HAS_DIFF = ITEMS.some(t => t.difficulty);
if (!HAS_DIFF) document.getElementById("diff").hidden = true;
let done = {}, star = {}, notes = {};
function load(obj) {
  // Accepts {done, star, notes} and the older plain {id: 1} map of done items.
  if (obj && (obj.done || obj.star || obj.notes)) { done = obj.done || {}; star = obj.star || {}; notes = obj.notes || {}; }
  else { done = obj || {}; star = {}; notes = {}; }
}
try { load(JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify({done, star, notes})); } catch (e) {} };
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const link = (u, label) => u ? `<a href="${esc(u)}" target="_blank" rel="noopener">${label}</a>` : `<span class="na">&ndash;</span>`;
const COLS = 5 + (HAS_PRACTICE ? 1 : 0) + (HAS_DIFF ? 1 : 0) + 1;
const head = `<thead><tr><th>Done</th><th>Problem</th><th>Article</th><th>YouTube</th>${HAS_PRACTICE ? "<th>Practice</th>" : ""}<th>Note</th>${HAS_DIFF ? "<th>Difficulty</th>" : ""}<th>Revision</th></tr></thead>`;
const row = t => `<tr data-id="${esc(t.id)}">
<td class="c"><input type="checkbox" aria-label="Mark ${esc(t.title)} done"></td>
<td class="t">${esc(t.title)}</td>
<td class="l">${link(t.article, "Read")}</td>
<td class="l">${link(t.youtube, "Watch")}</td>
${HAS_PRACTICE ? `<td class="l p">${t.practice.length ? t.practice.map(p => link(p.url, esc(p.label))).join("") : '<span class="na">&ndash;</span>'}</td>` : ""}
<td class="n"><button class="icon note-btn" aria-label="Note for ${esc(t.title)}" title="Notes">&#9998;</button></td>
${HAS_DIFF ? `<td><span class="diff ${t.difficulty || ""}">${t.difficulty || ""}</span></td>` : ""}
<td class="s"><button class="icon star" aria-label="Mark ${esc(t.title)} for revision" aria-pressed="false">&#9733;</button></td></tr>`;
const root = document.getElementById("sheet");
root.innerHTML = SHEET.map(s => `
<details class="step" data-step="${s.step}">
<summary><span class="num">__STEP__ ${s.step}</span><span class="name">${esc(s.name)}</span><span class="sc"></span></summary>
${s.groups.map((g, i) => `<section class="group">
${g.name ? `<h3><span class="lec">Lec ${i + 1}:</span><span class="gname">${esc(g.name)}</span><span class="sc"></span></h3>` : ""}
<div class="scroll"><table>${head}<tbody>${g.items.map(row).join("")}</tbody></table></div></section>`).join("")}
</details>`).join("") + '<p class="empty" id="empty" hidden>No problems match these filters.</p>';

const q = document.getElementById("q"), diffSel = document.getElementById("diff"), statusSel = document.getElementById("status");
const only = document.getElementById("onlyStar");
const byId = Object.fromEntries(ITEMS.map(t => [t.id, t]));
const filtering = () => !!(q.value.trim() || diffSel.value || statusSel.value || only.getAttribute("aria-pressed") === "true");
function visible(id) {
  const t = byId[id], term = q.value.trim().toLowerCase();
  if (term && !t.title.toLowerCase().includes(term)) return false;
  if (diffSel.value && t.difficulty !== diffSel.value) return false;
  if (statusSel.value === "done" && !done[id]) return false;
  if (statusSel.value === "todo" && done[id]) return false;
  if (only.getAttribute("aria-pressed") === "true" && !star[id]) return false;
  return true;
}
function refresh() {
  const f = filtering();
  let all = 0, n = 0, st = 0, shown = 0;
  const dc = {Easy: [0, 0], Medium: [0, 0], Hard: [0, 0]};
  root.querySelectorAll("details.step").forEach(d => {
    let sk = 0, stot = 0, svis = 0;
    d.querySelectorAll("section.group").forEach(g => {
      let k = 0, vis = 0;
      const rows = g.querySelectorAll("tr[data-id]");
      rows.forEach(r => {
        const id = r.dataset.id, on = !!done[id], s = !!star[id], t = byId[id];
        r.classList.toggle("done", on);
        r.querySelector("input").checked = on;
        const b = r.querySelector(".star");
        b.classList.toggle("on", s);
        b.setAttribute("aria-pressed", s);
        r.querySelector(".note-btn").classList.toggle("has", !!notes[id]);
        const v = visible(id);
        r.hidden = !v;
        const nr = r.nextElementSibling;
        if (nr && nr.classList.contains("note-row")) nr.hidden = !v;
        if (v) vis++;
        if (on) k++;
        if (s) st++;
        if (t.difficulty) { dc[t.difficulty][1]++; if (on) dc[t.difficulty][0]++; }
      });
      const h = g.querySelector("h3 .sc");
      if (h) h.textContent = `${k} / ${rows.length}`;
      g.hidden = vis === 0;
      sk += k; stot += rows.length; svis += vis;
    });
    d.querySelector("summary .sc").textContent = `${sk} / ${stot}`;
    d.hidden = svis === 0;
    if (f && svis) d.open = true;
    all += stot; n += sk; shown += svis;
  });
  document.getElementById("empty").hidden = shown > 0;
  document.getElementById("total").textContent = `${n} / ${all} done (${all ? Math.round(100 * n / all) : 0}%)`;
  document.getElementById("diffs").innerHTML = HAS_DIFF ? Object.entries(dc).map(([k, [a, b]]) => `<span class="diff ${k}">${k}</span> <b>${a}/${b}</b>`).join(" &middot; ") : "";
  document.getElementById("stars").textContent = `★ ${st} for revision`;
  document.getElementById("pb").style.width = (all ? 100 * n / all : 0) + "%";
}
root.addEventListener("change", e => {
  const r = e.target.closest("tr[data-id]");
  if (!r || e.target.type !== "checkbox") return;
  if (e.target.checked) done[r.dataset.id] = 1; else delete done[r.dataset.id];
  save(); refresh();
});
root.addEventListener("click", e => {
  const b = e.target.closest(".star, .note-btn");
  if (!b) return;
  const r = b.closest("tr[data-id]"), id = r.dataset.id;
  if (b.classList.contains("star")) {
    if (star[id]) delete star[id]; else star[id] = 1;
    save(); refresh();
    return;
  }
  const next = r.nextElementSibling;
  if (next && next.classList.contains("note-row")) { next.remove(); return; }
  const nr = document.createElement("tr");
  nr.className = "note-row";
  nr.innerHTML = `<td colspan="${COLS}"><textarea placeholder="Your notes for this problem (saved automatically)" aria-label="Notes for ${esc(byId[id].title)}"></textarea></td>`;
  r.after(nr);
  const ta = nr.querySelector("textarea");
  ta.value = notes[id] || "";
  ta.focus();
  ta.addEventListener("input", () => {
    if (ta.value.trim()) notes[id] = ta.value; else delete notes[id];
    save();
    b.classList.toggle("has", !!notes[id]);
  });
});
[q, diffSel, statusSel].forEach(el => el.addEventListener("input", refresh));
only.onclick = () => {
  only.setAttribute("aria-pressed", only.getAttribute("aria-pressed") !== "true");
  refresh();
};
document.getElementById("export").onclick = () => {
  const data = {sheet: SLUG, exported: new Date().toISOString(), done, star, notes};
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
  const a = document.createElement("a");
  a.href = url;
  a.download = `${SLUG}-progress-${data.exported.slice(0, 10)}.json`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
const file = document.getElementById("importFile");
document.getElementById("import").onclick = () => file.click();
file.onchange = async () => {
  const f = file.files[0];
  file.value = "";
  if (!f) return;
  let data;
  try { data = JSON.parse(await f.text()); } catch (e) { alert("That file isn't valid JSON."); return; }
  if (!data || typeof data !== "object" || !(data.done || data.star || data.notes)) { alert("That file doesn't look like an exported progress file."); return; }
  if (data.sheet && data.sheet !== SLUG && !confirm(`This file is for "${data.sheet}", not "${SLUG}". Import anyway?`)) return;
  const pick = m => Object.fromEntries(Object.keys(m || {}).filter(k => byId[k]).map(k => [k, 1]));
  const nd = pick(data.done), ns = pick(data.star);
  const nn = Object.fromEntries(Object.entries(data.notes || {}).filter(([k, v]) => byId[k] && typeof v === "string" && v.trim()));
  if (!confirm(`Replace current progress with ${Object.keys(nd).length} done, ${Object.keys(ns).length} marked for revision and ${Object.keys(nn).length} notes from this file?`)) return;
  done = nd; star = ns; notes = nn;
  root.querySelectorAll("tr.note-row").forEach(r => r.remove());
  save(); refresh();
};
const ex = document.getElementById("expand");
ex.onclick = () => {
  const open = ex.textContent === "Expand all";
  root.querySelectorAll("details.step").forEach(d => d.open = open);
  ex.textContent = open ? "Collapse all" : "Expand all";
};
document.getElementById("reset").onclick = () => {
  if (confirm("Clear all done marks, revision stars and notes for this sheet?")) {
    done = {}; star = {}; notes = {};
    root.querySelectorAll("tr.note-row").forEach(r => r.remove());
    save(); refresh();
  }
};
refresh();
</script>
</body>
</html>
"""


def slugify(title):
    # Also the localStorage key suffix, so changing a sheet's title orphans its saved progress.
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def build_page(src, out_dir, title, snapshots=None, archived="Jan 2025", intro=None,
               step_label="Step", home=None):
    """Write <out_dir>/index.html and sheet.json; return summary stats for the home page."""
    out_dir = Path(out_dir)
    snapshots = load_json(snapshots) if snapshots else {}
    steps = build(load_json(src), snapshots)
    out_dir.mkdir(parents=True, exist_ok=True)
    # The intro lives in a separate intro.js (git-ignored) so it shows locally but
    # isn't published; the page just skips it when the file is missing.
    intro_js = out_dir / "intro.js"
    if intro and Path(intro).exists():
        body = json.dumps(Path(intro).read_text(encoding="utf-8")).replace("</", "<\\/")
        intro_js.write_text('(function(){var e=document.getElementById("intro");'
                            f'e.innerHTML={body};e.hidden=false;}})();\n', encoding="utf-8")
        intro = '<section class="intro" id="intro" hidden></section><script src="intro.js"></script>'
    else:
        intro_js.unlink(missing_ok=True)
        intro = ""
    (out_dir / "sheet.json").write_text(json.dumps(steps, indent=2, ensure_ascii=False), encoding="utf-8")
    slug = slugify(title)
    back = f'<p class="home"><a href="{html.escape(home)}">&larr; All sheets</a></p>' if home else ""
    page = (PAGE.replace("__TITLE__", html.escape(title))
                .replace("__HOME__", back)
                .replace("__ARCHIVED__", html.escape(archived))
                .replace("__SLUG__", slug)
                .replace("__STEP__", html.escape(step_label))
                .replace("__INTRO__", intro)
                .replace("__DATA__", json.dumps(steps, ensure_ascii=False).replace("</", "<\\/")))
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    items = [t for s in steps for g in s["groups"] for t in g["items"]]
    unresolved = sum(1 for t in items if t["article"] and f"/web/{DEFAULT_SNAPSHOT}/" in t["article"])
    print(f"Wrote {out_dir / 'index.html'}: {len(steps)} steps, {len(items)} items"
          + (f", {unresolved} articles using fallback snapshot" if unresolved else ""))
    return {"slug": slug, "steps": len(steps), "items": len(items),
            "videos": sum(1 for t in items if t["youtube"]),
            "articles": sum(1 for t in items if t["article"]),
            "fallback": unresolved}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("title")
    ap.add_argument("--snapshots", help="JSON map of article path -> Wayback timestamp")
    ap.add_argument("--archived", default="Jan 2025")
    ap.add_argument("--intro", help="HTML fragment shown above the sheet")
    ap.add_argument("--step-label", default="Step", help='Prefix for step headings, e.g. "Day"')
    ap.add_argument("--home", help="Relative link back to the home page")
    args = ap.parse_args()
    build_page(args.src, args.out_dir, args.title, args.snapshots, args.archived, args.intro,
               args.step_label, args.home)


if __name__ == "__main__":
    main()
