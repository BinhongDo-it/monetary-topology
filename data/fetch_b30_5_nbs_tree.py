"""B30-5 carrier validation, step A: enumerate the indicator tree. Fetches no data.

The question this whole validation answers is whether the crowdsourced panel in
``data/b30_5/panel.json`` measures a cross-city price *level* at all. The only
class in that panel with an authoritative counterpart is housing, and the
counterpart is the average residential selling price published per region by the
statistics bureau, which the bureau itself describes as an absolute quantity
suitable for comparison across regions against local income -- that is, against
the same right-hand side B30-5 regresses on.

This step exists because the indicator code is not guessable, and guessing is how
a fetcher ends up silently pulling a neighbouring series. Take the codelist,
print the whole set, then choose. Nothing here selects anything.

Run:
    python data\\fetch_b30_5_nbs_tree.py
    python data\\fetch_b30_5_nbs_tree.py --grep 价格
    python data\\fetch_b30_5_nbs_tree.py --insecure     # only if TLS fails
"""

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Every indicator name on this host is Chinese, and a Windows console is cp936,
# so the final print is where this script would die -- after every request has
# already been paid for. Pin the stream instead of discovering it at the end.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HOST = "https://data.stats.gov.cn/easyquery.htm"
# fsnd = annual by province. csnd = annual by city, a much thinner indicator
# set. Which one holds the price series is exactly what this step is for, so
# both are walked rather than assumed.
DBCODES = ["fsnd", "csnd"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CACHE = Path(__file__).resolve().parents[1] / "data" / "b30_5" / "nbs"


def fetch(params, insecure=False):
    url = HOST + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://data.stats.gov.cn/easyquery.htm?cn=C01",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    })
    ctx = None
    if insecure:
        # Never silent. This host has had certificate trouble for years, but a
        # fetcher that quietly stops verifying is a fetcher that cannot say
        # where its numbers came from, which is the shape of failure mode 119.
        # So it is opt-in, announced on stdout, and recorded in the output.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        raw = r.read().decode("utf-8", "replace")
    return json.loads(raw)


def get_tree(dbcode, node, insecure=False):
    return fetch({"m": "getTree", "dbcode": dbcode, "wdcode": "zb",
                  "id": node, "k1": str(int(time.time() * 1000))}, insecure)


def walk(dbcode, root, insecure, depth=0, seen=None, out=None, maxdepth=4):
    seen = set() if seen is None else seen
    out = [] if out is None else out
    if root in seen or depth > maxdepth:
        return out
    seen.add(root)
    try:
        nodes = get_tree(dbcode, root, insecure)
    except Exception as e:
        print("  ! %s %s: %s" % (dbcode, root, str(e)[:80]))
        return out
    for n in nodes if isinstance(nodes, list) else []:
        code, name, isp = n.get("id"), n.get("name"), n.get("isParent")
        out.append({"db": dbcode, "code": code, "name": name,
                    "depth": depth, "parent": root, "is_parent": bool(isp)})
        if isp:
            time.sleep(0.4)
            walk(dbcode, code, insecure, depth + 1, seen, out, maxdepth)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--grep", default=None)
    a = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    if a.insecure:
        print("TLS verification is OFF for this run, by request. It is "
              "recorded in the output file.\n")

    allnodes = []
    for db in DBCODES:
        print("=" * 74)
        print("database %s" % db)
        print("=" * 74)
        try:
            roots = get_tree(db, "zb", a.insecure)
        except Exception as e:
            print("  cannot reach the host: %s" % str(e)[:140])
            print("  If that is a certificate error, re-run with --insecure "
                  "and the output will say so.")
            continue
        for r in roots if isinstance(roots, list) else []:
            print("  %-10s %s" % (r.get("id"), r.get("name")))
        for r in roots if isinstance(roots, list) else []:
            allnodes.extend(walk(db, r.get("id"), a.insecure, 1))
            time.sleep(0.4)

    if not allnodes:
        raise SystemExit("\nnothing enumerated. Nothing is chosen and nothing "
                         "is written.")

    pat = re.compile(a.grep) if a.grep else re.compile("价格")
    print("\n" + "=" * 74)
    print("leaf indicators whose name matches %s" % pat.pattern)
    print("=" * 74)
    hits = [n for n in allnodes
            if not n["is_parent"] and pat.search(n["name"] or "")]
    for n in hits:
        print("  %-6s %-12s %s" % (n["db"], n["code"], n["name"]))
    print("\n%d nodes enumerated, %d leaves match. Nothing selected here."
          % (len(allnodes), len(hits)))

    p = CACHE / "indicator_tree.json"
    p.write_text(json.dumps(
        {"tls": "unverified" if a.insecure else "verified",
         "nodes": allnodes}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("full tree written to %s" % p)


if __name__ == "__main__":
    main()
