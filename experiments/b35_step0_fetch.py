"""B35 step 0: confirm the door, and print what is behind it.

The carrier is one joint production process with two outputs whose anchors sit
on opposite sides of a border: bovine edible offal (HS 0206) against bovine
muscle meat (HS 0201 fresh, 0202 frozen). B35_design section 4 fixes the source
as the US Census international trade API, because it is free, needs no
registration, is monthly, is broken out by destination, and reaches ten digit HS
codes, which is what the composition risk in that section requires.

This step fetches, caches and PRINTS. It computes no unit value trend, takes no
difference and judges nothing. Its whole job is to answer three questions by
showing the object:

  1. Does the endpoint answer at all from this machine.
  2. Which ten digit lines actually exist under 0206, with their own
     descriptions, so the aggregate is never used blind.
  3. What each line's share of the 0206 total is, month by month, because
     B35_design section 4 says a unit value can move purely from the mix.

Caching follows project rule 6: one file per request, resumable, and a cached
file is validated before it is read rather than trusted.

Usage
-----
    python b35_step0_fetch.py --probe
    python b35_step0_fetch.py --years 2016 2022 --cty 5700

Writes into data/b35/ and results/. Deletes nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.census.gov/data/timeseries/intltrade/exports/hs"
KEY_SIGNUP = "https://api.census.gov/data/key_signup.html"
KEY_ENV = "CENSUS_API_KEY"
KEY_FILE = "census_key.txt"   # inside data/b35/, and gitignored


def read_key(explicit, cache_root):
    """Find the API key without ever printing it.

    Order: the flag, then the environment variable, then a one line file inside
    the cache directory. The file lives under data/ and is gitignored, so the
    key never reaches the repository and never reaches a tool result.
    """
    if explicit:
        return explicit, "the --key flag"
    import os
    v = os.environ.get(KEY_ENV)
    if v and v.strip():
        return v, "the %s environment variable" % KEY_ENV
    f = cache_root / KEY_FILE
    if f.exists():
        t = f.read_text(encoding="utf-8")
        if t.strip():
            return t, "data/b35/%s" % KEY_FILE
    return None, None


def key_shape(k, where):
    """Describe the key without revealing it.

    The key cannot be printed, so its structural signature is printed instead.
    A Census key is forty lowercase hex characters. Anything else is visible
    here without the value ever leaving the machine.
    """
    import re
    raw_len = len(k)
    stripped = k.strip()
    bits = []
    bits.append("length %d" % len(stripped))
    if raw_len != len(stripped):
        bits.append("HAD %d stray whitespace characters around it"
                    % (raw_len - len(stripped)))
    if re.fullmatch(r"[0-9a-f]{40}", stripped):
        bits.append("forty lowercase hex, which is the expected shape")
    else:
        cls = []
        if re.search(r"[A-Z]", stripped):
            cls.append("uppercase letters")
        if re.search(r"[^0-9a-zA-Z]", stripped):
            cls.append("characters that are neither letters nor digits")
        if re.search(r"\s", stripped):
            cls.append("whitespace INSIDE it")
        if len(stripped) != 40:
            cls.append("not forty characters")
        bits.append("NOT the expected shape: " + ", ".join(cls or ["unclear"]))
    return "key found in %s: %s" % (where, "; ".join(bits))


def key_help():
    return (
        "IF THE KEY WAS REJECTED RATHER THAN MISSING, check activation first.\n"
        "  A Census key does not expire with age, but it is inactive until the\n"
        "  activation link in the signup email is clicked. A key requested and\n"
        "  then used the next day without that click reads as invalid.\n"
        "  Second most common cause: stray text or whitespace copied with it.\n"
        "  The line above prints the key's shape without printing the key.\n\n"
        "The endpoint requires an API key. It is free and issued immediately.\n"
        "  1. Request one at %s\n"
        "  2. Put it somewhere this script can find it, in this order of\n"
        "     preference, and do NOT paste it into a chat or a commit:\n"
        "       set the environment variable %s\n"
        "       or write it as one line into data/b35/%s\n"
        "  3. Add data/b35/%s to .gitignore before writing it there.\n"
        "This script never prints the key."
        % (KEY_SIGNUP, KEY_ENV, KEY_FILE, KEY_FILE))
GET = ["CTY_NAME", "E_COMMODITY", "E_COMMODITY_LDESC",
       "ALL_VAL_MO", "QTY_1_MO", "UNIT_QY1"]

# Corrected at step 0, see B35_design section 5. HS 0206 is edible offal of
# several species, not of cattle, and 99.8 per cent of it by value to China is
# swine. The offal side is therefore 0206.30 (fresh or chilled) and 0206.49
# (frozen), read one ten digit line at a time. The muscle comparator is NOT an
# export line at all: it is the US domestic hog and pork price, because that is
# where the muscle's substitution class sits. Fetching 0203 here would pair two
# series anchored in the same market, which discriminates nothing.
DEFAULT_HS = ["020630", "020649"]
# Kept so the bovine lines can be re-checked against another destination later,
# but not fetched by default: bovine offal to China is a closed door, not a
# thin series.
BOVINE_HS = ["020621", "020622", "020629"]
CHINA = "5700"


def tag_of(cty):
    """Name the destination setting for a filename.

    Three settings, three names, and they must not share a file. Without a
    CTY_CODE predicate the feed returns one aggregate row per commodity-month
    named TOTAL FOR ALL COUNTRIES, carrying value but no quantity at all
    (QTY_1_MO is "0" and UNIT_QY1 is "-"). With CTY_CODE=* it returns one row
    per destination. Those are different objects, so an earlier run under the
    old shared name is left where it is and simply never read again.
    """
    if cty == "*":
        return "bycountry"
    if not cty:
        return "total"
    return str(cty)


def cache_path(root: Path, hs, year, month, cty, level):
    return root / ("%s_%s_%02d_%s_%s.json"
                   % (hs, year, month, tag_of(cty), level))


def load_cached(p: Path):
    """Return the parsed rows, or None if absent or damaged.

    Rule 6: a truncated or corrupt cache file must be recognised, not read in
    silently. A file that does not parse, or that is not a list of lists with a
    header, is treated as absent and refetched.
    """
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("   cache damaged, will refetch: %s (%s)" % (p.name, e))
        return None
    if not isinstance(d, list) or not d or not isinstance(d[0], list):
        print("   cache malformed, will refetch: %s" % p.name)
        return None
    return d


def fetch(hs, year, month, cty, level, root: Path, key=None, pause=0.4):
    p = cache_path(root, hs, year, month, cty, level)
    got = load_cached(p)
    if got is not None:
        return got, True
    q = {"get": ",".join(GET), "YEAR": str(year), "MONTH": "%02d" % month,
         "COMM_LVL": level, "E_COMMODITY": hs + "*"}
    if cty:
        q["CTY_CODE"] = cty
    if key:
        q["key"] = key
    url = BASE + "?" + urllib.parse.urlencode(q)
    # A dropped connection is not the same thing as no egress. WinError 10054,
    # "an existing connection was forcibly closed", turned up part way through a
    # 264 cell run on a machine where the previous 264 cell run had completed,
    # so it is the far end letting go under load, not the network being absent.
    # It is retried. A refusal to resolve or connect is not retried, because
    # waiting does not fix that one.
    raw = None
    last = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                raw = r.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code == 204 or "no data" in body.lower():
                rows = [["_empty"]]
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(rows), encoding="utf-8")
                return rows, False
            if e.code in (429, 500, 502, 503, 504):
                wait = 5 * (2 ** attempt)
                print("   HTTP %s on %s %s-%02d, waiting %ds (try %d of 5)"
                      % (e.code, hs, year, month, wait, attempt + 1))
                time.sleep(wait)
                last = "HTTP %s, body: %s" % (e.code, body)
                continue
            raise SystemExit("HTTP %s from the API.\n  url: %s\n  body: %s"
                             % (e.code, url, body))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            reason = getattr(e, "reason", e)
            text = str(reason)
            hard = any(k in text.lower() for k in
                       ("name or service", "getaddrinfo", "nodename",
                        "temporary failure in name resolution",
                        "connection refused", "certificate"))
            if hard:
                raise SystemExit(
                    "could not reach api.census.gov: %s\n"
                    "This looks like name resolution or a refusal, which is the\n"
                    "machine's egress and not this script. Run it somewhere with\n"
                    "outbound access and bring the cache across." % e)
            wait = 5 * (2 ** attempt)
            print("   connection dropped on %s %s-%02d (%s), waiting %ds "
                  "(try %d of 5)" % (hs, year, month, text, wait, attempt + 1))
            time.sleep(wait)
            last = text
            continue
    if raw is None:
        raise SystemExit(
            "gave up on %s %s-%02d after five tries. Last: %s\n"
            "Everything fetched so far is in the cache, so re-running picks up\n"
            "where this stopped. A missing month would make that year's total\n"
            "wrong, so the run stops rather than carrying a hole."
            % (hs, year, month, last))
    # An empty body is the API's way of saying this cell has no trade. That is
    # a reading, not a failure: a ten digit line that is empty for every month
    # tells us the lane does not exist. It is cached as empty and the run goes
    # on, per rule 6, rather than stopping the whole fetch.
    if not raw.strip():
        rows = [["_empty"]]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rows), encoding="utf-8")
        time.sleep(pause)
        return rows, False
    try:
        rows = json.loads(raw)
    except Exception:
        head = raw.lstrip()[:400].lower()
        if "missing key" in head or "invalid key" in head or "<html" in head:
            what = ("MISSING KEY" if "missing key" in head else
                    "INVALID KEY" if "invalid key" in head else
                    "an HTML page rather than data")
            raise SystemExit(
                "the endpoint answered with %s.\n\n%s" % (what, key_help()))
        raise SystemExit("the endpoint answered but not with JSON:\n%s" % raw[:400])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rows), encoding="utf-8")
    time.sleep(pause)
    return rows, False


def to_dicts(rows):
    if not rows or rows[0] == ["_empty"]:
        return []
    head = rows[0]
    return [dict(zip(head, r)) for r in rows[1:]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true",
                    help="one month, everything printed; use this first")
    ap.add_argument("--years", nargs=2, type=int, default=None,
                    metavar=("FROM", "TO"))
    ap.add_argument("--hs", nargs="*", default=DEFAULT_HS)
    ap.add_argument("--cty", default=CHINA,
                    help="5700 is China; 'all' is one row per destination; "
                         "'total' is the all-countries aggregate, which has "
                         "no quantity")
    ap.add_argument("--probe-dest", action="store_true",
                    help="fetch one month and report whether the destination "
                         "breakdown and the quantities are actually there")
    ap.add_argument("--level", default="HS10", choices=["HS6", "HS10"])
    ap.add_argument("--quota-kg", type=float, default=None,
                    help="if given, print monthly and cumulative quantity per "
                         "year against this figure. B36 uses 1.64e8 for the US "
                         "2026 beef allocation of 164,000 metric tons")
    ap.add_argument("--key", default=None,
                    help="Census API key; prefer the %s environment variable or "
                         "data/b35/%s so it never lands in shell history"
                         % (KEY_ENV, KEY_FILE))
    args = ap.parse_args()

    # Three settings, and the difference between the first two is the whole of
    # B36-5. "all" means one row per destination, which needs the CTY_CODE=*
    # predicate; with no predicate at all the feed silently hands back a single
    # aggregate row per commodity-month, carrying value and no quantity.
    # Windows PowerShell eats a bare empty argument, so neither is spelled "".
    _c = (args.cty or "").strip().lower()
    if _c in ("all", "each", "bycountry", "*"):
        args.cty = "*"
    elif _c in ("total", "world", "none", "-", ""):
        args.cty = ""
    print("destination setting: %s" % {
        "*": "CTY_CODE=*, one row per destination",
        "": "no predicate, ONE AGGREGATE ROW per commodity-month. At HS6 "
            "that row carried no quantity; at HS10 it has not been checked",
    }.get(args.cty, "CTY_CODE=%s, that one destination" % args.cty))

    root = Path(__file__).resolve().parent.parent
    cache = root / "data" / "b35"
    out = root / "results"
    cache.mkdir(parents=True, exist_ok=True)

    key, where = read_key(args.key, cache)
    if key:
        print(key_shape(key, where))
        key = key.strip()
    if not key:
        print("=" * 74)
        print("no API key found, and this endpoint needs one")
        print("=" * 74)
        print(key_help())
        return 2
    args.key = key

    if args.probe_dest:
        # Placed after the key is resolved, because it needs one, and after the
        # paths exist, because it writes to the cache. The first version sat
        # directly under parse_args and reached for both before either was
        # bound.
        if not args.years:
            print("--probe-dest needs --years, one year is enough")
            return 2
        hs = args.hs[0]
        y, m = args.years[0], 6
        rows, cached = fetch(hs, y, m, args.cty, args.level, cache, args.key)
        recs = to_dicts(rows)
        names = sorted({(r.get("CTY_NAME") or "").strip() for r in recs})
        withq = [r for r in recs
                 if str(r.get("QTY_1_MO") or "0") not in ("0", "", "-")]
        units = sorted({(r.get("UNIT_QY1") or "").strip() for r in recs})
        print("\nprobe on %s %d-%02d, level %s, %s"
              % (hs, y, m, args.level, "from cache" if cached else "fetched"))
        print("  rows                : %d" % len(recs))
        print("  distinct CTY_NAME   : %d" % len(names))
        print("  first eight names   : %s" % names[:8])
        print("  rows with a quantity: %d of %d" % (len(withq), len(recs)))
        print("  quantity units seen : %s" % units)
        if len(names) <= 1 or not withq:
            print("\n  This is not a destination breakdown with quantities. "
                  "Nothing else is fetched. Read the lines above before "
                  "changing anything.")
        else:
            print("\n  Destination breakdown with quantities is present. "
                  "Re-run without --probe-dest.")
        return


    if args.probe or not args.years:
        print("=" * 74)
        print("PROBE: swine offal frozen (020649) to destination %s, June 2019, %s"
              % (args.cty, args.level))
        print("=" * 74)
        rows, cached = fetch("020649", 2019, 6, args.cty, args.level, cache, args.key)
        recs = to_dicts(rows)
        if not recs:
            print("the endpoint answered and returned no rows for this cell.")
            print("that is information: try HS6, or another month, before")
            print("concluding anything about the door.")
            return
        print("%s   %d rows" % ("from cache" if cached else "fetched", len(recs)))
        tot = sum(float(r["ALL_VAL_MO"]) for r in recs if r["ALL_VAL_MO"])
        print("\n%-12s %-14s %-9s %-5s %7s  %s"
              % ("HS", "value", "qty", "unit", "share", "description"))
        for r in sorted(recs, key=lambda d: -float(d["ALL_VAL_MO"] or 0)):
            v = float(r["ALL_VAL_MO"] or 0)
            q = float(r["QTY_1_MO"] or 0)
            print("%-12s %-14.0f %-9.0f %-5s %6.1f%%  %s"
                  % (r["E_COMMODITY"], v, q, r.get("UNIT_QY1", ""),
                     100 * v / tot if tot else 0,
                     (r.get("E_COMMODITY_LDESC") or "")[:52]))
            if q:
                print("%-12s   unit value = %.4f per %s"
                      % ("", v / q, r.get("UNIT_QY1", "?")))
        print("\ndestination as the API names it: %s"
              % recs[0].get("CTY_NAME", "?"))
        print("\nPROBE ends. The door is open and the ten digit lines above are")
        print("what B35_design section 4 requires be handled one at a time.")
        print("Nothing has been computed.")
        return

    y0, y1 = args.years
    print("fetching %s, %s to %s, destination %s, level %s"
          % (", ".join(args.hs), y0, y1, args.cty, args.level))
    n_new = n_cached = 0
    allrecs = []
    empty = {}
    for hs in args.hs:
        for y in range(y0, y1 + 1):
            for m in range(1, 13):
                rows, cached = fetch(hs, y, m, args.cty, args.level, cache, args.key)
                n_cached += cached
                n_new += (not cached)
                recs = to_dicts(rows)
                if not recs:
                    empty.setdefault(hs, []).append("%04d-%02d" % (y, m))
                for r in recs:
                    r["_year"], r["_month"], r["_hs_head"] = y, m, hs
                    allrecs.append(r)
            print("  %s %s done" % (hs, y))
    print("\ncells: %d from cache, %d fetched, %d rows total"
          % (n_cached, n_new, len(allrecs)))

    # An HS head that is empty in every month is a finding about the lane, so it
    # is named rather than passed over.
    months = (y1 - y0 + 1) * 12
    for hs in args.hs:
        n_empty = len(empty.get(hs, []))
        if n_empty == months:
            print("  %s: EMPTY IN ALL %d MONTHS. This lane does not exist to "
                  "this destination; it is a reading, not a gap." % (hs, months))
        elif n_empty:
            print("  %s: %d of %d months empty, first %s, last %s"
                  % (hs, n_empty, months, empty[hs][0], empty[hs][-1]))
        else:
            print("  %s: every month has data" % hs)
    if not allrecs:
        print("\nnothing at all came back. Re-check the HS heads against the")
        print("probe output before assuming the fetch is broken.")
        return

    out.mkdir(parents=True, exist_ok=True)
    # Name the record by what is in it. Two runs with different HS heads or a
    # different destination used to write the same file, and the second silently
    # replaced the first. Same shape as the B34 step three overwrite.
    tag = "-".join(args.hs) + "_" + tag_of(args.cty)
    p = out / ("b35_census_raw_%s.json" % tag)
    p.write_text(json.dumps(allrecs, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written: %s" % p)

    # The mix, printed. Design section 4: a unit value can move on mix alone.
    print("\n" + "=" * 74)
    print("the composition of the swine offal family, share of monthly value")
    print("=" * 74)
    lines = sorted({r["E_COMMODITY"] for r in allrecs})
    desc = {r["E_COMMODITY"]: (r.get("E_COMMODITY_LDESC") or "")[:40]
            for r in allrecs}
    for ln in lines:
        print("  %-12s %s" % (ln, desc.get(ln, "")))
    print("\n  %-8s %s" % ("month", " ".join("%11s" % l[-6:] for l in lines)))
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            cell = {r["E_COMMODITY"]: float(r["ALL_VAL_MO"] or 0)
                    for r in allrecs
                    if r["_year"] == y and r["_month"] == m}
            tot = sum(cell.values())
            if not tot:
                continue
            print("  %04d-%02d %s" % (y, m,
                  " ".join("%10.1f%%" % (100 * cell.get(l, 0) / tot)
                           for l in lines)))
    if args.quota_kg:
        print("\n" + "=" * 74)
        print("quantity against the published line: %.0f kg (%.0f metric tons)"
              % (args.quota_kg, args.quota_kg / 1000.0))
        print("=" * 74)
        print("  %-8s %14s %14s %8s" % ("month", "qty kg", "cumulative", "of line"))
        for y in range(y0, y1 + 1):
            cum = 0.0
            any_row = False
            for m in range(1, 13):
                q = sum(float(r["QTY_1_MO"] or 0) for r in allrecs
                        if r["_year"] == y and r["_month"] == m)
                if q == 0 and not any_row:
                    continue
                any_row = True
                cum += q
                print("  %04d-%02d %14.0f %14.0f %7.1f%%"
                      % (y, m, q, cum, 100 * cum / args.quota_kg))
            if any_row:
                print("  %-8s %14s %14.0f %7.1f%%   <- year end"
                      % (y, "", cum, 100 * cum / args.quota_kg))
        print("\nB36-0 reads this table and nothing else. A cumulative that")
        print("stays far below the line means the line does not bite for this")
        print("source, which is a reading, not a failure.")

    print("\nStep 0 ends here. No unit value series has been built and nothing")
    print("has been judged. Read the mix above before step 1 is written.")


if __name__ == "__main__":
    sys.exit(main())
