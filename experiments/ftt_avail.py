"""Availability probe for the Italian FTT carrier. Free endpoints only.

PRE-STATION. This file has no stage number on purpose: the station is not open.
Gate zero (D18) has not been run, and the line this file sits on is the one
carrier selection draws: an availability note measures whether a registered
domain is REACHABLE, and it does not choose the domain. Nothing here
registers a prediction or reads one.

WHY THIS CARRIER IS BEING PRICED AT ALL

B16 (Section 31) closed on power, not on sign: the fee moves the friction half by
0.9% while the friction half's own 10-day variation is 17%, and the registered
cross-sectional regression that was meant to separate them missed by 13-15x. The
Italian FTT's 2026-01-01 doubling is the same SHAPE of instrument — ad valorem,
so relatively identical across venues by construction — at 1000e-6 against
Section 31's largest 27.8e-6, which is 36 times larger. Tolerance scales with the
instrument and the noise does not, so the arithmetic that killed B16 is the
arithmetic that recommends this one.

    events, all venue-symmetric by the statute's own drafting
      2013-03-01   introduction, transitional rates 0.12% / 0.22%
      2014-01-01   step down to the standing 0.10% / 0.20%
      2026-01-01   doubling to 0.20% / 0.40%   (L. 199/2025 art.1 c.29-31)

    the two classes
      Euronext Milan (Borsa Italiana, IT)  against the MTFs, all EU-domiciled:
      Cboe DXE/CEUX (NL), Turquoise TQEX (NL), Aquis AQEU (FR),
      Equiduct (DE), SIGMA X Europe (FR)

WHAT THIS FILE CANNOT DO

It cannot buy. The only endpoints it names are metadata endpoints, and the
selftest walks its own AST to require that the set of endpoint literals equals
the free whitelist exactly. b16_cost.py uses the same construction and for the
same reason: the file that can spend money should be a different file.

    python experiments/ftt_avail.py --selftest    no network
    python experiments/ftt_avail.py --datasets    free, every dataset and range
    python experiments/ftt_avail.py --europe      free, the European ones only
    python experiments/ftt_avail.py --cost        free, quotes one sample month
"""
import argparse
import ast
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(RESULTS, "ftt_availability.json")

API = "https://hist.databento.com/v0"
FREE_ENDPOINTS = ("metadata.list_datasets", "metadata.get_dataset_range",
                  "metadata.get_cost", "metadata.get_billable_size")

#: Anything a European venue code might contain. Deliberately loose: the point is
#: to see the whole catalogue, not to confirm a guess. D12, enumerate then choose.
EU_HINTS = ("XMIL", "MTAA", "EURONEXT", "XPAR", "XAMS", "XBRU", "XLIS", "XLON",
            "CHIX", "BATE", "CEUX", "DXE", "TRQX", "TQEX", "AQEU", "AQXE",
            "EQTA", "EQTB", "XETR", "XSWX", "EUR", "EU.", "ICE", "OPRA")

#: One sample request, used only to get a quote. Six FTSE MIB names that also
#: quote on the MTFs. Not a universe: the screen is a later step and it is not
#: this file's business.
SAMPLE_SYMBOLS = ("ENEL", "ENI", "ISP", "UCG", "STLAM", "RACE")
SAMPLE_START = "2025-12-15"
SAMPLE_END = "2026-01-16"
SAMPLE_SCHEMA = "bbo-1s"


def api_key():
    k = os.environ.get("DATABENTO_API_KEY")
    if k:
        return k.strip()
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env, encoding="utf-8"):
            line = line.strip()
            if line.startswith("DATABENTO_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DATABENTO_API_KEY; nothing was requested")


def call(endpoint, params, key, method="POST"):
    """Copied from b16_cost.py rather than rewritten.

    The catalogue endpoints do not accept POST: metadata.list_datasets returns
    HTTP 405 Method Not Allowed for a POST body. get_cost and get_billable_size
    do accept POST. b16_cost.py already carried that distinction and this file
    was written from scratch instead of from it, which cost one round trip.
    """
    url = API + "/" + endpoint
    data = urllib.parse.urlencode(params, doseq=True).encode() if params else None
    if method == "GET":
        url = url + ("?" + data.decode() if data else "")
        data = None
    req = urllib.request.Request(url, data=data)
    req.add_header("Authorization",
                   "Basic " + base64.b64encode((key + ":").encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code,
                "body": e.read().decode("utf-8", "replace")[:600]}
    except Exception as ex:                                          # noqa: BLE001
        return {"http_error": "?", "body": "%s: %s" % (type(ex).__name__, ex)}


def datasets(key, europe_only=False):
    ds = call("metadata.list_datasets", {}, key, method="GET")
    if isinstance(ds, dict):
        print("  list_datasets failed http %s  %s"
              % (ds.get("http_error"), str(ds.get("body"))[:200]))
        return 1
    print("  %d datasets in the catalogue\n" % len(ds))
    rows = []
    for d in sorted(ds):
        hit = any(h in d.upper() for h in EU_HINTS)
        if europe_only and not hit:
            continue
        rng = call("metadata.get_dataset_range", {"dataset": d}, key,
                   method="GET")
        if isinstance(rng, dict) and "http_error" in rng:
            lo = hi = "?"
        else:
            lo = (rng or {}).get("start", "?")[:10]
            hi = (rng or {}).get("end", "?")[:10]
        rows.append({"dataset": d, "start": lo, "end": hi, "eu_hint": hit})
        print("  %-22s %s .. %s%s" % (d, lo, hi, "   <- EU hint" if hit else ""))
    os.makedirs(RESULTS, exist_ok=True)
    json.dump({"datasets": rows, "eu_hints": list(EU_HINTS)},
              open(OUT, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(OUT, ROOT))
    if not any(r["eu_hint"] for r in rows):
        print("\n  NO European equity dataset in this vendor's catalogue.")
        print("  That is a finding, not a failure: it means the carrier needs a")
        print("  different vendor (bigxyt, BMLL, LSEG Tick History, Cboe Europe")
        print("  historical, Euronext market data), and those are quoted by")
        print("  sales rather than by an endpoint.")
    return 0


def cost(key):
    if not os.path.exists(OUT):
        print("  run --datasets first; this needs the catalogue")
        return 1
    rows = json.load(open(OUT, encoding="utf-8"))["datasets"]
    cands = [r["dataset"] for r in rows if r["eu_hint"]
             and r["start"] != "?" and r["start"] <= SAMPLE_START
             and r["end"] >= SAMPLE_END]
    if not cands:
        print("  no European dataset covers %s .. %s" % (SAMPLE_START, SAMPLE_END))
        print("  nothing to quote. See the note under --datasets.")
        return 0
    print("  quoting %d candidate dataset(s), %d symbols, %s, %s .. %s\n"
          % (len(cands), len(SAMPLE_SYMBOLS), SAMPLE_SCHEMA,
             SAMPLE_START, SAMPLE_END))
    for d in cands:
        p = {"dataset": d, "symbols": ",".join(SAMPLE_SYMBOLS),
             "schema": SAMPLE_SCHEMA, "start": SAMPLE_START, "end": SAMPLE_END,
             "stype_in": "raw_symbol", "mode": "historical"}
        c = call("metadata.get_cost", p, key)
        z = call("metadata.get_billable_size", p, key)
        if isinstance(c, dict):
            detail = ""
            try:
                detail = json.loads(c["body"])["detail"]["case"]
            except Exception:                                       # noqa: BLE001
                detail = str(c.get("body", ""))[:120]
            print("  %-22s REFUSED http %s  %s" % (d, c.get("http_error"), detail))
            continue
        gb = 0 if isinstance(z, dict) else int(z) / 1e9
        print("  %-22s $%.4f   %.2f GB   (six names, one month)" % (d, float(c), gb))
        print("      x %d names / 6 x %d events -> rough station total"
              % (60, 3))
        print("      $%.2f for 60 names across 3 events" % (float(c) * 10 * 3))
    print("\n  nothing was bought. This file has no download path.")
    return 0


def _endpoints():
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    seen = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "call" \
                and n.args and isinstance(n.args[0], ast.Constant):
            seen.add(n.args[0].value)
    return seen


def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    eps = _endpoints()
    chk("1  the endpoint set is exactly the free four: %s" % sorted(eps),
        eps == set(FREE_ENDPOINTS))
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.Name):
            names.add(n.id)
    chk("2  no download path: no urlretrieve, copyfileobj, get_range or"
        " submit_job anywhere",
        not (names & {"urlretrieve", "copyfileobj", "get_range", "submit_job"}))
    calls = {getattr(c.func, "attr", None) for c in ast.walk(tree)
             if isinstance(c, ast.Call)}
    chk("3  nothing here deletes anything", not ({"remove", "unlink", "rmtree",
                                                  "rmdir"} & calls))
    chk("4  the file carries no stage number: the station is not open and gate"
        " zero (D18) has not been run",
        os.path.basename(__file__).startswith("ftt_"))
    #: The check that was missing. Walk the call sites and require the two
    #: catalogue endpoints to carry method="GET"; a POST there is a 405.
    getters = {"metadata.list_datasets", "metadata.get_dataset_range"}
    seen_get = set()
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and getattr(n.func, "id", None) == "call"):
            continue
        if not (n.args and isinstance(n.args[0], ast.Constant)):
            continue
        ep = n.args[0].value
        m = None
        for kw in n.keywords:
            if kw.arg == "method" and isinstance(kw.value, ast.Constant):
                m = kw.value.value
        if ep in getters and m == "GET":
            seen_get.add(ep)
    chk("5  both catalogue endpoints are called with method=GET; a POST there"
        " returns 405 (found %s)" % sorted(seen_get), seen_get == getters)
    chk("6  the sample window brackets the 2026-01-01 event on both sides",
        SAMPLE_START < "2026-01-01" < SAMPLE_END)
    chk("7  the EU hint list is a superset, not a guess at one venue (D12,"
        " enumerate before choosing): %d codes" % len(EU_HINTS),
        len(EU_HINTS) >= 15)
    print("\nselftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--datasets", action="store_true")
    ap.add_argument("--europe", action="store_true")
    ap.add_argument("--cost", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.datasets:
        return datasets(api_key())
    if a.europe:
        return datasets(api_key(), europe_only=True)
    if a.cost:
        return cost(api_key())
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
