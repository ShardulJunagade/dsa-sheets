"""Find a Wayback Machine snapshot that still has the article text for every
takeuforward article linked from a sheet.

Usage: python resolve_snapshots.py <sheet.raw.json> <snapshots.json> [--before 20250401]
           [--workers 1] [--seed other.snapshots.json]

From about Sep 2024 takeuforward pages are an empty JS shell (the text came from
an API the archive rarely captured), so we pick the newest earlier capture that
is big enough and actually contains the article. Results are written as
{"<path>": "<timestamp>" | null}; reruns retry every null (misses are often
rate-limited responses), so run it again until the unresolved count stops falling.
"""
import argparse
import json
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from build_sheet import load_json  # noqa: E402

STOP = {"data", "structure", "structures", "algorithm", "algorithms", "problem", "problems",
        "with", "using", "from", "into", "that", "java", "code", "array", "arrays"}
lock = threading.Lock()


PAUSE = 1.5  # seconds between requests; the archive refuses connections if pushed harder


def get(url, tries=4):
    err = None
    for i in range(tries):
        time.sleep(PAUSE)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tuf-backup/1.0"})
            return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
        except Exception as e:
            err = e
            time.sleep((15, 45, 90, 120)[i])
    raise err


def article_paths(data):
    rows = data["sheetData"] if isinstance(data, dict) else data
    out = []
    def walk(x):
        if isinstance(x, dict):
            link = x.get("post_link")
            if link and re.match(r"^https?://(www\.)?takeuforward\.org/", link.strip()):
                out.append(urlparse(link.strip()).path.strip("/"))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(rows)
    return list(dict.fromkeys(out))


def keywords(path):
    words = re.findall(r"[a-z]{4,}", path.split("/")[-1].lower())
    words = [w for w in words if w not in STOP]
    return sorted(words, key=len, reverse=True)[:2] or [path.split("/")[-1][:12].lower()]


def has_article(page, kws):
    if "<title" not in page:
        return False
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)).lower()
    return len(text.split()) > 300 and all(text.count(k) >= 2 for k in kws)


def resolve(path, before):
    cdx = get(f"https://web.archive.org/cdx/search/cdx?url=takeuforward.org/{path}/"
              f"&filter=statuscode:200&fl=timestamp,length&collapse=digest&to={before}")
    rows = [r.split() for r in cdx.splitlines() if r.strip()]
    cands = [ts for ts, ln in rows if ts.isdigit() and ln.isdigit() and int(ln) > 8000][::-1]
    kws = keywords(path)
    for ts in cands[:5]:
        page = get(f"https://web.archive.org/web/{ts}id_/https://takeuforward.org/{path}/")
        if has_article(page, kws):
            return ts
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out", type=Path)
    ap.add_argument("--before", default="20250401")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--seed", action="append", default=[], type=Path,
                    help="Another snapshots.json to reuse resolved paths from (repeatable)")
    args = ap.parse_args()

    paths = article_paths(load_json(args.src))
    result = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    for seed in args.seed:
        if seed.exists():
            known = json.loads(seed.read_text(encoding="utf-8"))
            result.update({p: known[p] for p in paths if not result.get(p) and known.get(p)})
    todo = [p for p in paths if not result.get(p)]
    print(f"{len(paths)} articles, {len(todo)} to resolve", flush=True)

    def work(p):
        try:
            ts = resolve(p, args.before)
        except Exception as e:
            ts = None
            print(f"ERR {p}: {e}", flush=True)
        with lock:
            result[p] = ts
            args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
            done = sum(1 for q in paths if q in result)
            print(f"[{done}/{len(paths)}] {p} -> {ts}", flush=True)

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, todo))
    missing = [p for p in paths if not result.get(p)]
    print(f"done: {len(paths) - len(missing)} resolved, {len(missing)} unresolved", flush=True)
    for p in missing:
        print("  unresolved:", p)


if __name__ == "__main__":
    main()
