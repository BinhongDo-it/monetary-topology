"""Fetch Agmarknet arrivals from the Agmarknet 2.0 JSON API.

The old SearchCmmMkt.aspx endpoint is gone; the site is a single-page app now and
its data comes from

    GET https://api.agmarknet.gov.in/v1/prices-and-arrivals/date-wise/specific-commodity
        ?year=YYYY&month=MM&includeExcel=false&stateId=<id>&commodityId=<id>

captured from the site's own form. The response is

    { success, message, title, columns,
      markets: [ { marketName, dates: [ { arrivalDate, total_arrivals, data: [...] } ] } ] }

so `markets` is the support set for that (commodity, state, month): a list of the
markets that had a positive arrival. `title` names the commodity and the state,
which is how this script checks it asked for what it thinks it asked for.

Three facts this script is built around, each measured rather than assumed:
  - one state and one month per request; stateId=0 returns nothing, and omitting
    stateId or month is a 500, so neither dimension can be collapsed;
  - includeExcel=true returns a real xlsx for the same single cell, so it buys
    no coverage;
  - the endpoint rate-limits. Ten concurrent requests got 19 of 200 answered and
    left even serial requests failing for a while afterwards. Serial with a
    delay, and back off hard on failure.

Order of work: `--phase states` finds, per commodity, which states actually
trade it, so the main pull skips the empty ones. `--phase pull` then walks only
those pairs over each commodity's own window.

Nothing is ever deleted. A file that fails its check is renamed .corrupt_<ts>.
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "agmark" / "api"
SCOPE = OUT / "state_scope.json"
COSTFILE = OUT / "request_cost.json"
BASE = "https://api.agmarknet.gov.in/v1/prices-and-arrivals/date-wise/specific-commodity"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# The portal renumbered its commodities: the low ids carried over from the legacy
# table (1=Wheat, 2=Paddy(Common), ...) but the high ones did not -- 311 is
# Gladiolus Bulb here, not Sponge gourd. So nothing is keyed by id any more.
# Each entry is (name fragment as the portal spells it, first month, last month),
# and the id is looked up in commodity_map.json, which --phase map builds by
# asking the portal what each id is called.
TREATED = [
    # cohort A
    ("Aloe Vera", "2017-01", "2026-08"),
    ("Arrowroot", "2017-01", "2026-08"),
    ("Avocado", "2017-01", "2026-08"),
    ("Bilimbi", "2017-01", "2026-08"),
    ("Bread Fruit", "2017-01", "2026-08"),   # eNAM: Breadfruit
    ("Chakhao(Black Rice)", "2017-01", "2026-08"),   # eNAM: Chakhao Or Black Rice
    ("Chironji", "2017-01", "2026-08"),
    ("Chrysanthemum(Loose)", "2017-01", "2026-08"),
    ("Chrysanthemum", "2017-01", "2026-08"),   # id 331, the bare name; the outcome is the union of the two codes   # eNAM: Chrysanthemum
    ("Garcinia", "2017-01", "2026-08"),
    ("Gerbera", "2017-01", "2026-08"),
    ("Gherkin", "2017-01", "2026-08"),
    ("Ginger Seed", "2017-01", "2026-08"),
    ("Hilsa", "2017-01", "2026-08"),
    ("Jackfruit Seed", "2017-01", "2026-08"),   # eNAM: Jack Fruit Seed
    ("Lesser Yam", "2017-01", "2026-08"),   # eNAM: Lesser yam
    ("Mangosteen", "2017-01", "2026-08"),
    ("Passion Fruit", "2017-01", "2026-08"),
    ("Rambutan", "2017-01", "2026-08"),
    ("Round Chilli", "2017-01", "2026-08"),   # eNAM: Round chilli
    ("Soursop", "2017-01", "2026-08"),
    ("Sponge gourd", "2017-01", "2026-08"),   # eNAM: Sponge Gourd
    ("Sugar Snap Peas", "2017-01", "2026-08"),
    ("Tulip", "2017-01", "2026-08"),
    # cohort B
    ("Banana stem", "2017-01", "2026-08"),   # eNAM: Banana Stem
    ("Barnyard Millet", "2017-01", "2026-08"),
    ("Browntop Millet", "2017-01", "2026-08"),
    ("Foxtail Millet(Navane)", "2017-01", "2026-08"),   # eNAM: Foxtail Millet
    ("Khandsari(Desi Khand)", "2017-01", "2026-08"),   # eNAM: Khandsari
    ("Kiwi Fruit", "2017-01", "2026-08"),   # eNAM: Kiwi
    ("Kodo Millet(Varagu)", "2017-01", "2026-08"),   # eNAM: Kodo Millet
    ("Little Millet", "2017-01", "2026-08"),
    ("Pine Nut(Chilgoza /Niyoza)", "2017-01", "2026-08"),   # eNAM: Pinenut
    ("Proso Millet", "2017-01", "2026-08"),
    ("Silk Cocoon", "2017-01", "2026-08"),
    ("Snow Mountain Garlic", "2017-01", "2026-08"),
    # cohort 2025-02-06
    ("Gramflour", "2017-01", "2026-08"),   # eNAM: Besan
    ("Wheat Atta", "2017-01", "2026-08"),   # eNAM: Wheat Flour
    ("Water chestnut", "2017-01", "2026-08"),   # eNAM: Water Chestnut
    ("Baby Corn", "2017-01", "2026-08"),
    ("Dragon fruit", "2017-01", "2026-08"),   # eNAM: Dragon Fruit
    # cohort 2025-10-08
    ("Green Tea", "2017-01", "2026-08"),
    ("Tea", "2017-01", "2026-08"),
    ("Ashwagandha", "2017-01", "2026-08"),   # eNAM: Aswagandha Dry Roots
    ("Mustard Oil", "2017-01", "2026-08"),
    ("Mentha Oil", "2017-01", "2026-08"),
    ("Broken Rice", "2017-01", "2026-08"),
]
# A state reports to the portal at its own discretion, and a state that stops
# reporting looks exactly like a support set that contracted -- which is the very
# thing this station is trying to read. So a basket of commodities that every
# reporting state carries is pulled alongside, and its market count per state and
# month is the state's reporting base. The treated series is read against it.
REFERENCE = ["Onion", "Potato", "Tomato", "Wheat", "Paddy(Common)"]
MAP = OUT / "commodity_map.json"
MAX_COMMODITY_ID = 900   # 600 was the scan's own ceiling, not the master's end
# The state scan asks several months, not one. A thin commodity can be blank in a
# given month everywhere and still have a series: Kodo Millet reports in exactly
# one state, Foxtail Millet in two, and a single off-season month would read both
# as dead. Months are spread across the year for that reason.
PROBE_MONTHS = [("2025", "01"), ("2024", "07"), ("2024", "11")]
PROBE_MONTH = PROBE_MONTHS[0]          # --phase probe and --phase map use just one
# A first pass over all states in month one is enough when it finds a few states.
# When it finds this many or fewer, the other months are asked as well, over the
# states that came back empty, before the commodity is called dead.
THIN_ENOUGH_TO_RECHECK = 2
MAX_STATE_ID = 36        # 37..40 come back N/A; measured, not assumed


def months(a, b):
    y0, m0 = (int(x) for x in a.split("-"))
    y1, m1 = (int(x) for x in b.split("-"))
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield "%04d" % y, "%02d" % m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def get(year, month, state_id, commodity_id, timeout=60):
    q = urllib.parse.urlencode({"year": year, "month": month, "includeExcel": "false",
                                "stateId": state_id, "commodityId": commodity_id})
    req = urllib.request.Request(BASE + "?" + q, headers={"User-Agent": UA,
                                                          "Accept": "application/json",
                                                          "Referer": "https://agmarknet.gov.in/"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def names_from_title(j):
    """-> (commodity, state) as the server itself reports them"""
    t = str(j.get("title") or "")
    c = s = None
    if "Commodity :" in t:
        c = t.split("Commodity :", 1)[1].split(",")[0].strip()
    if "State/UT :" in t:
        s = t.split("State/UT :", 1)[1].split(",")[0].strip()
    return c, s


# Two different failures wear the same 500. A burst really does get throttled, and
# that wants a long wait; a single 500 in a serial walk is the server twitching,
# and paying 101 seconds for it is how an hour turns into three. Short waits, few
# tries, and the caller decides whether a miss is fatal or just unknown for now.
BACKOFF = [3, 9]


def polite(fn, sleep, waits=None):
    """serial only. never call this from more than one thread."""
    waits = BACKOFF if waits is None else waits
    for k in range(len(waits) + 1):
        try:
            out = fn()
            time.sleep(sleep)
            return out
        except Exception as e:
            code = getattr(e, "code", None)
            if k == len(waits):
                raise
            print("      retry %d after %s (%s), waiting %ds"
                  % (k + 1, type(e).__name__, code, waits[k]))
            time.sleep(waits[k])
    return None


def phase_states(sleep):
    """which states actually trade each treated commodity, asked over several months"""
    OUT.mkdir(parents=True, exist_ok=True)
    scope = json.loads(SCOPE.read_text(encoding="utf-8")) if SCOPE.exists() else {}
    todo = dict(resolve())
    ref = resolve_names(REFERENCE)
    for cid, nm in ref.items():
        todo.setdefault(cid, (nm, None, None))
    print("scoping %d commodities (%d treated, %d reference basket)\n"
          % (len(todo), len(todo) - len(ref), len(ref)))
    for cid, (frag, _, _) in sorted(todo.items(), key=lambda kv: int(kv[0])):
        if cid in scope:
            print("  %-4s already scoped: %d states" % (cid, len(scope[cid]["states"])))
            continue
        seen_name, state_names, counts = None, {}, {}

        def ask(sid, y, m):
            nonlocal seen_name
            try:
                j = polite(lambda: get(y, m, sid, cid), sleep)
            except Exception as e:
                print("  %-4s state %-3d %s-%s ERROR %s" % (cid, sid, y, m, type(e).__name__))
                return None
            cn, sn = names_from_title(j)
            if cn:
                seen_name = cn
            if sn:
                state_names[str(sid)] = sn
            n = len(j.get("markets") or [])
            counts.setdefault(str(sid), {})["%s-%s" % (y, m)] = n
            print("  %-4s state %-3d %-26s %s-%s markets %3d"
                  % (cid, sid, (sn or "?")[:26], y, m, n))
            return n

        y0, m0 = PROBE_MONTHS[0]
        for sid in range(1, MAX_STATE_ID + 1):
            ask(sid, y0, m0)
        live = [s for s, d in counts.items() if any(v for v in d.values())]

        if len(live) <= THIN_ENOUGH_TO_RECHECK:
            print("  %-4s only %d state(s) in %s-%s, asking the other months over the blanks"
                  % (cid, len(live), y0, m0))
            for y, m in PROBE_MONTHS[1:]:
                for sid in range(1, MAX_STATE_ID + 1):
                    if str(sid) in live:
                        continue
                    ask(sid, y, m)
            live = [s for s, d in counts.items() if any(v for v in d.values())]

        if seen_name and frag.strip().lower() not in seen_name.strip().lower():
            print("  !! id %s reports %r, expected %r. NOT SCOPED." % (cid, seen_name, frag))
            continue
        scope[cid] = {"name": seen_name, "role": "reference" if cid in ref else "treated",
                      "states": sorted(live, key=int),
                      "state_names": state_names, "counts": counts,
                      "probe_months": ["%s-%s" % t for t in PROBE_MONTHS]}
        SCOPE.write_text(json.dumps(scope, indent=2, sort_keys=True, ensure_ascii=False),
                         encoding="utf-8", newline="\n")
        print("  %-4s %-26s -> %d state(s) with data%s"
              % (cid, seen_name, len(live), "   DEAD IN AGMARKNET" if not live else ""))
    alive = [c for c in scope if scope[c]["states"]]
    tre = [c for c in alive if scope[c].get("role") != "reference"]
    print("\nscope written to %s" % SCOPE.name)
    print("commodities with a series: %d of %d scoped  (%d of them treated)"
          % (len(alive), len(scope), len(tre)))
    print("treated (commodity, state) pairs: %d" % sum(len(scope[c]["states"]) for c in tre))
    print("reference basket covers %d states"
          % len({s for c in alive if scope[c].get("role") == "reference" for s in scope[c]["states"]}))


def phase_map(sleep, upto):
    """ask the portal what each commodity id is called, and write it down"""
    OUT.mkdir(parents=True, exist_ok=True)
    m = json.loads(MAP.read_text(encoding="utf-8")) if MAP.exists() else {}
    y, mo = PROBE_MONTH
    miss = 0
    for cid in range(1, upto + 1):
        k = str(cid)
        if k in m:
            continue
        try:
            j = polite(lambda: get(y, mo, 2, k), sleep)
        except Exception as e:
            print("  id %-4s ERROR %s" % (k, type(e).__name__))
            miss += 1
            if miss >= 40:
                print("  40 failures in a row, stopping. re-run to resume.")
                break
            continue
        name, _ = names_from_title(j)
        if not name:
            miss += 1
            continue
        miss = 0
        m[k] = name
        print("  id %-4s %s" % (k, name))
        if len(m) % 25 == 0:
            MAP.write_text(json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False),
                           encoding="utf-8", newline="\n")
    MAP.write_text(json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print("\n%d ids named, written to %s" % (len(m), MAP.name))
    resolve(m, report=True)


def resolve_names(names, m=None):
    """same lookup as resolve() but for a plain list of names"""
    if m is None:
        m = json.loads(MAP.read_text(encoding="utf-8"))
    out = {}
    for nm in names:
        hits = sorted(k for k, v in m.items() if v.strip().lower() == nm.strip().lower())
        if len(hits) == 1:
            out[hits[0]] = m[hits[0]]
        else:
            print("  reference %r -> %s, skipped" % (nm, hits or "no match"))
    return out


def resolve(m=None, report=False):
    """name fragment -> id, and shout when it is not exactly one"""
    if m is None:
        if not MAP.exists():
            sys.exit("run --phase map first")
        m = json.loads(MAP.read_text(encoding="utf-8"))
    out, bad = {}, []
    for frag, a, b in TREATED:
        hits = sorted(k for k, v in m.items() if v.strip().lower() == frag.strip().lower())
        if not hits:
            hits = sorted(k for k, v in m.items() if frag.strip().lower() in v.strip().lower())
        if len(hits) == 1:
            out[hits[0]] = (frag, a, b)
        else:
            bad.append((frag, [k + "=" + m[k] for k in hits]))
    if report or bad:
        print("\nresolved:")
        for cid, (frag, a, b) in sorted(out.items(), key=lambda kv: int(kv[0])):
            print("  %-22s -> id %-4s  %s .. %s" % (frag, cid, a, b))
        for frag, hits in bad:
            print("  %-22s -> %s   NOT USABLE, fix the name in TREATED"
                  % (frag, hits if hits else "no match"))
    return out


def slug(name):
    keep = "".join(c if (c.isalnum() or c in " -_") else "_" for c in name)
    return "_".join(keep.split())[:60]


def valid(path, want_commodity=None):
    """A file is not good just because it parses.

    The portal renumbers: 267 of the 347 ids on the legacy list now name a different
    commodity. So a request built from a stale id returns a perfectly well-formed response
    for the WRONG commodity, and a check that only looks for the keys accepts it. The
    response names itself in `title`, so compare that.
    """
    try:
        j = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False, "unparseable"
    if not (isinstance(j, dict) and "markets" in j and "title" in j):
        return False, "missing keys"
    if want_commodity:
        cn, _ = names_from_title(j)
        if cn and want_commodity.strip().lower() not in cn.strip().lower():
            return False, "title says %r, asked for %r" % (cn, want_commodity)
    return True, ""


def phase_pull(sleep, confirm):
    if not SCOPE.exists():
        sys.exit("run --phase states first")
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    cmap = json.loads(MAP.read_text(encoding="utf-8"))
    jobs = []
    for cid, (frag, a, b) in sorted(resolve().items(), key=lambda kv: int(kv[0])):
        if cid not in scope:
            print("  %s (%s) not scoped, skipped" % (cid, frag))
            continue
        if not scope[cid]["states"]:
            continue
        for y, m in months(a, b):
            for sid in scope[cid]["states"]:
                jobs.append((cid, cmap.get(cid, frag), sid, y, m))

    # Seconds per request is not a constant: the response carries one row per market per
    # reported day, so a 200-market state-month is orders of magnitude bigger than a
    # one-market one, over the same link. Every estimate in this collection until now used a
    # hardcoded 0.4s here. Use the measured file if --phase cost has been run, and say so
    # plainly when it has not.
    if COSTFILE.exists():
        c = json.loads(COSTFILE.read_text(encoding="utf-8"))
        per = c["thin_s"], c["thick_s"]
        print("requests: %d   measured %.2fs (thin) to %.2fs (thick) plus %.1fs sleep"
              % (len(jobs), per[0], per[1], sleep))
        print("   so between %.1f and %.1f hours"
              % (len(jobs) * (per[0] + sleep) / 3600, len(jobs) * (per[1] + sleep) / 3600))
    else:
        print("requests: %d   per-request time NOT MEASURED. run --phase cost first;"
              % len(jobs))
        print("   this used to print a number built on a hardcoded 0.4s and it was wrong.")
    if not confirm:
        print("nothing fetched. re-run with --confirm.")
        return

    done = skipped = failed = mismatch = 0
    t0 = time.time()
    for k, (cid, cname, sid, y, m) in enumerate(jobs):
        # Folder carries the name as well as the id, because the id is the thing that moves.
        folder = OUT / ("%s_%s" % (cid, slug(cname))) / sid
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / ("%s-%s.json" % (y, m))
        if path.exists():
            ok, why = valid(path, cname)
            if ok:
                skipped += 1
                continue
            path.rename(path.with_suffix(".json.rejected_%s_%s"
                                         % (time.strftime("%Y%m%d_%H%M%S"), slug(why)[:40])))
        try:
            j = polite(lambda: get(y, m, sid, cid), sleep)
        except Exception as e:
            failed += 1
            print("  %-4s %-3s %s-%s ERROR %s" % (cid, sid, y, m, type(e).__name__))
            continue
        part = path.with_suffix(".json.part")
        part.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8", newline="\n")
        ok, why = valid(part, cname)
        if not ok:
            mismatch += 1
            part.rename(part.with_suffix(".part_rejected_%s" % slug(why)[:40]))
            print("  %-4s %-3s %s-%s REJECTED: %s" % (cid, sid, y, m, why))
            continue
        part.rename(path)
        done += 1
        if k % 25 == 0 or len(j.get("markets") or []) > 80:
            el = time.time() - t0
            rate = (k + 1) / max(el, 1e-9)
            print("  %-4s %-22s %-3s %s-%s  markets %3d   %5.1f%%  eta %.1f h"
                  % (cid, cname[:22], sid, y, m, len(j.get("markets") or []),
                     100.0 * (k + 1) / len(jobs), (len(jobs) - k - 1) / rate / 3600))
    print("\nfetched %d, already on disk %d, failed %d, rejected on their own title %d"
          % (done, skipped, failed, mismatch))
    man = OUT / "pull_manifest.json"
    man.write_text(json.dumps(
        {"window": [jobs[0][3] + "-" + jobs[0][4], jobs[-1][3] + "-" + jobs[-1][4]] if jobs else [],
         "commodities": sorted({"%s=%s" % (c, n) for c, n, _, _, _ in jobs})},
        indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print("manifest written to %s  (the id-to-name map as it stood for this pull)" % man.name)


RECENT = ("2026", "06")          # the most recent full month, for the zeros that could not
                                 # have shown a series in the probe months


def phase_prewindow(sleep):
    """Two questions the scope phase could not answer, both cheap, both prior to power.

    (A) A commodity that only starts appearing in Agmarknet when eNAM lists it gives a
        support set that grows from zero by administration, not by information. The probe
        months (2024-07, 2024-11, 2025-01) sit AFTER listing for cohorts A and B, so for
        those the scope says nothing about whether a pre-window exists. Ask each live
        (commodity, state) pair two months near the start of its own design window.

    (B) The zeros whose window starts 2023-01 are the 2025 listing batches. Every probe
        month sits before those listings, so a zero there is not evidence of absence if
        Agmarknet's own menu tracks eNAM's. Ask them one recent month across every state.
    """
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    want = {frag: (a, b) for frag, a, b in TREATED}

    def ask(cid, sid, y, m):
        try:
            j = polite(lambda: get(y, m, sid, cid), sleep)
        except Exception as e:
            return None, type(e).__name__
        return len(j.get("markets") or []), None

    # A zero in an early month is only evidence of absence if the API HAS that month.
    # Ask a thick reference commodity in a thick state at every early month first; if the
    # reference is empty there too, the month is outside the API's own coverage and every
    # treated zero at that month says nothing.
    early_months = sorted({("%04d" % (int(a.split("-")[0]) + k), "07")
                           for _, a, _ in TREATED for k in (0, 1)})
    ref = resolve_names(["Wheat"])
    thick = None
    for cid, rec in scope.items():
        if rec.get("role") == "reference" and rec["name"].strip().lower() == "wheat":
            thick = max(((s, max(rec["counts"][s].values())) for s in rec["states"]),
                        key=lambda kv: kv[1])[0]
    print("=== 0. coverage control: %s in state %s, one request per early month ==="
          % (list(ref.values())[0] if ref else "?", thick))
    covered = set()
    for y, m in early_months:
        n, err = ask(list(ref)[0], int(thick), y, m)
        print("  %s-%s  reference markets %s" % (y, m, err or n))
        if n:
            covered.add((y, m))
    print("  months the API actually carries: %s\n"
          % (", ".join("%s-%s" % t for t in sorted(covered)) or "NONE, branch A is unreadable"))

    print("=== A. pre-window: does the series predate the eNAM listing? ===")
    print("    a live pair with markets in the early months has a pre-window;")
    print("    a live pair that is empty there grew from zero, and that is a menu event.\n")
    verdict = {}
    for cid, rec in sorted(scope.items(), key=lambda kv: int(kv[0])):
        if rec.get("role") == "reference" or not rec["states"]:
            continue
        w = want.get(rec["name"])
        if not w:
            continue
        y0, m0 = w[0].split("-")
        early = [("%04d" % (int(y0) + 0), "%02d" % 7), ("%04d" % (int(y0) + 1), "%02d" % 7)]
        for sid in rec["states"]:
            for y, m in early:
                n, err = ask(cid, int(sid), y, m)
                sn = rec["state_names"].get(sid, sid)
                print("  %-24s %-18s %s-%s  markets %s"
                      % (rec["name"][:24], sn[:18], y, m, err or n))
                if n:
                    verdict.setdefault(rec["name"], []).append("%s %s-%s=%d" % (sn, y, m, n))
                elif (y, m) not in covered:
                    print("       ^ that month is outside the API's coverage, so this zero"
                          " is not evidence")
    print("\n  pairs with a pre-window:")
    for k, v in sorted(verdict.items()):
        print("    %-24s %s" % (k, "; ".join(v)))
    dark = sorted({scope[c]["name"] for c in scope
                   if scope[c].get("role") != "reference" and scope[c]["states"]}
                  - set(verdict))
    print("  live but EMPTY in its own early window (grew from zero): %s"
          % (", ".join(dark) if dark else "none"))

    print("\n=== B. the 2025-batch zeros, asked at %s-%s ===" % RECENT)
    y, m = RECENT
    for cid, rec in sorted(scope.items(), key=lambda kv: int(kv[0])):
        if rec.get("role") == "reference" or rec["states"]:
            continue
        if want.get(rec["name"], ("", ""))[0] != "2023-01":
            continue
        found = []
        for sid in range(1, MAX_STATE_ID + 1):
            n, err = ask(cid, sid, y, m)
            if n:
                found.append("%d=%d" % (sid, n))
        print("  %-24s %s" % (rec["name"][:24],
                              ", ".join(found) if found
                              else "still nothing anywhere at %s-%s" % (y, m)))

GOURDS = ["Bitter gourd", "Bottle gourd", "Ashgourd", "Little gourd(Kundru)",
          "Pointed gourd(Parval)", "Spiny Gourd / Kartali(Kantola)", "Round gourd",
          "Sponge gourd", "Red Gourd", "Ridge Gourd(Permal/Hybrid Gourd)"]


def phase_diagnose(sleep, blocks="abcd"):
    """Four checks on the treated commodities, each aimed at one specific alternative.

    (a) Family conservation. Ten gourd codes exist. If markets moved off the generic code
        onto specific ones, the family total holds while Sponge gourd falls.
    (b) The split name. Chrysanthemum exists twice, 189 (Loose) and 331 (bare). A support
        set read on one of a pair is missing the other by construction.
    (c) Cliff, slope, or season. A code change lands on one month; a market losing a trade
        does not; and a summer vegetable does neither, it cycles. Ask every month, with a
        thick year-round reference in the same state beside it.
    (d) Sugarcane, the one commodity of the 2025-07-09 batch that Agmarknet carries. Cane
        mostly moves to mills at an administered price rather than through mandi auctions,
        so its mandi support set has to be measured rather than assumed.
    """
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    m = json.loads(MAP.read_text(encoding="utf-8"))
    byname = {v.strip().lower(): k for k, v in m.items()}

    def ask(cid, sid, y, mo):
        try:
            j = polite(lambda: get(y, mo, sid, cid), sleep)
        except Exception as e:
            return None, type(e).__name__
        return len(j.get("markets") or []), None

    STATES = {"34": "Uttar Pradesh", "12": "Haryana", "35": "Uttarakhand"}

    def land(block, rows):
        """A diagnostic that costs hundreds of requests has to land on disk.

        Block (e) cost 258 requests and wrote nothing, so its answer lived only in a
        terminal scrollback. That is the same mistake as fetching data and not keeping it:
        the requests are spent either way, and a printed table is gone the moment the
        window is closed.
        """
        p = OUT / ("diagnose_%s.json" % block)
        p.write_text(json.dumps({"run": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": rows},
                                indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        print("  -> %s  (%d rows)" % (p.name, len(rows)))

    if "a" in blocks:
        print("=== (a) gourd family conservation ===")
        rows_a = []
        for y, mo in (("2018", "07"), ("2021", "07"), ("2024", "11")):
            for sid, sname in STATES.items():
                tot, parts = 0, []
                for nm in GOURDS:
                    cid = byname.get(nm.strip().lower())
                    if not cid:
                        continue
                    n, err = ask(cid, int(sid), y, mo)
                    if n:
                        tot += n
                        parts.append("%s=%d" % (nm.split("(")[0].strip()[:14], n))
                print("  %s-%s  %-16s family total %3d   %s"
                      % (y, mo, sname, tot, ", ".join(parts) or "all empty"))
                rows_a.append({"month": "%s-%s" % (y, mo), "state": sname,
                               "family_total": tot, "parts": parts})

        land("a_gourd_family", rows_a)

    if "b" in blocks:
        print("\n=== (b) Chrysanthemum: 189 (Loose) against 331 (bare) ===")
        rows_b = []
        for nm in ("Chrysanthemum(Loose)", "Chrysanthemum"):
            cid = byname.get(nm.lower())
            for sid, sname in (("20", "Maharashtra"), ("16", "Karnataka"),
                               ("25", "NCT of Delhi")):
                row = []
                for y, mo in (("2017", "07"), ("2018", "07"), ("2021", "07"), ("2024", "11")):
                    n, err = ask(cid, int(sid), y, mo)
                    row.append("%s-%s=%s" % (y, mo, err or n))
                print("  id %-4s %-22s %-14s %s" % (cid, nm[:22], sname, "  ".join(row)))
                rows_b.append({"id": cid, "name": nm, "state": sname, "reads": row})

        land("b_chrysanthemum_codes", rows_b)

    if "d" in blocks:
        print("\n=== (d) Sugarcane, listed 2025-07-09 ===")
        rows_d = []
        sc = byname.get("sugarcane")
        for y, mo in (("2023", "07"), ("2024", "07"), ("2026", "06")):
            found, tot = [], 0
            for sid in range(1, MAX_STATE_ID + 1):
                n, err = ask(sc, sid, y, mo)
                if n:
                    found.append("%s=%d" % (sid, n))
                    tot += n
            print("  %s-%s  states with data %2d   markets %3d   %s"
                  % (y, mo, len(found), tot, ", ".join(found) or "nothing anywhere"))
            rows_d.append({"month": "%s-%s" % (y, mo), "states": len(found),
                           "markets": tot, "detail": found})

        land("d_sugarcane", rows_d)

    if "e" in blocks:
        # Sponge gourd in UP runs 2018-2025 flat to slightly rising (annual sums 296, 328,
        # 312, 310, 333, 316, 331, 379) and then reads 7 to 10 in the 2026 peak months where
        # 2025 read 46 to 61. Wheat in the same state went the other way in 2026, from about
        # 185 to about 240. Two series breaking in opposite directions in the same state and
        # year is not weather and not a reporting outage; it looks like a remap. Whatever it
        # is, the post-period of the 2025-10-08 cohort lies entirely inside it, so the usable
        # window depends on the answer. Compare the same calendar month one year apart.
        print("=== (e) the 2026 break: same calendar month, 2025-06 against 2026-06 ===")
        pairs = []
        for cid, rec in sorted(scope.items(), key=lambda kv: int(kv[0])):
            if not rec["states"]:
                continue
            sids = rec["states"]
            if rec.get("role") == "reference":
                # every treated pair is walked, but the reference basket only has to answer
                # "is the break everywhere". Its states are also the thick ones, and a thick
                # state-month is a much bigger response than a thin one, so walking all 108
                # reference pairs costs far more than the 108/129 of the count suggests.
                sids = sorted(sids, key=lambda s: -max(rec["counts"][s].values()))[:3]
            for sid in sids:
                pairs.append((cid, rec["name"], sid, rec["state_names"].get(sid, sid),
                              rec.get("role")))
        for nm in ("Red Gourd", "Ridge Gourd(Permal/Hybrid Gourd)", "Bitter gourd",
                   "Bottle gourd"):
            cid = byname.get(nm.strip().lower())
            if cid:
                pairs.append((cid, nm, "34", "Uttar Pradesh", "gourd sibling"))
        print("  %-28s %-16s %-14s %6s %6s   ratio" % ("commodity", "state", "role",
                                                       "2025-06", "2026-06"))
        rows_e = []
        for cid, nm, sid, sname, role in pairs:
            a, _ = ask(cid, int(sid), "2025", "06")
            b, _ = ask(cid, int(sid), "2026", "06")
            r = ("%.2f" % (b / a)) if (a and b is not None) else "-"
            print("  %-28s %-16s %-14s %6s %6s   %s"
                  % (nm[:28], sname[:16], (role or "")[:14], a, b, r))
            rows_e.append({"id": cid, "name": nm, "state": sname, "role": role,
                           "m2025_06": a, "m2026_06": b})

        land("e_2026_break", rows_e)

    if "c" in blocks:
        print("\n=== (c) Sponge gourd in Uttar Pradesh, every month, Wheat beside it ===")
        sg, wh = byname["sponge gourd"], byname["wheat"]
        out = []
        for y, mo in months("2017-01", "2026-08"):
            a, _ = ask(sg, 34, y, mo)
            b, _ = ask(wh, 34, y, mo)
            out.append(("%s-%s" % (y, mo), a, b))
            print("  %s-%s  sponge %3s  wheat %3s  %s"
                  % (y, mo, a, b, "#" * min(int(a or 0), 60)))
        p = OUT / "diagnose_sponge_up.json"
        p.write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
        print("\n  written to %s" % p.name)


def phase_cost(sleep):
    """Multiply out the main pull with a measured number instead of a guessed one.

    Every cost estimate in this collection so far has treated a request as costing a fixed
    time. It does not. The response carries one entry per market per reported day, so a
    state-month with 200 markets returns something on the order of a hundred times what a
    one-market pair returns, and it travels over the same link. The main pull is dominated
    by the reference basket, which is made entirely of the thickest commodities, so the one
    number the estimate is most sensitive to is the one never measured.

    Time and size one request at each thickness actually present, then print the arithmetic.
    """
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    probes = []
    for cid, rec in sorted(scope.items(), key=lambda kv: int(kv[0])):
        for sid, mm in rec["counts"].items():
            n = max(mm.values()) if mm else 0
            if n:
                probes.append((n, cid, rec["name"], sid, rec["state_names"].get(sid, sid)))
    probes.sort()
    picks, seen = [], set()
    for target in (1, 5, 20, 50, 150, 10 ** 9):
        best = min(probes, key=lambda p: abs(p[0] - target))
        if best[1:] not in seen:
            seen.add(best[1:])
            picks.append(best)
    print("  %-24s %-16s %7s %9s %8s %10s" % ("commodity", "state", "markets", "seconds",
                                              "KB", "KB/market"))
    rows = []
    for n, cid, nm, sid, sname in picks:
        t0 = time.time()
        try:
            j = get("2025", "06", int(sid), cid)
        except Exception as e:
            print("  %-24s %-16s  %s" % (nm[:24], sname[:16], type(e).__name__))
            continue
        dt = time.time() - t0
        kb = len(json.dumps(j, ensure_ascii=False).encode("utf-8")) / 1024.0
        got = len(j.get("markets") or [])
        rows.append((got, dt, kb))
        print("  %-24s %-16s %7d %9.2f %8.1f %10.2f"
              % (nm[:24], sname[:16], got, dt, kb, kb / max(got, 1)))
        time.sleep(sleep)
    if len(rows) < 2:
        return
    thin = [r for r in rows if r[0] <= 10]
    thick = [r for r in rows if r[0] >= 100] or [max(rows)]
    ts = sum(r[1] for r in thin) / max(len(thin), 1) if thin else rows[0][1]
    ks = sum(r[1] for r in thick) / len(thick)
    treated = sum(len(r["states"]) for r in scope.values()
                  if r["states"] and r.get("role") != "reference") * 116
    refstates = {s for r in scope.values() if r.get("role") == "reference" for s in r["states"]}
    ref = 5 * len(refstates) * 116
    print("\n  measured: a thin request %.2fs, a thick one %.2fs  (ratio %.1fx)"
          % (ts, ks, ks / max(ts, 0.01)))
    print("  treated side   %5d requests, thin   -> %.1f h" % (treated, treated * (ts + sleep) / 3600))
    print("  reference side %5d requests, thick  -> %.1f h" % (ref, ref * (ks + sleep) / 3600))
    print("  reference disk at the measured size: about %.1f GB"
          % (ref * (sum(r[2] for r in thick) / len(thick)) / 1024 / 1024))
    print("\n  the reference side is the whole cost, and it is the part that was never sized.")
    COSTFILE.write_text(json.dumps(
        {"measured": time.strftime("%Y-%m-%dT%H:%M:%S"), "sleep": sleep,
         "thin_s": round(ts, 3), "thick_s": round(ks, 3),
         "thick_kb": round(sum(r[2] for r in thick) / len(thick), 1),
         "rows": [{"markets": r[0], "seconds": round(r[1], 3), "kb": round(r[2], 1)}
                  for r in rows]},
        indent=1), encoding="utf-8", newline="\n")
    print("  written to %s, and --phase pull reads it instead of guessing." % COSTFILE.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["probe", "map", "states", "prewindow", "diagnose", "cost", "pull"], default="probe")
    ap.add_argument("--upto", type=int, default=MAX_COMMODITY_ID,
                    help="highest commodity id the map phase asks about")
    ap.add_argument("--sleep", type=float, default=0.8)
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--blocks", default="abcd",
                    help="which diagnose blocks to run, e.g. --blocks c")
    a = ap.parse_args()
    if a.phase == "probe":
        y, m = PROBE_MONTH
        j = get(y, m, 2, "2")
        c, s = names_from_title(j)
        print("one request, no data bought:")
        print("  commodity : %s" % c)
        print("  state     : %s" % s)
        print("  markets   : %d" % len(j.get("markets") or []))
        print("  columns   : %s" % ", ".join(x.get("key", "?") for x in (j.get("columns") or [])))
    elif a.phase == "map":
        phase_map(a.sleep, a.upto)
    elif a.phase == "states":
        phase_states(a.sleep)
    elif a.phase == "prewindow":
        phase_prewindow(a.sleep)
    elif a.phase == "cost":
        phase_cost(a.sleep)
    elif a.phase == "diagnose":
        phase_diagnose(a.sleep, a.blocks)
    else:
        phase_pull(a.sleep, a.confirm)


if __name__ == "__main__":
    main()
