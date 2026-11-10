"""B153: triangle deficits in the British rail fares database, by fare setter.

One issue of the fares database (flows and fares, station clusters, locations,
routes) and the timetable issued with it. For a ticket type t and three stations
o, b, d called at in that order by one public train,

    delta_t(o, b, d) = f_t(o, b) + f_t(b, d) - f_t(o, d)        (pence)

delta < 0 means two tickets split at b cost less than the through ticket. Each
station-pair price f_t(x, y) is the lowest fare among the flows that serve the
pair: origin is x, x's fare group, or a station cluster holding either; the
destination likewise; a reversible flow serves both directions; the route code
must be allowed by the route knob; the fare must be live on the generation date
and carry no restriction code. The flow that supplies the price is kept with
its usage code ('A' a fare actually set, 'G' a flow constructed by
concatenating others) and its fare setter (the TOC field of the flow). A
triangle's setter count k is the number of distinct setters among its three
supplying flows.

Route knob. 'compatible' (default) prices each leg on the
train that carries the triangle (the first calling sequence, in sorted order,
that yields it): a flow with any route code is admitted when the route's
include and exclude locations (route file, location records) are met by the
stations the train calls at or passes between the leg's ends; routes without
location records are admitted only when they read NOT VIA LONDON and neither
the ends nor the path touch the London fare group; routes reading ONLY (one
operator's trains) are not admitted; a flow marked cross-London is admitted
only when an end or the path touches the London fare group. 'anyperm' (a knob
point) admits the two route codes that put no condition on the journey (00000,
01000) on every pair, whatever the train. Three brackets are printed beside the
knob points and are not knob values: every route code on all three legs; every
route code on the through leg alone; the anyperm reading without cross-London
flows on pairs with neither end in London.

Criteria (kind in brackets; each flag is computed from the object):
  B153-1 [instrument]   member hashes match the manifest; FFL/TTY/TOC/FSC record
                        counts equal their headers and the files end with the
                        end-of-file line; every non-cancelled MCA schedule closes.
  B153-2 [instrument]   retail check of the listed station triples, read from the
                        stored retail rows: each retail Anytime Day Single equals
                        the default-point price; a leg where retail shows no
                        Anytime Day Single has its shown price in the feed at the
                        lower of SDS and SOS on the same train. No rows: third state.
  B153-3 [known_answer] every live 'G' flow ("constructed by concatenating two or
                        more other flows", RSPS5045 4.1.2) is a sum of flow fares.
                        Read in three cells: an exact two-leg or three-leg sum;
                        a fare below the cheapest chain of any length in the file
                        (no sum of flow fares reaches it: FAIL cell); the rest
                        (four legs or more, or a search cut by its time cap, or
                        no chain at all: third state). The FAIL cell is then read
                        into classes (a reading, no verdict): a two-leg sum exact
                        with next-round fares, with an Anytime Single leg, with a
                        restricted fare, with another standard single; the rest
                        set below every sum of components in the file.
  B153-4 [rival]        the scalar-potential prediction delta = 0 (within the
                        rounding floor 1.5 grid) on triangles supplied by 'A'
                        flows only.
  B153-5 [own_reading]  three-cell sign table; the flag reads whether both signs
                        clear the floor inside one setter's own table (k = 1).
  B153-6 [own_reading]  share of delta < -floor lower among k = 1 triangles than
                        among k >= 2, read on every knob point (ten points).
  B153-7 [known_answer] railcard arm. Not run in this pass (third state).
  B153-8 [bookkeeping]  the record carries its config block and coverage table.

The record holds aggregate counts, shares, quantiles and public station names
only; no fare table and no individual fares (single triangles carry a delta band,
not a delta).

    python -B experiments/b153_rail_triangles.py --selftest
    python -B experiments/b153_rail_triangles.py --mutation
    python -B experiments/b153_rail_triangles.py --run          # all points, resumable
    python -B experiments/b153_rail_triangles.py --gflows       # B153-3 search, resumable
    python -B experiments/b153_rail_triangles.py --gbelow       # classes of the B153-3 FAIL cell
    python -B experiments/b153_rail_triangles.py --assemble     # write the record from the cache
"""
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import ctypes  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "rail_fares"
CACHE = ROOT / "data" / "cache" / "b153" / "v3"
CACHE_V2 = ROOT / "data" / "cache" / "b153" / "v2"  # the 2026-10-14 run, read only for the rule-19 comparison
RETAIL = RAW / "b153_arm0_retail_20261027.json"
OUT = ROOT / "results" / "b153_rail_triangles.json"
SESSION = "B153"
STAGE = "B153"
TICKETS = ("SDS", "SOS")
GRID = 5
LONDON_FG = "1072"
MUT = os.environ.get("B153_MUT", "")  # mutation hook for the mutation test only

# knob points: each knob moved alone from the default
#: route codes whose route description puts no condition on the journey: 00000 prints "ANY PERMITTED",
#: 01000 prints "." (an empty route). Both are read as the any-permitted route by default.
ANYPERM = frozenset({"00000", "01000"})
#: default reading point: routes compatible with the train (ruled 2026-10-27; until then 'anyperm' was the default)
DEFAULT = {"ticket": "SDS", "route": "compatible", "p2p_first": False, "floor_mult": 1.5, "dedupe": "stations"}
POINTS = {
    "default": {},
    "ticket_SOS": {"ticket": "SOS"},
    "ticket_min": {"ticket": "min"},
    "p2p_first": {"p2p_first": True},
    "floor_1x": {"floor_mult": 1.0},
    "floor_3x": {"floor_mult": 3.0},
    "dedupe_flows": {"dedupe": "flows"},
    "route_anyperm": {"route": "anyperm"},
    "route_relaxed": {"route": "relaxed"},
    "route_00000_only": {"route": "00000"},
}
#: the 2026-10-14 point that each point here reproduces when it has the same config (rule 19 comparison)
V2_SAME = {"default": "route_compatible", "route_anyperm": "default", "route_relaxed": "route_relaxed",
           "route_00000_only": "route_00000_only", "bracket_any_all_legs": "bracket_any_all_legs",
           "bracket_any_through_leg": "bracket_any_through_leg", "bracket_no_cross_london": "bracket_no_cross_london"}
#: brackets, not knob values: they admit fares a passenger on that train might not hold
BRACKETS = {
    "bracket_any_all_legs": {"route": "any"},
    "bracket_any_through_leg": {"route": "anyperm", "through_route": "any"},
    "bracket_no_cross_london": {"route": "noxlon"},
}

MAP_B3 = {"some G fare below every chain of flow fares in the file": False,
          "every G fare met by an exact two- or three-leg sum": True,
          "no fare below every chain, some untested at four legs or more": None,
          "no G flow": None}
MAP_B5 = {"cells sum to the count and both signs clear the floor at k = 1": True,
          "cells sum to the count and one sign or none clears the floor at k = 1": False,
          "a cell missing or the cells do not sum to the count": False,
          "no triangle, or no k = 1 triangle": None}
MAP_B6 = {"all points lower": True, "all points not lower": False, "direction flips or a cell is empty": None}
MAP_B4 = {"A-flow triangles exist, some beyond the floor": "PASS, grid B",
          "A-flow triangles exist, none beyond the floor": "FAIL, grid C",
          "no A-flow triangle": "None, grid unread"}
G_CAP_S = 0.5  # time cap per G flow for the three-leg search; a capped flow lands in the third state
G_SAMPLE = 2000  # flows searched at three legs, drawn with a fixed seed from those at or above their cheapest chain
G_SEED = 7


def floor_of(mult, grid=GRID):
    if MUT == "floor0":
        return 0.0
    return mult * grid


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def peak_mb():
    try:
        class PMC(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        gpmi = ctypes.windll.psapi.GetProcessMemoryInfo
        gpmi.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
        gpmi(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.PeakWorkingSetSize / 2 ** 20
    except Exception:
        return float("nan")


def r6(x):
    return float(f"{x:.6f}")


def write_json(p, obj):
    p.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# reading


def read_lines(p):
    with open(p, "rb") as f:
        for raw in f:
            yield raw.decode("latin-1").rstrip("\r\n")


def dkey(ddmmyyyy):
    return ddmmyyyy[4:8] + ddmmyyyy[2:4] + ddmmyyyy[0:2]


def is_live(start, end, gen):
    return dkey(start) <= gen <= dkey(end)


def file_check(p):
    """Records (non-comment lines), the header's Records value, and whether the last line is the end-of-file line."""
    n = 0
    header = None
    last = ""
    for s in read_lines(p):
        if s.startswith("/"):
            if s.startswith("/!! Records:"):
                header = int(s.split(":", 1)[1])
        elif s.strip():
            n += 1
        if s.strip():
            last = s
    return {"records": n, "header": header, "ends": last.startswith("/!! End of file")}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def generation_key(ffl):
    for s in read_lines(ffl):
        if s.startswith("/!! Generated:"):
            g = s.split(":", 1)[1].strip()
            return g[6:10] + g[3:5] + g[0:2]
        if not s.startswith("/"):
            break
    raise ValueError("no generation date in header")


def parse_loc(p, gen):
    loc = {}
    for s in read_lines(p):
        if s.startswith("/") or s[1:2] != "L" or len(s) < 75:
            continue
        if not is_live(s[17:25], s[9:17], gen):
            continue
        nlc = s[36:40]
        if not nlc.strip():
            continue
        loc[nlc] = {"desc": s[40:56].strip(), "crs": s[56:59].strip(), "fg": s[69:75].strip()[:4]}
    return loc


def parse_fsc(p, gen):
    members = defaultdict(set)   # cluster -> members
    clusters = defaultdict(set)  # member -> clusters
    for s in read_lines(p):
        if s.startswith("/") or len(s) < 25:
            continue
        if not is_live(s[17:25], s[9:17], gen):
            continue
        c, m = s[1:5], s[5:9]
        members[c].add(m)
        clusters[m].add(c)
    return members, clusters


def parse_toc(p):
    fare_tocs = {}
    for s in read_lines(p):
        if s.startswith("/") or s[:1] != "F":
            continue
        fare_tocs[s[1:4]] = {"carrier": s[4:6].strip(), "name": s[6:36].strip()}
    return fare_tocs


def parse_rte(p, gen):
    """Route descriptions of live routes, and their live include/exclude locations (RSPS5045 4.20.3)."""
    rte = {}
    locs = defaultdict(lambda: {"I": set(), "E": set()})
    for s in read_lines(p):
        if s.startswith("/"):
            continue
        if s[1:2] == "R" and len(s) >= 47:
            if is_live(s[15:23], s[7:15], gen):
                rte[s[2:7]] = s[31:47].strip()
        elif s[1:2] == "L" and len(s) >= 26:
            if dkey(s[7:15]) < gen:
                continue
            ie = s[25]
            if ie in ("I", "E"):
                for code in (s[18:22].strip(), s[22:25].strip()):
                    if code:
                        locs[s[2:7]][ie].add(code)
    return rte, {r: {"I": frozenset(v["I"]), "E": frozenset(v["E"])} for r, v in locs.items() if r in rte}


def add_fare(tab, o, d, direction, e):
    """Index one fare; a reversible ('R') flow serves both directions."""
    tab[(o, d)].append(e)
    if direction == "R" and o != d and MUT != "RasS":
        tab[(d, o)].append(e)


#: bits of the per-code-pair presence mask used to say why a station pair is unpriced
HAS_SDS_ANY, HAS_SDS_ROUTE, HAS_SOS, HAS_OTHER = 1, 2, 4, 8


def parse_ffl(p, gen, tickets=TICKETS, reverse=True):
    """Price index per ticket: (origin code, destination code) -> list of (fare, route, usage, toc, fid, xlon)."""
    flows = {}
    cnt = Counter()
    idx = {t: defaultdict(list) for t in tickets}
    gflows = {t: [] for t in tickets}
    has = {}
    for s in read_lines(p):
        if s.startswith("/"):
            continue
        rt = s[1:2]
        if rt == "F":
            cnt["flow"] += 1
            if not is_live(s[28:36], s[20:28], gen):
                cnt["flow_not_live"] += 1
                continue
            fid = s[42:49]
            flows[fid] = (sys.intern(s[2:6]), sys.intern(s[6:10]), sys.intern(s[10:15]), s[18], s[19],
                          sys.intern(s[36:39]), s[39])
        elif rt == "T":
            cnt["fare"] += 1
            t = s[9:12]
            fl = flows.get(s[2:9])
            if fl is not None:
                o, d, route, usage, direction, toc, xl = fl
                bit = (HAS_SDS_ANY if route in ANYPERM else HAS_SDS_ROUTE) if t == "SDS" else (HAS_SOS if t == "SOS" else HAS_OTHER)
                has[(o, d)] = has.get((o, d), 0) | bit
                if direction == "R" and o != d:
                    has[(d, o)] = has.get((d, o), 0) | bit
            if t not in idx:
                continue
            if fl is None:
                cnt[f"fare_{t}_on_not_live_flow"] += 1
                continue
            if s[20:22].strip():
                cnt[f"fare_{t}_restricted_skipped"] += 1
                continue
            v = int(s[12:20])
            if v == 99999999:
                cnt[f"fare_{t}_placeholder"] += 1
                continue
            o, d, route, usage, direction, toc, xl = fl
            add_fare(idx[t], o, d, direction if reverse else "S", (v, route, usage, toc, s[2:9], xl))
            cnt[f"fare_{t}_indexed"] += 1
            cnt[f"fare_{t}_usage_{usage}"] += 1
            if usage == "G":
                gflows[t].append((o, d, v, route, toc, s[2:9]))
    cnt["flow_live"] = len(flows)
    return idx, gflows, cnt, has


def parse_nfo(p, gen, tickets=TICKETS):
    pairs = defaultdict(set)
    n = Counter()
    for s in read_lines(p):
        if s.startswith("/") or len(s) < 65:
            continue
        if s[17:20] not in tickets or s[14:17].strip():
            continue
        if not is_live(s[29:37], s[21:29], gen):
            continue
        n["live_no_railcard"] += 1
        if s[64] == "Y" and s[46:54] != "99999999":
            n["composite_Y"] += 1
            pairs[s[17:20]].add((s[1:5], s[5:9]))
    return pairs, n


# ---------------------------------------------------------------------------
# timetable


def parse_msn(p):
    tip = {}
    for s in read_lines(p):
        if s[:1] != "A" or len(s) < 52 or s.startswith("A    " + " " * 20):
            continue
        t = s[36:43].strip()
        crs = s[49:52].strip()
        if t and crs:
            tip[t] = (crs, s[5:31].strip(), s[43:46].strip())
    return tip


def station_names(tip):
    """One public name per CRS: the MSN entry whose minor CRS equals the CRS, else the first by name."""
    best = {}
    for t, (crs, nm, minor) in tip.items():
        key = (minor != crs, nm)
        if crs not in best or key < best[crs][0]:
            best[crs] = (key, nm)
    return {c: v[1] for c, v in best.items()}


def _acts(b):
    return {b[i:i + 2] for i in range(0, len(b), 2)}


def parse_mca(p, tip2sid):
    """Distinct public calling sequences as tuples of (station id, flags); flags 1 board, 2 alight.

    Also returns, per public sequence, the full path of the first schedule that yields it (every location the
    train calls at or passes that maps to a station, consecutive repeats merged) and the position in that path of
    each public call."""
    cnt = Counter()
    seqs = set()
    full_of = {}
    unmapped = Counter()
    cur = None
    full = pos = None
    with open(p, "rb") as f:
        for raw in f:
            rt = raw[:2]
            if rt == b"BS":
                cnt["BS"] += 1
                if cur is not None:
                    cnt["BS_unclosed"] += 1
                stp = raw[79:80]
                cnt["BS_stp_" + stp.decode("latin-1")] += 1
                cur = None if stp == b"C" else []
                full, pos = [], []
                if cur is not None:
                    cnt["BS_open"] += 1
                continue
            if rt == b"LT" and cur is None:
                cnt["LT_orphan"] += 1
                continue
            if cur is None or rt not in (b"LO", b"LI", b"LT"):
                continue
            t = raw[2:9].decode("latin-1").strip()
            if rt == b"LO":
                pdp = raw[15:19]
                a = _acts(raw[29:41])
                board = pdp.strip() not in (b"", b"0000") and b"D " not in a and b"N " not in a
                alight = False
                public = board
            elif rt == b"LI":
                pa, pdp = raw[25:29], raw[29:33]
                a = _acts(raw[42:54])
                hasa = pa.strip() not in (b"", b"0000")
                hasd = pdp.strip() not in (b"", b"0000")
                public = hasa or hasd
                alight = hasa and b"U " not in a and b"N " not in a
                board = hasd and b"D " not in a and b"N " not in a
            else:
                pa = raw[15:19]
                a = _acts(raw[25:37])
                alight = pa.strip() not in (b"", b"0000") and b"N " not in a
                board = False
                public = alight
            sid = tip2sid.get(t)
            if sid is not None and not (full and full[-1] == sid):
                full.append(sid)
            if public:
                if sid is None:
                    unmapped[t] += 1
                else:
                    fl = (1 if board else 0) | (2 if alight else 0)
                    if cur and cur[-1][0] == sid:
                        cur[-1] = (sid, cur[-1][1] | fl)
                    else:
                        cur.append((sid, fl))
                        pos.append(len(full) - 1)
            if rt == b"LT":
                cnt["LT"] += 1
                if len(cur) >= 2:
                    key = tuple(cur)
                    seqs.add(key)
                    if key not in full_of:
                        full_of[key] = (tuple(full), tuple(pos))
                cur = None
    if cur is not None:
        cnt["BS_unclosed"] += 1
    return seqs, cnt, unmapped, full_of


def _triples_of(s):
    L = len(s)
    for i in range(L):
        oi, fi = s[i]
        if not fi & 1:
            continue
        for j in range(i + 1, L):
            bj, fj = s[j]
            if fj != 3 or bj == oi:
                continue
            for k in range(j + 1, L):
                dk, fk = s[k]
                if fk & 2 and dk != oi and dk != bj:
                    yield i, j, k


def triples_from(seqs, n):
    out = set()
    for s in seqs:
        for i, j, k in _triples_of(s):
            out.add((s[i][0] * n + s[j][0]) * n + s[k][0])
    arr = np.fromiter(out, dtype=np.int64, count=len(out))
    arr.sort()
    return arr


def triple_reps(seqs, n, tri):
    """For each triangle (aligned with the sorted array tri): the first sequence in sorted order that yields it and
    the three call positions in that sequence."""
    order = sorted(seqs)
    rep = {}
    for si, s in enumerate(order):
        for i, j, k in _triples_of(s):
            code = (s[i][0] * n + s[j][0]) * n + s[k][0]
            if code not in rep:
                rep[code] = (si, i, j, k)
    arr = np.array([rep[c] for c in tri.tolist()], dtype=np.int32).reshape(-1, 4)
    return order, arr


# ---------------------------------------------------------------------------
# pricing


class Net:
    """Stations (ids 0..n-1) with their fare codes, and the price index."""

    def __init__(self, nlcs, loc, clusters, idx, names, london=frozenset(), notlondon_routes=frozenset(),
                 rte=None, rte_locs=None):
        self.nlcs = nlcs
        self.n = len(nlcs)
        self.idx = idx
        self.names = names
        self.london = london
        self.notlondon = notlondon_routes
        self.rte = rte or {}
        self.rte_locs = rte_locs or {}
        self.codes = []
        self.place = []  # per station: codes a route location record can name (NLC, fare group, CRS)
        self.is_lon = []
        for nlc in nlcs:
            base = [nlc]
            info = loc.get(nlc, {})
            fg = info.get("fg", "")
            if fg and fg != nlc:
                base.append(fg)
            clus = set()
            if MUT != "nocluster":
                for c in base:
                    clus |= clusters.get(c, set())
            self.codes.append((tuple(base), tuple(sorted(clus - set(base)))))
            self.place.append(frozenset(base + ([info["crs"]] if info.get("crs") else [])))
            self.is_lon.append(nlc in london or fg == LONDON_FG)

    def route_ok(self, rc, xl, route, lon):
        if route == "any":
            return True
        if route == "noxlon":
            return rc in ANYPERM and (xl == "0" or lon)
        if rc == "00000":
            return True
        if route == "00000":
            return False
        if rc in ANYPERM:
            return True
        return route == "relaxed" and rc in self.notlondon and not lon

    def price(self, x, y, ticket, route="anyperm", p2p_first=False):
        """Lowest fare from station x to station y, with the supplying flow. None if no flow serves the pair."""
        tab = self.idx[ticket]
        bx, cx = self.codes[x]
        by, cy = self.codes[y]
        best = None
        best_p = None
        lon = (self.nlcs[x] in self.london) or (self.nlcs[y] in self.london)
        for a in bx + cx:
            pa = a in bx
            for b in by + cy:
                lst = tab.get((a, b))
                if not lst:
                    continue
                pp = pa and b in by
                for (v, rc, u, toc, fid, xl) in lst:
                    if not self.route_ok(rc, xl, route, lon):
                        continue
                    key = (v, 0 if u == "A" else 1, 0 if pp else 1, fid)
                    if best is None or key < best[0]:
                        best = (key, (v, toc, u, fid, rc, pp))
                    if pp and (best_p is None or key < best_p[0]):
                        best_p = (key, (v, toc, u, fid, rc, pp))
        if p2p_first and best_p is not None:
            return best_p[1]
        return None if best is None else best[1]

    def candidates(self, x, y, ticket):
        """Every flow serving x -> y with its sort key, cheapest first; flows that can never be admitted on a train
        (a route reading ONLY, or a route without location records other than NOT VIA LONDON) are left out."""
        tab = self.idx[ticket]
        bx, cx = self.codes[x]
        by, cy = self.codes[y]
        out = []
        for a in bx + cx:
            pa = a in bx
            for b in by + cy:
                for (v, rc, u, toc, fid, xl) in tab.get((a, b), ()):
                    if rc not in ANYPERM:
                        desc = self.rte.get(rc)
                        if desc is None or "ONLY" in desc.upper():
                            continue
                        if rc not in self.rte_locs and desc.upper() != "NOT VIA LONDON":
                            continue
                    pp = pa and b in by
                    out.append(((v, 0 if u == "A" else 1, 0 if pp else 1, fid), (v, toc, u, fid, rc, pp, xl)))
        out.sort()
        return [c[1] for c in out]

    def leg_ok(self, rc, xl, x, y, path):
        """Is a flow with route code rc and cross-London marker xl usable from x to y on a train whose stations
        between the two (inclusive) are path?"""
        ends_lon = self.is_lon[x] or self.is_lon[y]
        path_lon = ends_lon or any(self.is_lon[s] for s in path)
        if xl != "0" and not path_lon:
            return False
        if rc in ANYPERM:
            return True
        desc = self.rte.get(rc, "").upper()
        rl = self.rte_locs.get(rc)
        if rl is None:
            return desc == "NOT VIA LONDON" and not path_lon
        places = set()
        for s in path:
            places |= self.place[s]
        return rl["I"] <= places and not (rl["E"] & places)


def price_pairs(net, pairs, ticket, route, p2p_first):
    """Arrays over the pair list: fare (-1 unpriced), toc, usage (0 A, 1 G), fid, p2p."""
    P = len(pairs)
    fare = np.full(P, -1, np.int64)
    toc = np.empty(P, dtype=object)
    usage = np.full(P, -1, np.int8)
    fid = np.empty(P, dtype=object)
    p2p = np.zeros(P, np.int8)
    n = net.n
    for i, code in enumerate(pairs.tolist()):
        r = net.price(code // n, code % n, ticket, route, p2p_first)
        if r is None:
            continue
        fare[i] = r[0]
        toc[i] = r[1]
        usage[i] = 0 if r[2] == "A" else 1
        fid[i] = r[3]
        p2p[i] = 1 if r[5] else 0
    return {"fare": fare, "toc": toc, "usage": usage, "fid": fid, "p2p": p2p}


def combine_min(a, b):
    """Pairwise min of two priced pair arrays (ticket_min); ties keep the first ticket."""
    fa, fb = a["fare"], b["fare"]
    use_b = (fb >= 0) & ((fa < 0) | (fb < fa))
    out = {k: a[k].copy() for k in a}
    for k in out:
        out[k][use_b] = b[k][use_b]
    out["ticket_b"] = use_b
    return out


def legs(tri, n):
    o = tri // (n * n)
    b = (tri // n) % n
    d = tri % n
    return o, b, d


LEGKEYS = ("fare", "toc", "usage", "fid", "p2p")


def gather(pp, ix):
    return {k: pp[k][ix] for k in LEGKEYS}


def pair_index(tri, n, pairs):
    o, b, d = legs(tri, n)
    pos = {c: i for i, c in enumerate(pairs.tolist())}
    iob = np.fromiter((pos[c] for c in (o * n + b).tolist()), np.int64, len(tri))
    ibd = np.fromiter((pos[c] for c in (b * n + d).tolist()), np.int64, len(tri))
    iod = np.fromiter((pos[c] for c in (o * n + d).tolist()), np.int64, len(tri))
    return o, b, d, iob, ibd, iod


def cycle_core(o, b, d, ob, bd, od):
    """Per triangle from the three legs' arrays: delta, k, the A-only mask and the cluster-leg mask."""
    priced = (ob["fare"] >= 0) & (bd["fare"] >= 0) & (od["fare"] >= 0)
    delta = ob["fare"] + bd["fare"] - od["fare"]
    if MUT == "k1":
        k = np.ones(len(o), np.int64)
    else:
        k = np.fromiter((len({x, y, z}) for x, y, z in zip(ob["toc"], bd["toc"], od["toc"])), np.int64, len(o))
    allA = (ob["usage"] == 0) & (bd["usage"] == 0) & (od["usage"] == 0)
    clus = (ob["p2p"] == 0) | (bd["p2p"] == 0) | (od["p2p"] == 0)
    return {"o": o, "b": b, "d": d, "ob": ob, "bd": bd, "od": od, "priced": priced,
            "delta": delta, "k": k, "allA": allA, "cluster_leg": clus}


def cycle_table(tri, n, pairs, pp, pp_through=None):
    o, b, d, iob, ibd, iod = pair_index(tri, n, pairs)
    ct = cycle_core(o, b, d, gather(pp, iob), gather(pp, ibd), gather(pp_through if pp_through is not None else pp, iod))
    ct["iob"], ct["ibd"], ct["iod"] = iob, ibd, iod
    return ct


def price_on_trains(net, tri, n, order, reps, full_of, ticket, p2p_first=False):
    """Leg arrays for the 'compatible' route knob: each leg priced on the train that carries the triangle.
    p2p_first: the cheapest admitted point-to-point flow when one is admitted, else the cheapest admitted flow."""
    T = len(tri)
    out = {r: {"fare": np.full(T, -1, np.int64), "toc": np.empty(T, dtype=object), "usage": np.full(T, -1, np.int8),
               "fid": np.empty(T, dtype=object), "p2p": np.zeros(T, np.int8)} for r in ("ob", "bd", "od")}
    cand = {}
    path_cache = {}
    stats = Counter()
    for t in range(T):
        si, i, j, k = (int(v) for v in reps[t])
        s = order[si]
        fullp, pos = full_of[s]
        for role, a_, b_ in (("ob", i, j), ("bd", j, k), ("od", i, k)):
            x, y = s[a_][0], s[b_][0]
            key = (x, y)
            lst = cand.get(key)
            if lst is None:
                lst = net.candidates(x, y, ticket)
                cand[key] = lst
            hit = None
            for c in lst:
                v, toc, u, fid, rc, pp, xl = c
                if p2p_first and hit is not None and not pp:
                    continue  # already holding an admitted flow; only a point-to-point one can replace it
                if rc in ANYPERM and xl == "0":
                    ok = True
                else:
                    pk = (si, pos[a_], pos[b_])
                    path = path_cache.get(pk)
                    if path is None:
                        path = fullp[pos[a_]:pos[b_] + 1]
                        path_cache[pk] = path
                    ok = net.leg_ok(rc, xl, x, y, path)
                    if ok:
                        stats["admitted_after_path_check"] += 1
                        if rc not in ANYPERM:
                            stats["route_coded_admitted"] += 1
                    else:
                        stats["rejected_on_path"] += 1
                if not ok:
                    continue
                if hit is None or (p2p_first and pp and not hit[5]):
                    hit = c
                if not p2p_first or hit[5]:
                    break
            if hit is None:
                continue
            arr = out[role]
            arr["fare"][t] = hit[0]
            arr["toc"][t] = hit[1]
            arr["usage"][t] = 0 if hit[2] == "A" else 1
            arr["fid"][t] = hit[3]
            arr["p2p"][t] = 1 if hit[5] else 0
    return out, dict(stats)


def three_cells(delta, fl):
    return {"neg": int((delta < -fl).sum()), "zero_band": int((np.abs(delta) <= fl).sum()), "pos": int((delta > fl).sum())}


def quantiles(x):
    if len(x) == 0:
        return {}
    qs = (1, 5, 25, 50, 75, 95, 99)
    v = np.percentile(x, qs, method="lower")
    return {f"p{q:02d}": int(a) for q, a in zip(qs, v)}


def band(delta):
    """A delta band in pence, for single triangles in the record (no single fare is printed)."""
    if delta <= -5000:
        return "<= -5000"
    if delta <= -1000:
        return "(-5000, -1000]"
    if delta < -7.5:
        return "(-1000, -7.5)"
    if delta <= 7.5:
        return "[-7.5, 7.5]"
    if delta < 1000:
        return "(7.5, 1000)"
    if delta < 5000:
        return "[1000, 5000)"
    return ">= 5000"


def within_through(dA, kA, fod, fl):
    """Inside each through flow that has both one-setter and several-setter split points: the share below -floor
    in each group, compared flow by flow, and pooled over those flows."""
    if len(fod) == 0:
        return None
    order = np.argsort(fod.astype(str), kind="stable")
    f_sorted = fod[order].astype(str)
    starts = np.flatnonzero(np.r_[True, f_sorted[1:] != f_sorted[:-1]])
    ends = list(starts[1:]) + [len(order)]
    k_sorted, d_sorted = kA[order], dA[order]
    higher = lower = equal = 0
    n1s, n2s = [], []
    neg1 = tot1 = neg2 = tot2 = 0
    for a0, a1 in zip(starts, ends):
        kk = k_sorted[a0:a1]
        dd = d_sorted[a0:a1]
        m1 = kk == 1
        m2 = kk >= 2
        c1, c2 = int(m1.sum()), int(m2.sum())
        if not c1 or not c2:
            continue
        s1 = int((dd[m1] < -fl).sum())
        s2 = int((dd[m2] < -fl).sum())
        n1s.append(c1)
        n2s.append(c2)
        neg1 += s1
        tot1 += c1
        neg2 += s2
        tot2 += c2
        r1, r2 = s1 / c1, s2 / c2
        if r2 > r1:
            higher += 1
        elif r2 < r1:
            lower += 1
        else:
            equal += 1
    return {"through_flows_with_both": len(n1s), "k2plus_share_higher": higher, "k2plus_share_lower": lower,
            "equal": equal, "median_splits_k1": float(np.median(n1s)) if n1s else None,
            "median_splits_k2plus": float(np.median(n2s)) if n2s else None,
            "pooled_neg_share_k1": r6(neg1 / tot1) if tot1 else None,
            "pooled_neg_share_k2plus": r6(neg2 / tot2) if tot2 else None,
            "pooled_triangles_k1": tot1, "pooled_triangles_k2plus": tot2}


def summarise(ct, net, fl, dedupe="stations", noncarrier=frozenset()):
    """All the readings on one knob point."""
    m = ct["priced"]
    sel = np.flatnonzero(m)
    if dedupe == "flows":
        key = np.stack([np.array([hash(x) for x in ct[c]["fid"][sel]], dtype=np.int64) for c in ("ob", "bd", "od")], 1)
        _, first = np.unique(key, axis=0, return_index=True)
        sel = sel[np.sort(first)]
    delta = ct["delta"][sel]
    k = ct["k"][sel]
    A = ct["allA"][sel]
    out = {"triangles_total": int(len(ct["delta"])), "triangles_priced": int(m.sum()),
           "triangles_counted": int(len(sel)), "floor_pence": r6(fl)}
    out["all_priced"] = {"cells": three_cells(delta, fl), "exact_zero": int((delta == 0).sum()),
                         "by_k": {str(kk): three_cells(delta[k == kk], fl) for kk in (1, 2, 3)}}
    dA, kA = delta[A], k[A]
    selA = sel[A]
    out["A_only"] = {
        "n": int(len(dA)), "cells": three_cells(dA, fl),
        "beyond_floor": int((np.abs(dA) > fl).sum()),
        "share_beyond_floor": r6((np.abs(dA) > fl).mean()) if len(dA) else None,
        "exact_zero": int((dA == 0).sum()),
        "quantiles": quantiles(dA),
        "by_k": {str(kk): three_cells(dA[kA == kk], fl) for kk in (1, 2, 3)},
        "n_by_k": {str(kk): int((kA == kk).sum()) for kk in (1, 2, 3)},
        "exact_zero_by_k": {str(kk): int(((dA == 0) & (kA == kk)).sum()) for kk in (1, 2, 3)},
    }
    n1 = int((kA == 1).sum())
    n2 = int((kA >= 2).sum())
    s1 = (dA[kA == 1] < -fl).mean() if n1 else None
    s2 = (dA[kA >= 2] < -fl).mean() if n2 else None
    out["A_only"]["neg_share_k1"] = None if s1 is None else r6(s1)
    out["A_only"]["neg_share_k2plus"] = None if s2 is None else r6(s2)
    out["A_only"]["direction"] = None if (s1 is None or s2 is None) else ("lower" if s1 < s2 else "not lower")
    T_ob, T_bd, T_od = ct["ob"]["toc"][selA], ct["bd"]["toc"][selA], ct["od"]["toc"][selA]
    # control: drop triangles touching a non-carrier setter code
    if noncarrier:
        touch = np.array([(x in noncarrier) or (y in noncarrier) or (z in noncarrier) for x, y, z in zip(T_ob, T_bd, T_od)],
                         bool) if len(selA) else np.zeros(0, bool)
        keep = ~touch
        d2, k2 = dA[keep], kA[keep]
        c1 = (d2[k2 == 1] < -fl).mean() if (k2 == 1).any() else None
        c2 = (d2[k2 >= 2] < -fl).mean() if (k2 >= 2).any() else None
        used = sorted({x for x in np.concatenate([T_ob, T_bd, T_od]).tolist() if x in noncarrier}) if len(selA) else []
        out["A_only"]["control_no_noncarrier"] = {"n": int(keep.sum()), "neg_share_k1": None if c1 is None else r6(c1),
                                                 "neg_share_k2plus": None if c2 is None else r6(c2),
                                                 "noncarrier_codes_on_these_triangles": used}
    # by the setter of the through flow
    by_setter = {}
    for t in sorted(set(T_od.tolist())):
        mm = T_od == t
        c = three_cells(dA[mm], fl)
        c["k1"] = int((kA[mm] == 1).sum())
        by_setter[t] = c
    out["A_only"]["by_through_setter"] = by_setter
    out["A_only"]["setters_on_these_triangles"] = len(set(np.concatenate([T_ob, T_bd, T_od]).tolist())) if len(selA) else 0
    # by through flow: the most negative split, and the comparison inside one through flow
    fod = ct["od"]["fid"][selA]
    if len(fod):
        order = np.argsort(fod.astype(str), kind="stable")
        f_sorted = fod[order].astype(str)
        starts = np.flatnonzero(np.r_[True, f_sorted[1:] != f_sorted[:-1]])
        mins = np.minimum.reduceat(dA[order], starts)
        out["A_only"]["through_flows"] = {"n": int(len(starts)), "cells_of_min_split": three_cells(mins, fl)}
        out["A_only"]["within_through_flow"] = within_through(dA, kA, fod, fl)
    # largest |delta|: names, setter count, setters and a band
    if len(dA):
        o, b, d = ct["o"][selA], ct["b"][selA], ct["d"][selA]
        order = np.lexsort((d, b, o, -np.abs(dA)))[:20]
        top = []
        for i in order.tolist():
            top.append({"o": net.names[int(o[i])], "b": net.names[int(b[i])], "d": net.names[int(d[i])],
                        "delta_band": band(int(dA[i])), "k": int(kA[i]),
                        "setters": [T_ob[i], T_bd[i], T_od[i]]})
        out["A_only"]["top20_abs_delta"] = top
    out["cluster_leg_triangles"] = int(ct["cluster_leg"][sel].sum())
    return out


def arm0_pairs(ct, net, fl, robust=None):
    """Five distinct station triples for the retail check: most negative, exact zero, k = 1, k = 3, cluster leg.
    robust: optional mask of triangles whose three leg prices equal the lowest fare over every route code."""
    m = ct["priced"] & ct["allA"]
    if robust is not None:
        m = m & robust
    sel = np.flatnonzero(m)
    d = ct["delta"][sel]
    k = ct["k"][sel]
    cl = ct["cluster_leg"][sel]
    fod = ct["od"]["fid"][sel]
    so, sb, sd = ct["o"][sel], ct["b"][sel], ct["d"][sel]
    ftrip = ct["od"]["fare"][sel] * 10 ** 12 + ct["ob"]["fare"][sel] * 10 ** 6 + ct["bd"]["fare"][sel]
    picks = {}
    taken = np.zeros(len(sel), bool)

    def pick(name, mask, by):
        """Pick the extreme triangle not yet taken; triangles on the same through flow, with the same three fares,
        or sharing the split station and an end station (either way round) are then taken too, so the five checks
        do not repeat one fare."""
        idx = np.flatnonzero(mask & ~taken)
        if len(idx):
            w = idx[np.argmin(by[idx])]
            ends = {int(so[w]), int(sd[w])}
            taken[(fod == fod[w]) | (ftrip == ftrip[w])] = True
            taken[(sb == sb[w]) & (np.isin(so, list(ends)) | np.isin(sd, list(ends)))] = True
            picks[name] = int(sel[w])
    pick("most_negative", np.ones(len(sel), bool), d)
    pick("exact_zero", d == 0, -k)
    pick("k1", k == 1, d)
    pick("k3", k == 3, d)
    pick("cluster_leg", cl, d)
    out = {}
    for name, i in picks.items():
        out[name] = {"o": net.names[int(ct["o"][i])], "b": net.names[int(ct["b"][i])], "d": net.names[int(ct["d"][i])],
                     "through": int(ct["od"]["fare"][i]), "leg1": int(ct["ob"]["fare"][i]), "leg2": int(ct["bd"]["fare"][i]),
                     "delta": int(ct["delta"][i]), "k": int(ct["k"][i]), "tri_index": int(i),
                     "setters": [ct["ob"]["toc"][i], ct["bd"]["toc"][i], ct["od"]["toc"][i]]}
    return out


# ---------------------------------------------------------------------------
# G flows: the zero the rules build in


def _fg_members(loc):
    fgm = defaultdict(set)
    for nlc, v in loc.items():
        fg = v.get("fg", "")
        if fg and fg != nlc:
            fgm[fg].add(nlc)
    return fgm


def g_zero(idx_t, gflows_t, members, clusters, loc, cap=None):
    """For each live G flow: is there a junction where two flows of the same ticket sum exactly to its fare?
    Returns the counts and, per G flow, its class ('exact2', 'miss', 'nojunction') and the cheapest two-leg sum."""
    def eq(code):
        s = {code}
        fg = loc.get(code, {}).get("fg", "")
        if fg:
            s.add(fg)
        for c in list(s):
            s |= clusters.get(c, set())
        return s
    out_by = defaultdict(dict)
    in_by = defaultdict(dict)
    for (a, b), lst in idx_t.items():
        fares = {e[0] for e in lst}
        exp_b = {b} | members.get(b, set())
        exp_a = {a} | members.get(a, set())
        for x in exp_b:
            out_by[a].setdefault(x, set()).update(fares)
        for x in exp_a:
            in_by[b].setdefault(x, set()).update(fares)
    res = Counter()
    cls = []
    miss_by_toc = Counter()
    for gi, (O, D, v, route, toc, fid) in enumerate(gflows_t):
        if cap is not None and gi >= cap:
            break
        found = False
        any_j = False
        for a in eq(O):
            oa = out_by.get(a)
            if not oa:
                continue
            for dd in eq(D):
                idd = in_by.get(dd)
                if not idd:
                    continue
                small, big = (oa, idd) if len(oa) < len(idd) else (idd, oa)
                for x in small:
                    if x in (O, D) or x not in big:
                        continue
                    any_j = True
                    f1, f2 = oa[x], idd[x]
                    if any((v - u) in f2 for u in f1):
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if found:
            res["exact"] += 1
            cls.append(("exact2", None))
        elif any_j:
            res["no_exact_sum"] += 1
            miss_by_toc[toc] += 1
            best = None
            for a in eq(O):
                oa = out_by.get(a, {})
                for dd in eq(D):
                    idd = in_by.get(dd, {})
                    for x in (oa.keys() & idd.keys()) - {O, D}:
                        s2 = min(oa[x]) + min(idd[x])
                        if best is None or s2 < best:
                            best = s2
            res["miss_G_below_cheapest_two_leg_sum"] += int(v < best)
            res["miss_G_above_cheapest_two_leg_sum"] += int(v > best)
            res["miss_G_equal_cheapest_two_leg_sum"] += int(v == best)
            cls.append(("miss", best))
        else:
            res["no_junction"] += 1
            cls.append(("nojunction", None))
    return {"counts": dict(res), "no_exact_two_leg_by_setter": dict(miss_by_toc)}, cls, out_by, in_by, eq


def chain_graph(idx_t, members, loc):
    """Graph for the cheapest chain of flows: per code a standing node S, a departure node DEP and an arrival node
    ARR. S(m) -> DEP(a) when m is covered by a (a itself, its cluster members, its fare-group members);
    DEP(a) -> ARR(b) at the lowest fare from a to b; ARR(b) -> S(m) when m is covered by b."""
    from scipy.sparse import csr_matrix
    fgm = _fg_members(loc)

    def cov(c):
        s = {c} | members.get(c, set()) | fgm.get(c, set())
        for m in list(members.get(c, ())):
            s |= fgm.get(m, set())
        return s
    wmin = {}
    for (a, b), lst in idx_t.items():
        w = min(e[0] for e in lst)
        if (a, b) not in wmin or w < wmin[(a, b)]:
            wmin[(a, b)] = w
    codes = set()
    for a, b in wmin:
        codes.add(a)
        codes.add(b)
    covs = {}
    for c in list(codes):
        covs[c] = cov(c)
        codes |= covs[c]
    ids = {c: i for i, c in enumerate(sorted(codes))}
    N = len(ids)
    EPS = 1e-6
    rows, cols, ws = [], [], []
    mem_m, mem_a = [], []
    inv = defaultdict(set)
    for c, cv in covs.items():
        ci = ids[c]
        for m in cv:
            mi = ids[m]
            inv[m].add(c)
            rows.append(3 * mi)
            cols.append(3 * ci + 1)
            ws.append(EPS)
            mem_m.append(mi)
            mem_a.append(ci)
            rows.append(3 * ci + 2)
            cols.append(3 * mi)
            ws.append(EPS)
    fa, fb, fw = [], [], []
    for (a, b), w in wmin.items():
        rows.append(3 * ids[a] + 1)
        cols.append(3 * ids[b] + 2)
        ws.append(float(w))
        fa.append(ids[a])
        fb.append(ids[b])
        fw.append(float(w))
    g = csr_matrix((np.array(ws), (np.array(rows), np.array(cols))), shape=(3 * N, 3 * N))
    fa, fb, fw = np.array(fa), np.array(fb), np.array(fw)
    o = np.argsort(fb, kind="stable")
    fa, fb, fw = fa[o], fb[o], fw[o]
    starts = np.searchsorted(fb, np.arange(N + 1))
    return {"g": g, "ids": ids, "N": N, "covs": covs, "inv": inv, "mem_m": np.array(mem_m), "mem_a": np.array(mem_a),
            "fa": fa, "fw": fw, "starts": starts}


def cheapest_chains(CG, gflows_t, which):
    """Cheapest chain of two or more flows for each G flow listed in which (indices into gflows_t); inf if none."""
    from scipy.sparse.csgraph import dijkstra
    ids, N = CG["ids"], CG["N"]
    by_origin = defaultdict(list)
    for gi in which:
        by_origin[gflows_t[gi][0]].append(gi)
    out = {}
    for O, gis in by_origin.items():
        src_codes = CG["covs"].get(O, {O})
        src = sorted(ids[m] for m in src_codes if m in ids)
        if not src:
            for gi in gis:
                out[gi] = float("inf")
            continue
        dist = dijkstra(CG["g"], directed=True, indices=[3 * s for s in src], min_only=True)
        distS = dist[0::3].copy()
        distS[src] = np.inf
        d1dep = np.full(N, np.inf)
        np.minimum.at(d1dep, CG["mem_a"], distS[CG["mem_m"]])
        for gi in gis:
            D = gflows_t[gi][1]
            best = np.inf
            for b in CG["inv"].get(D, {D}):
                bi = ids.get(b)
                if bi is None:
                    continue
                s0, s1 = CG["starts"][bi], CG["starts"][bi + 1]
                if s1 > s0:
                    c = (d1dep[CG["fa"][s0:s1]] + CG["fw"][s0:s1]).min()
                    if c < best:
                        best = c
            out[gi] = float(best)
    return out


def three_leg(O, D, v, out_by, in_by, eq, cap_s=G_CAP_S):
    """Is there x, y with f(O, x) + f(x, y) + f(y, D) = v? Returns True, False, or None when the time cap cuts the
    search."""
    t0 = time.perf_counter()
    need = defaultdict(set)
    for dd in eq(D):
        for y, fs in in_by.get(dd, {}).items():
            if y in (O, D):
                continue
            for f3 in fs:
                if v - f3 > 0:
                    need[y].add(v - f3)
    if not need:
        return False
    for a in eq(O):
        for x, f1s in out_by.get(a, {}).items():
            if x in (O, D):
                continue
            if time.perf_counter() - t0 > cap_s:
                return None
            for c in eq(x):
                oc = out_by.get(c)
                if not oc:
                    continue
                for y in (oc.keys() & need.keys()):
                    if y == x:
                        continue
                    fms = oc[y]
                    nd = need[y]
                    for f1 in f1s:
                        if any((r - f1) in fms for r in nd):
                            return True
    return False


def g_classify(idx_t, gflows_t, members, clusters, loc, ckpt=None, cap_s=G_CAP_S, every=2000, sample_n=None):
    """Full B153-3 reading: two-leg exact, then the cheapest chain of any length, then the three-leg search on what
    is left. Resumable through ckpt (a JSON file holding the per-flow results so far)."""
    head, cls, out_by, in_by, eq = g_zero(idx_t, gflows_t, members, clusters, loc)
    todo = [gi for gi, (c, _b) in enumerate(cls) if c != "exact2"]
    CG = chain_graph(idx_t, members, loc)
    chains = cheapest_chains(CG, gflows_t, todo)
    done = {}
    if ckpt is not None and ckpt.exists():
        done = {int(k): v for k, v in json.loads(ckpt.read_text(encoding="utf-8")).items()}
    rest = [gi for gi in todo if not np.isinf(chains[gi]) and gflows_t[gi][2] >= round(chains[gi])]
    if sample_n is not None and sample_n < len(rest):
        import random
        searched = set(random.Random(G_SEED).sample(rest, sample_n))
    else:
        searched = set(rest)
    t0 = time.perf_counter()
    for n_, gi in enumerate(todo):
        if gi in done:
            continue
        O, D, v = gflows_t[gi][0], gflows_t[gi][1], gflows_t[gi][2]
        ch = chains[gi]
        if np.isinf(ch):
            done[gi] = "no_chain"
        elif v < round(ch):
            done[gi] = "below_chain"
        elif gi not in searched:
            done[gi] = "not_searched"
        else:
            r = three_leg(O, D, v, out_by, in_by, eq, cap_s)
            done[gi] = "exact3" if r is True else ("capped" if r is None else "untested_4plus")
        if ckpt is not None and (n_ % every == 0):
            write_json(ckpt, {str(k): x for k, x in done.items()})
            log(f"G flows: {len(done)} of {len(todo)} classified ({time.perf_counter() - t0:.0f} s)")
    if ckpt is not None:
        write_json(ckpt, {str(k): x for k, x in done.items()})
    cells = Counter(done.values())
    cells["exact2"] = sum(1 for c, _ in cls if c == "exact2")
    two = Counter(c for c, _ in cls)
    below_by = Counter(gflows_t[gi][4] for gi, c in done.items() if c == "below_chain")
    ends = Counter()
    for gi, c in done.items():
        O, D = gflows_t[gi][0], gflows_t[gi][1]
        kind = "an end is a cluster code" if (O in members or D in members) else "both ends are location codes"
        ends[(c, kind)] += 1
    head["cells_by_end_kind"] = {f"{c} | {k}": int(v) for (c, k), v in sorted(ends.items())}
    first = []
    for gi in sorted(gi for gi, c in done.items() if c == "below_chain")[:20]:
        O, D, v, route, toc, fid = gflows_t[gi]
        first.append({"origin": loc.get(O, {}).get("desc", O), "destination": loc.get(D, {}).get("desc", D),
                      "setter": toc, "route": route})
    head.update({"cells": {k: int(cells.get(k, 0)) for k in ("exact2", "exact3", "below_chain", "untested_4plus",
                                                               "capped", "no_chain", "not_searched")},
                 "three_leg_searched": len(searched), "three_leg_pool": len(rest), "three_leg_seed": G_SEED,
                 "two_leg_classes": dict(two), "below_chain_by_setter": dict(below_by),
                 "below_chain_first20": first, "g_flows": len(gflows_t), "three_leg_cap_seconds": cap_s})
    return head


def parse_tty(p):
    """Ticket code -> (class, type): class '1' first, '2' standard; type 'S' single, 'R' return, 'N' season."""
    out = {}
    for s in read_lines(p):
        if s.startswith("/") or len(s) < 45:
            continue
        out[s[1:4]] = (s[43], s[44])
    return out


def parse_ffl_full(p, gen, tickets):
    """Every flow with its dates (live, or starting after the generation date), and its fares of the listed tickets,
    restricted ones included: fid -> (o, d, route, usage, direction, toc, xlon, start, end), fid -> [(ticket, fare,
    restriction)]."""
    flows = {}
    fares = defaultdict(list)
    for s in read_lines(p):
        if s.startswith("/"):
            continue
        if s[1:2] == "F":
            flows[s[42:49]] = (s[2:6], s[6:10], s[10:15], s[18], s[19], s[36:39], s[39], dkey(s[28:36]), dkey(s[20:28]))
        elif s[1:2] == "T":
            t = s[9:12]
            if t in tickets:
                v = int(s[12:20])
                if v != 99999999:
                    fares[s[2:9]].append((t, v, s[20:22]))
    return flows, fares


def variant_index(flows, fares, gen, tickets, future=False, restricted=False):
    """Price index like parse_ffl's over a widened set: flows live on the generation date (and, with future, flows
    starting after it), fares of the listed tickets (with restricted, restriction codes too)."""
    idx = defaultdict(list)
    for fid, (o, d, route, usage, direction, toc, xl, start, end) in flows.items():
        live = start <= gen <= end
        if not (live or (future and start > gen)):
            continue
        for t, v, r in fares.get(fid, ()):
            if t not in tickets or (r.strip() and not restricted):
                continue
            add_fare(idx, o, d, direction, (v, route, usage, toc, fid, xl, t))
    return idx


def two_leg_tickets(idx, gl_sub, members, clusters, loc):
    """For each flow (O, D, v, ...): the ticket codes of the first exact two-leg sum found (junction and fares in
    sorted order), or None. Entries of idx carry the ticket in position 6."""
    def eq(code):
        s = {code}
        fg = loc.get(code, {}).get("fg", "")
        if fg:
            s.add(fg)
        for c in list(s):
            s |= clusters.get(c, set())
        return s
    out_t = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    in_t = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    for (a, b), lst in idx.items():
        for e in lst:
            for x in {b} | members.get(b, set()):
                out_t[a][x][e[0]].add(e[6])
            for x in {a} | members.get(a, set()):
                in_t[b][x][e[0]].add(e[6])
    res = []
    for (O, D, v, *_r) in gl_sub:
        hit = None
        for a in sorted(eq(O)):
            for dd in sorted(eq(D)):
                oa, idd = out_t.get(a, {}), in_t.get(dd, {})
                for x in sorted(oa.keys() & idd.keys() - {O, D}):
                    for u in sorted(oa[x]):
                        if (v - u) in idd[x]:
                            hit = (min(oa[x][u]), min(idd[x][v - u]))
                            break
                    if hit:
                        break
                if hit:
                    break
            if hit:
                break
        res.append(hit)
    return res


def gap_band(g):
    if g <= 50:
        return "(0, 50]"
    if g <= 200:
        return "(50, 200]"
    if g <= 500:
        return "(200, 500]"
    return "> 500"


#: classes of a G fare below every chain of live SDS flow fares, tried in this order; the first that gives an exact
#: two-leg sum names the class. Each widens the index the chain was taken over by one thing.
G_BELOW_VARIANTS = (
    ("next-round fares: an exact two-leg sum once flows starting after the generation date are read",
     {"tickets": ("SDS",), "future": True}),
    ("an Anytime Single (SOS) leg: an exact two-leg sum over SDS and SOS fares", {"tickets": ("SDS", "SOS")}),
    ("a restricted leg: an exact two-leg sum once SDS fares carrying a restriction code are read",
     {"tickets": ("SDS",), "restricted": True}),
    ("another standard-class single leg: an exact two-leg sum over every standard-class single ticket",
     {"tickets": "std_single"}),
)
G_BELOW_REST = "set below every sum of components in the file (no variant gives an exact two-leg sum)"


def g_below_classes(gl, below, chains, flows, fares, gen, members, clusters, loc, std_single):
    """Classes of the B153-3 FAIL cell (G fares below every chain of live SDS flow fares). For each variant: exact
    two-leg hits, hits at the fare plus one grid step (the chance level of an exact hit), and how many flows the
    variant's cheapest chain reaches (chain at or below the fare). First exact hit names the class."""
    sub = [gl[gi] for gi in below]
    cls = [None] * len(sub)
    variants = {}
    for name, spec in G_BELOW_VARIANTS:
        t0 = time.perf_counter()
        tk = std_single if spec["tickets"] == "std_single" else spec["tickets"]
        idx = variant_index(flows, fares, gen, set(tk), spec.get("future", False), spec.get("restricted", False))
        _h, c_exact, _ob, _ib, _eq = g_zero(idx, sub, members, clusters, loc)
        shifted = [(o, d, v + GRID, r, toc, fid) for (o, d, v, r, toc, fid) in sub]
        _h, c_ctrl, _ob, _ib, _eq = g_zero(idx, shifted, members, clusters, loc)
        ch = cheapest_chains(chain_graph(idx, members, loc), sub, range(len(sub)))
        exact = [c == "exact2" for c, _ in c_exact]
        newly = []
        for i, e in enumerate(exact):
            if e and cls[i] is None:
                cls[i] = name
                newly.append(i)
        pairs_t = Counter()
        if newly:
            for h in two_leg_tickets(idx, [sub[i] for i in newly], members, clusters, loc):
                pairs_t["unfound" if h is None else " + ".join(h)] += 1
        newly = len(newly)
        variants[name] = {"exact_two_leg": int(sum(exact)), "exact_two_leg_at_fare_plus_grid": int(sum(c == "exact2" for c, _ in c_ctrl)),
                          "cheapest_chain_reaches_fare": int(sum(1 for i, s in enumerate(sub) if s[2] >= round(ch[i]))),
                          "first_class_here": newly, "first_class_leg_tickets": dict(pairs_t.most_common(15)),
                          "index_code_pairs": len(idx), "seconds": round(time.perf_counter() - t0, 1)}
        log(f"G below variant done: {variants[name]}")
        del idx
    rest = [i for i, c in enumerate(cls) if c is None]
    for i in rest:
        cls[i] = G_BELOW_REST
    counts = Counter(cls)
    examples = defaultdict(list)
    for i, c in enumerate(cls):
        if len(examples[c]) < 5:
            O, D, v, route, toc, fid = sub[i]
            e = {"origin": loc.get(O, {}).get("desc", f"cluster {O}"), "destination": loc.get(D, {}).get("desc", f"cluster {D}"), "setter": toc,
                 "route": route, "gap_band_pence": gap_band(chains[below[i]] - v)}
            examples[c].append(e)
    # the remainder, broken down
    _h, c_base, _ob, _ib, _eq = g_zero(variant_index(flows, fares, gen, {"SDS"}), [sub[i] for i in rest], members, clusters, loc)
    rb = {"by_gap_band_pence": Counter(), "two_leg_junction": Counter(), "route": Counter(), "ends": Counter(),
          "setter": Counter(), "start_month": Counter()}
    for j, i in enumerate(rest):
        O, D, v, route, toc, fid = sub[i]
        rb["by_gap_band_pence"][gap_band(chains[below[i]] - v)] += 1
        rb["two_leg_junction"]["a junction exists, no two-leg sum equals the fare" if c_base[j][0] == "miss"
                               else "no two-leg junction in the file"] += 1
        rb["route"]["no-condition route (00000, 01000)" if route in ANYPERM else "a route code naming a route"] += 1
        rb["ends"]["an end is a cluster code" if (O in members or D in members) else "both ends are location codes"] += 1
        rb["setter"][toc] += 1
        rb["start_month"][flows[fid][7][:6]] += 1
    ratio = np.array([sub[i][2] / chains[below[i]] for i in rest]) if rest else np.zeros(0)
    remainder = {k: dict(v.most_common(12) if k in ("setter", "start_month") else sorted(v.items())) for k, v in rb.items()}
    remainder["fare_over_cheapest_chain_quantiles"] = ({f"p{q:02d}": r6(x) for q, x in zip((1, 5, 25, 50, 75, 95, 99),
                                                         np.percentile(ratio, (1, 5, 25, 50, 75, 95, 99)))} if len(ratio) else {})
    return {"flows": len(sub), "classes": {k: int(counts.get(k, 0)) for k in [n for n, _ in G_BELOW_VARIANTS] + [G_BELOW_REST]},
            "variants": variants, "examples": dict(examples), "remainder": remainder,
            "class_order": [n for n, _ in G_BELOW_VARIANTS] + [G_BELOW_REST]}


# ---------------------------------------------------------------------------
# criteria


def crit(name, kind, passed, detail, **extra):
    c = {"name": name, "kind": kind, "passed": passed, "detail": detail}
    c.update(extra)
    return c


def crit1(hash_ok, files, mca):
    bad = [f for f, v in files.items() if not (v["records"] == v["header"] and v["ends"])]
    mca_ok = mca["BS_open"] == mca["LT"] and mca["BS_unclosed"] == 0 and mca["LT_orphan"] == 0
    passed = bool(hash_ok["mismatch"] == 0 and hash_ok["checked"] > 0 and not bad and mca_ok)
    det = (f"{hash_ok['checked']} extracted members hashed, {hash_ok['mismatch']} differ from the manifest; "
           + "; ".join(f"{f}: {v['records']} records against header {v['header']}, end line {'present' if v['ends'] else 'missing'}" for f, v in sorted(files.items()))
           + f"; MCA: {mca['BS']} schedules, {mca['BS_open']} not cancelled, {mca['LT']} closed by LT, "
           f"{mca['BS_unclosed']} unclosed, {mca['LT_orphan']} orphan LT")
    return crit("B153-1", "instrument", passed, det)


MAP_B2 = {"no retail rows, or a listed triangle without its three legs": None,
          "a retail Anytime Day Single differs from the default-point price": False,
          "a leg without a retail Anytime Day Single whose shown price the feed does not hold at the lower of SDS and SOS": False,
          "every retail Anytime Day Single equals the default-point price; any leg without one has its shown price at "
          "the lower of SDS and SOS on the same train": True}
B2_ROLE = {"through": "through", "leg1": "leg1", "leg2": "leg2"}


def _eq(a, b):
    return True if MUT == "retail_eq" else a == b


def crit2(resolved, rows):
    """resolved: the listed triangles with their default-point leg prices ('through', 'leg1', 'leg2') and, under
    'min_ticket', the legs at the lower of SDS and SOS on the same train. rows: the stored retail readings, one per
    leg ('triangle', 'leg' ending in through/leg1/leg2, 'retail_anytime_pence' the Anytime Day Single or null,
    'retail_lowest_pence_if_different' the price shown when it differs)."""
    mapping = {k: ("PASS" if v else "FAIL" if v is False else "no verdict") for k, v in MAP_B2.items()}
    got = defaultdict(dict)
    for r in rows or ():
        if r["retail_anytime_pence"] is None and r["retail_lowest_pence_if_different"] is None:
            continue  # nothing read on this leg
        got[r["triangle"]][B2_ROLE[r["leg"].split()[-1]]] = r
    missing = [k for k in resolved if set(got.get(k, {})) != {"through", "leg1", "leg2"}]
    if not resolved or not rows or missing:
        state = "no retail rows, or a listed triangle without its three legs"
        return crit("B153-2", "instrument", MAP_B2[state], f"{len(rows or ())} retail rows for {len(resolved)} listed "
                    f"triangles; triangles without three legs: {missing}. State: {state}", mapping=mapping, state=state)
    eq_sds, differ, other_ok, other_bad = [], [], [], []
    for k in sorted(resolved):
        v = resolved[k]
        for role in ("through", "leg1", "leg2"):
            r = got[k][role]
            label = f"{k} {role} ({r['leg'].split()[0]})"
            if r["retail_anytime_pence"] is not None:
                (eq_sds if _eq(r["retail_anytime_pence"], v[role]) else differ).append(label)
            else:
                shown = r["retail_lowest_pence_if_different"]
                mt = v.get("min_ticket", {}).get(role)
                tick = v.get("min_ticket_code", {}).get(role)
                (other_ok if (shown is not None and _eq(shown, mt)) else other_bad).append(f"{label}, feed ticket {tick}")
    if differ:
        state = "a retail Anytime Day Single differs from the default-point price"
    elif other_bad:
        state = "a leg without a retail Anytime Day Single whose shown price the feed does not hold at the lower of SDS and SOS"
    else:
        state = ("every retail Anytime Day Single equals the default-point price; any leg without one has its shown "
                 "price at the lower of SDS and SOS on the same train")
    det = (f"{len(eq_sds) + len(differ) + len(other_ok) + len(other_bad)} retail legs over {len(resolved)} triangles: "
           f"Anytime Day Single equal to the default-point price {len(eq_sds)}, different {len(differ)} {differ}; legs "
           f"where retail shows no Anytime Day Single: shown price held by the feed at the lower of SDS and SOS on the "
           f"same train {len(other_ok)} {other_ok}, not held {len(other_bad)} {other_bad}. State: {state}")
    return crit("B153-2", "instrument", MAP_B2[state], det, mapping=mapping, state=state)


def crit3(gz):
    if not gz.get("g_flows"):
        return crit("B153-3", "known_answer", MAP_B3["no G flow"], "no live G flow", mapping=MAP_B3, state="no G flow")
    c = gz["cells"]
    if c["below_chain"] > 0:
        state = "some G fare below every chain of flow fares in the file"
    elif c["untested_4plus"] + c["capped"] + c["no_chain"] + c.get("not_searched", 0) == 0:
        state = "every G fare met by an exact two- or three-leg sum"
    else:
        state = "no fare below every chain, some untested at four legs or more"
    det = (f"live G flows {gz['g_flows']}: exact two-leg sum {c['exact2']}; exact three-leg sum {c['exact3']}; "
           f"below the cheapest chain of two or more flows of any length in the file {c['below_chain']}; "
           f"not met at two or three legs and not below the cheapest chain {c['untested_4plus']}; "
           f"three-leg search cut by its {gz['three_leg_cap_seconds']} s cap {c['capped']}; no chain in the file {c['no_chain']}; "
           f"at or above the cheapest chain and outside the seeded three-leg sample of {gz.get('three_leg_searched')} "
           f"(pool {gz.get('three_leg_pool')}) {c.get('not_searched', 0)}. "
           f"State: {state}. Below-chain flows by setter: {gz['below_chain_by_setter']}")
    return crit("B153-3", "known_answer", MAP_B3[state], det, mapping={k: ("PASS" if v else "FAIL" if v is False else "no verdict")
                                                                      for k, v in MAP_B3.items()},
                state=state, below_chain_first20=gz["below_chain_first20"])


RIVAL = {
    "rival_premise": "The fare is a scalar defined on stations along the direction of travel: f(x, y) = phi(y) - phi(x).",
    "rival_entailment": ("f(o, d) = phi(d) - phi(o) = [phi(b) - phi(o)] + [phi(d) - phi(b)] = f(o, b) + f(b, d), "
                         "so delta = 0; each fare rounded to the grid g moves by at most g/2, so |delta| <= 1.5 g."),
    "rival_shape": "point prediction (zero within the rounding floor)",
}


def crit4(A):
    n = A["n"]
    if n == 0:
        return crit("B153-4", "rival", None, "no triangle supplied by A flows only; nothing to read",
                    grid="unread", grid_note={"B": "not claimed: no triangle"}, mapping=MAP_B4, **RIVAL)
    over = A["beyond_floor"]
    holds = (n - over) / n
    passed = over > 0
    det = (f"{n} triangles supplied by A flows only; beyond the floor {over} ({A['share_beyond_floor']}); "
           f"cells {A['cells']}; exact zero {A['exact_zero']}; quantiles {A['quantiles']}")
    return crit("B153-4", "rival", passed, det, grid="B" if passed else "C",
                rival_holds_share=r6(holds), mapping=MAP_B4, **RIVAL)


def crit5(cells, total, k1_cells):
    keys = ("neg", "zero_band", "pos")
    mapping = {k: ("PASS" if v else "FAIL" if v is False else "no verdict") for k, v in MAP_B5.items()}
    if total <= 0 or not k1_cells or sum(k1_cells.get(k, 0) for k in keys) == 0:
        state = "no triangle, or no k = 1 triangle"
        return crit("B153-5", "own_reading", MAP_B5[state], f"cells {cells} against total {total}; k = 1 cells {k1_cells}. State: {state}",
                    mapping=mapping, state=state)
    if any(k not in cells for k in keys) or sum(cells[k] for k in keys) != total:
        state = "a cell missing or the cells do not sum to the count"
        return crit("B153-5", "own_reading", MAP_B5[state], f"cells {cells} against total {total}. State: {state}", mapping=mapping, state=state)
    both = k1_cells.get("neg", 0) > 0 and k1_cells.get("pos", 0) > 0
    state = ("cells sum to the count and both signs clear the floor at k = 1" if both
             else "cells sum to the count and one sign or none clears the floor at k = 1")
    det = (f"cells {cells} sum to {total} triangles. One-sided readings: subadditivity (delta >= 0) holds on "
           f"{cells['zero_band'] + cells['pos']}, fails on {cells['neg']}; the through-ticket-carries-more-rights reading "
           f"(delta <= 0) holds on {cells['neg'] + cells['zero_band']}, fails on {cells['pos']}. On one-setter (k = 1) "
           f"triangles supplied by A flows: {k1_cells}. State: {state}")
    return crit("B153-5", "own_reading", MAP_B5[state], det, mapping=mapping, state=state)


def crit6(points, brackets=None):
    dirs = {name: p["A_only"]["direction"] for name, p in points.items()}
    vals = set(dirs.values())
    if None in vals or len(vals) != 1:
        state = "direction flips or a cell is empty"
    elif vals == {"lower"}:
        state = "all points lower"
    else:
        state = "all points not lower"
    shares = {name: (p["A_only"]["neg_share_k1"], p["A_only"]["neg_share_k2plus"]) for name, p in points.items()}
    det = f"state: {state}; share of delta < -floor (k = 1, k >= 2) per knob point: {shares}"
    if brackets:
        bs = {name: (p["A_only"]["neg_share_k1"], p["A_only"]["neg_share_k2plus"], p["A_only"]["direction"]) for name, p in brackets.items()}
        det += f"; brackets (not knob values, not in the verdict): {bs}"
    return crit("B153-6", "own_reading", MAP_B6[state], det,
                mapping={k: ("PASS" if v else "FAIL" if v is False else "no verdict") for k, v in MAP_B6.items()},
                state=state)


def crit7_not_run(detail):
    """The railcard arm did not run in this pass: third state, no verdict."""
    return crit("B153-7", "known_answer", None, detail)


def crit8(rec):
    cfg = rec.get("config")
    cov = rec.get("coverage")
    ok = isinstance(cfg, dict) and bool(cfg) and isinstance(cov, dict) and bool(cov)
    return crit("B153-8", "bookkeeping", ok, f"config keys {sorted(cfg) if isinstance(cfg, dict) else None}; coverage keys {sorted(cov) if isinstance(cov, dict) else None}")


# ---------------------------------------------------------------------------
# run on the real files


def load_all():
    t0 = time.perf_counter()
    fd = RAW / "fares"
    td = RAW / "timetable"
    ffl = next(fd.glob("*.FFL"))
    gen = generation_key(ffl)
    loc = parse_loc(next(fd.glob("*.LOC")), gen)
    members, clusters = parse_fsc(next(fd.glob("*.FSC")), gen)
    fare_tocs = parse_toc(next(fd.glob("*.TOC")))
    rte, rte_locs = parse_rte(next(fd.glob("*.RTE")), gen)
    log(f"locations {len(loc)}, clusters {len(members)}, fare TOCs {len(fare_tocs)}, routes {len(rte)} ({len(rte_locs)} with locations)")
    idx, gflows, fcnt, has = parse_ffl(ffl, gen)
    log(f"flow file read: {dict(fcnt)}  ({time.perf_counter() - t0:.1f} s, peak {peak_mb():.0f} MB)")
    tip = parse_msn(next(td.glob("*.MSN")))
    crs2nlc = defaultdict(list)
    for nlc, v in loc.items():
        if v["crs"] and "+BUS" not in v["desc"]:
            crs2nlc[v["crs"]].append(nlc)
    ambiguous = sorted(c for c, v in crs2nlc.items() if len(v) > 1)
    nlcs = []
    sid_of_nlc = {}
    tip2sid = {}
    names = []
    unmapped_crs = Counter()
    crs_name = station_names(tip)
    for t, (crs, _nm, _minor) in sorted(tip.items()):
        nm = crs_name[crs]
        cand = crs2nlc.get(crs)
        if not cand:
            unmapped_crs[crs] += 1
            continue
        nlc = sorted(cand, key=lambda c: (loc[c]["fg"] != c, c))[0]
        if nlc not in sid_of_nlc:
            sid_of_nlc[nlc] = len(nlcs)
            nlcs.append(nlc)
            names.append(f"{nm} ({crs})")
        tip2sid[t] = sid_of_nlc[nlc]
    seqs, mcnt, unmapped_tip, full_of = parse_mca(next(td.glob("*.MCA")), tip2sid)
    log(f"timetable read: {dict(mcnt)}; distinct sequences {len(seqs)}; unmapped TIPLOCs {len(unmapped_tip)} ({time.perf_counter() - t0:.1f} s)")
    n = len(nlcs)
    tri = triples_from(seqs, n)
    o, b, d = legs(tri, n)
    pairs = np.unique(np.concatenate([o * n + b, b * n + d, o * n + d]))
    log(f"triangles {len(tri)}, pairs {len(pairs)} ({time.perf_counter() - t0:.1f} s, peak {peak_mb():.0f} MB)")
    london = frozenset(c for c, v in loc.items() if v["fg"] == LONDON_FG)
    notlondon = frozenset(r for r, desc in rte.items() if desc.upper() == "NOT VIA LONDON")
    net = Net(nlcs, loc, clusters, idx, names, london, notlondon, rte, rte_locs)
    nfo_pairs, nfo_cnt = parse_nfo(next(fd.glob("*.NFO")), gen)
    noncarrier = frozenset(k for k, v in fare_tocs.items() if not v["carrier"])
    rdesc = Counter()
    for r, desc in rte.items():
        rdesc[("ONLY" if "ONLY" in desc.upper() else "other") + ("_with_locations" if r in rte_locs else "_without_locations")] += 1
    meta = {"gen": gen, "fcnt": dict(fcnt), "mcnt": dict(mcnt), "n_stations": n, "n_sequences": len(seqs),
            "unmapped_tiploc": len(unmapped_tip), "unmapped_tiploc_first20": sorted(unmapped_tip)[:20],
            "unmapped_tiploc_calls": int(sum(unmapped_tip.values())),
            "msn_tiplocs": len(tip), "crs_not_in_loc": len(unmapped_crs), "crs_not_in_loc_first20": sorted(unmapped_crs)[:20],
            "crs_ambiguous": len(ambiguous), "crs_ambiguous_first20": ambiguous[:20],
            "locations_live": len(loc), "clusters_live": len(members), "routes_live": len(rte),
            "routes_by_kind": dict(rdesc),
            "not_london_routes": sorted(notlondon), "london_codes": len(london),
            "noncarrier_setters": sorted(noncarrier), "fare_tocs": len(fare_tocs),
            "nfo": dict(nfo_cnt), "triangles": int(len(tri)), "pairs": int(len(pairs))}
    return {"net": net, "tri": tri, "pairs": pairs, "gflows": gflows, "members": members, "clusters": clusters,
            "loc": loc, "nfo_pairs": nfo_pairs, "noncarrier": noncarrier, "meta": meta, "seqs": seqs,
            "full_of": full_of, "has": has}


def nfo_touch(net, pairs, nfo_pairs_t):
    if not nfo_pairs_t:
        return 0
    n = net.n
    hit = 0
    for code in pairs.tolist():
        x, y = divmod(code, n)
        bx, cx = net.codes[x]
        by, cy = net.codes[y]
        if any((a, b) in nfo_pairs_t for a in bx + cx for b in by + cy):
            hit += 1
    return hit


def unpriced_classes(net, pairs, pp, has):
    """Why a station pair has no default price: the strongest ticket presence over its code pairs."""
    n = net.n
    c = Counter()
    for i, code in enumerate(pairs.tolist()):
        if pp["fare"][i] >= 0:
            continue
        x, y = divmod(code, n)
        bx, cx = net.codes[x]
        by, cy = net.codes[y]
        m = 0
        for a in bx + cx:
            for b in by + cy:
                m |= has.get((a, b), 0)
        if m & HAS_SDS_ANY:
            c["SDS on a no-condition route, every such fare restricted"] += 1
        elif m & HAS_SDS_ROUTE:
            c["SDS only on flows whose route code names a route"] += 1
        elif m & HAS_SOS:
            c["SOS and no SDS"] += 1
        elif m:
            c["other ticket types only"] += 1
        else:
            c["no live fare on any station, fare-group or cluster code"] += 1
    return dict(c)


def priced_for(D, cache, cfg, route_key="route"):
    net, pairs = D["net"], D["pairs"]
    t = cfg["ticket"]
    if t == "min":
        a = priced_for(D, cache, dict(cfg, ticket="SDS"), route_key)
        b = priced_for(D, cache, dict(cfg, ticket="SOS"), route_key)
        return combine_min(a, b)
    key = (t, cfg[route_key], cfg["p2p_first"])
    if key not in cache:
        t0 = time.perf_counter()
        cache[key] = price_pairs(net, pairs, t, cfg[route_key], cfg["p2p_first"])
        log(f"priced pairs {key}: {int((cache[key]['fare'] >= 0).sum())} of {len(pairs)} ({time.perf_counter() - t0:.1f} s, peak {peak_mb():.0f} MB)")
    return cache[key]


def train_legs(D, cache, ticket, p2p_first):
    """Leg arrays on the trains, cached per (ticket, p2p_first); ticket 'min' takes the lower of SDS and SOS leg by
    leg (ties keep SDS)."""
    net, tri, n = D["net"], D["tri"], D["net"].n
    if ticket == "min":
        a, sa = train_legs(D, cache, "SDS", p2p_first)
        b, sb = train_legs(D, cache, "SOS", p2p_first)
        return {r: combine_min(a[r], b[r]) for r in ("ob", "bd", "od")}, {"SDS": sa, "SOS": sb}
    key = ("train", ticket, p2p_first)
    if key not in cache:
        if "reps" not in D:
            t0 = time.perf_counter()
            D["order"], D["reps"] = triple_reps(D["seqs"], n, tri)
            log(f"triangle representatives ({time.perf_counter() - t0:.1f} s, peak {peak_mb():.0f} MB)")
        t0 = time.perf_counter()
        cache[key] = price_on_trains(net, tri, n, D["order"], D["reps"], D["full_of"], ticket, p2p_first)
        log(f"legs priced on their trains {key}: {cache[key][1]} ({time.perf_counter() - t0:.1f} s, peak {peak_mb():.0f} MB)")
    return cache[key]


def compatible_table(D, cache, cfg):
    """Cycle table for route = compatible, and a mask of triangles whose three leg prices equal the lowest fare of
    the same ticket over every route code (so the retail cheapest of that ticket is the price read here)."""
    tri, n = D["tri"], D["net"].n
    lg, stats = train_legs(D, cache, cfg["ticket"], cfg["p2p_first"])
    o, b, d, iob, ibd, iod = pair_index(tri, n, D["pairs"])
    ct = cycle_core(o, b, d, lg["ob"], lg["bd"], lg["od"])
    ct["iob"], ct["ibd"], ct["iod"] = iob, ibd, iod
    robust = None
    if cfg["ticket"] != "min":
        F = priced_for(D, cache, dict(cfg, route="any"))["fare"]
        robust = (lg["ob"]["fare"] == F[iob]) & (lg["bd"]["fare"] == F[ibd]) & (lg["od"]["fare"] == F[iod])
    else:
        stats = dict(stats, legs_from_SOS=int(sum(lg[r]["ticket_b"].sum() for r in ("ob", "bd", "od"))))
    return ct, robust, stats


def arm0_feed(D, cache, a0):
    """For each listed triangle: the three legs on its train at the lower of SDS and SOS, with the ticket and route
    code that supply each (local cache only, for the retail check)."""
    lg, _ = train_legs(D, cache, "min", False)
    roles = (("through", "od"), ("leg1", "ob"), ("leg2", "bd"))
    for v in a0.values():
        t = v["tri_index"]
        v["min_ticket"] = {nm: int(lg[r]["fare"][t]) for nm, r in roles}
        v["min_ticket_code"] = {nm: ("SOS" if lg[r]["ticket_b"][t] else "SDS") for nm, r in roles}
        v["min_ticket_flow"] = {nm: lg[r]["fid"][t] for nm, r in roles}
    return a0


def run_one(D, cache, name, cfg):
    t0 = time.perf_counter()
    extra = {}
    if cfg["route"] == "compatible":
        ct, robust, stats = compatible_table(D, cache, cfg)
        extra["train_pricing"] = stats
        if robust is not None:
            extra["robust_triangles"] = int((robust & ct["priced"] & ct["allA"]).sum())
        if name == "default":
            a0 = arm0_feed(D, cache, arm0_pairs(ct, D["net"], floor_of(cfg["floor_mult"]), robust))
            write_json(CACHE / "arm0.json", a0)
        extra["pairs_priced"] = None
    else:
        pp = priced_for(D, cache, cfg)
        ppt = priced_for(D, cache, cfg, "through_route") if cfg.get("through_route") else None
        ct = cycle_table(D["tri"], D["net"].n, D["pairs"], pp, ppt)
        extra["pairs_priced"] = int((pp["fare"] >= 0).sum())
        extra["pairs_unpriced"] = int((pp["fare"] < 0).sum())
        if cfg["ticket"] == "min":
            extra["legs_from_SOS"] = int(pp["ticket_b"].sum())
        if name == "route_anyperm":
            extra["nfo_composite_pairs_touched"] = nfo_touch(D["net"], D["pairs"], D["nfo_pairs"].get("SDS", set()))
            extra["unpriced_pairs_by_reason"] = unpriced_classes(D["net"], D["pairs"], pp, D["has"])
    fl = floor_of(cfg["floor_mult"])
    s = summarise(ct, D["net"], fl, cfg["dedupe"], D["noncarrier"])
    s["config"] = cfg
    s.update(extra)
    return s, time.perf_counter() - t0


def run_points(D, names):
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = {}
    for name in names:
        f = CACHE / f"point_{name}.json"
        if f.exists():
            log(f"point {name}: cached, skipped")
            continue
        cfg = dict(DEFAULT, **(POINTS[name] if name in POINTS else BRACKETS[name]))
        s, dt = run_one(D, cache, name, cfg)
        write_json(f, s)
        log(f"point {name}: done ({dt:.1f} s, peak {peak_mb():.0f} MB); A-only {s['A_only']['n']}, "
            f"beyond floor {s['A_only']['beyond_floor']}, direction {s['A_only']['direction']}")


def run_b1():
    f = CACHE / "b1.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    man = json.loads((RAW / "b153_manifest.json").read_text(encoding="utf-8"))
    checked = mismatch = 0
    bad = []
    for pk in man["packages"]:
        for m in pk["members"]:
            p = RAW / pk["extract_dir"] / m["name"]
            checked += 1
            if not p.exists() or p.stat().st_size != m["bytes"] or sha256_file(p) != m["sha256"]:
                mismatch += 1
                bad.append(m["name"])
    files = {}
    for ext in ("FFL", "TTY", "TOC", "FSC"):
        p = next((RAW / "fares").glob(f"*.{ext}"))
        files[p.name] = file_check(p)
    out = {"hash": {"checked": checked, "mismatch": mismatch, "bad": bad}, "files": files}
    write_json(f, out)
    return out


def run_g(D):
    f = CACHE / "gzero_SDS.json"
    if f.exists():
        return
    t0 = time.perf_counter()
    gz = g_classify(D["net"].idx["SDS"], D["gflows"]["SDS"], D["members"], D["clusters"], D["loc"],
                    ckpt=CACHE / "gzero_SDS.partial.json", sample_n=G_SAMPLE)
    write_json(f, gz)
    log(f"G flows: {gz['cells']} ({time.perf_counter() - t0:.1f} s, peak {peak_mb():.0f} MB)")


def run_gbelow():
    """Classes of the B153-3 FAIL cell, from the G-flow search on disk (run --gflows first)."""
    f = CACHE / "gbelow_SDS.json"
    if f.exists():
        log("G below classes: cached, skipped")
        return
    t0 = time.perf_counter()
    part = json.loads((CACHE / "gzero_SDS.partial.json").read_text(encoding="utf-8"))
    below = sorted(int(k) for k, v in part.items() if v == "below_chain")
    fd = RAW / "fares"
    ffl = next(fd.glob("*.FFL"))
    gen = generation_key(ffl)
    loc = parse_loc(next(fd.glob("*.LOC")), gen)
    members, clusters = parse_fsc(next(fd.glob("*.FSC")), gen)
    tty = parse_tty(next(fd.glob("*.TTY")))
    std_single = sorted(t for t, (c, ty) in tty.items() if c == "2" and ty == "S")
    idx, gflows, _c, _h = parse_ffl(ffl, gen, tickets=("SDS",))
    gl = gflows["SDS"]
    flows, fares = parse_ffl_full(ffl, gen, set(std_single) | {"SDS", "SOS"})
    log(f"G below: {len(below)} flows; standard single tickets {len(std_single)}; flows {len(flows)} "
        f"({time.perf_counter() - t0:.1f} s, peak {peak_mb():.0f} MB)")
    chains = cheapest_chains(chain_graph(idx["SDS"], members, loc), gl, below)
    still = sum(1 for gi in below if gl[gi][2] < round(chains[gi]))
    out = g_below_classes(gl, below, chains, flows, fares, gen, members, clusters, loc, std_single)
    out["below_reproduced"] = still
    out["standard_single_tickets"] = len(std_single)
    out["seconds"] = round(time.perf_counter() - t0, 1)
    write_json(f, out)
    log(f"G below classes: {out['classes']} ({out['seconds']} s, peak {peak_mb():.0f} MB)")


def compare_v2():
    """Rule 19: every point here whose config equals a 2026-10-14 point, field by field."""
    out = {}
    skip = {"config", "train_pricing", "robust_triangles", "pairs_priced", "pairs_unpriced", "nfo_composite_pairs_touched",
            "unpriced_pairs_by_reason", "legs_from_SOS"}
    for new, old in V2_SAME.items():
        a, b = CACHE / f"point_{new}.json", CACHE_V2 / f"point_{old}.json"
        if not (a.exists() and b.exists()):
            continue
        A = json.loads(a.read_text(encoding="utf-8"))
        Bv = json.loads(b.read_text(encoding="utf-8"))
        diff = sorted(k for k in set(A) | set(Bv) if k not in skip and A.get(k) != Bv.get(k))
        out[new] = {"v2_point": old, "fields_compared": len((set(A) | set(Bv)) - skip), "fields_differing": diff}
    a0n, a0o = CACHE / "arm0.json", CACHE_V2 / "arm0.json"
    if a0n.exists() and a0o.exists():
        n_ = json.loads(a0n.read_text(encoding="utf-8"))
        o_ = json.loads(a0o.read_text(encoding="utf-8"))
        keys = ("o", "b", "d", "k", "setters", "through", "leg1", "leg2", "delta")
        out["arm0_list"] = {"same": all(n_.get(k, {}).get(x) == o_.get(k, {}).get(x) for k in o_ for x in keys) and set(n_) == set(o_)}
    return out


def assemble():
    meta = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
    b1 = json.loads((CACHE / "b1.json").read_text(encoding="utf-8"))
    points = {n: json.loads((CACHE / f"point_{n}.json").read_text(encoding="utf-8")) for n in POINTS if (CACHE / f"point_{n}.json").exists()}
    brackets = {n: json.loads((CACHE / f"point_{n}.json").read_text(encoding="utf-8")) for n in BRACKETS if (CACHE / f"point_{n}.json").exists()}
    gf = CACHE / "gzero_SDS.json"
    gz = json.loads(gf.read_text(encoding="utf-8")) if gf.exists() else None
    arm0 = json.loads((CACHE / "arm0.json").read_text(encoding="utf-8")) if (CACHE / "arm0.json").exists() else {}
    gb = CACHE / "gbelow_SDS.json"
    if gz is not None and gb.exists():
        gz["below_chain_classes"] = json.loads(gb.read_text(encoding="utf-8"))
    retail = json.loads(RETAIL.read_text(encoding="utf-8")) if RETAIL.exists() else {"rows": []}
    d = points["default"]
    anyp = points.get("route_anyperm", {})
    mca = {k: meta["mcnt"].get(k, 0) for k in ("BS", "BS_open", "LT", "BS_unclosed", "LT_orphan")}
    crits = [crit1(b1["hash"], b1["files"], mca), crit2(arm0, retail["rows"])]
    crits.append(crit3(gz) if gz else crit("B153-3", "known_answer", None, "G-flow search not on disk; not read"))
    crits += [crit4(d["A_only"]), crit5(d["all_priced"]["cells"], d["triangles_counted"], d["A_only"]["by_k"]["1"])]
    if len(points) == len(POINTS):
        crits.append(crit6(points, brackets))
    else:
        crits.append(crit("B153-6", "own_reading", None, f"only {len(points)} of {len(POINTS)} knob points on disk; not read"))
    crits.append(crit7_not_run("Railcard arm not run in this pass; the arms on the undiscounted fare ran first. No verdict."))
    rec = {
        "stage": STAGE,
        "config": {"fares_issue": "RJFAF917", "timetable_issue": "RJTTF988", "routeing_issue": "RJRG1095",
                   "generation_date": meta["gen"], "ticket": DEFAULT["ticket"], "route": DEFAULT["route"],
                   "default_ruled": "2026-10-27: routes compatible with the train; the no-condition route set is the knob point route_anyperm",
                   "anyperm_route_codes": sorted(ANYPERM),
                   "retail_check_source": {"file": "data/raw/rail_fares/b153_arm0_retail_20261027.json (local)",
                                           "read_on": retail.get("read_on"), "source": retail.get("source"),
                                           "rows": len(retail["rows"])},
                   "cluster_rule": "lowest fare among point-to-point, fare-group and cluster flows",
                   "restriction_codes": "blank only", "floor": "1.5 x grid of 5 pence",
                   "dedupe": "station triple", "knob_points": POINTS, "brackets": BRACKETS, "live_records_only": True,
                   "nfo_overlay": False, "triangle_rule": "o boards, b alights and boards, d alights, one public train",
                   "compatible_route_rule": ("each leg on the first calling sequence (sorted) yielding the triangle; route "
                                             "include/exclude locations met by the stations called at or passed; routes "
                                             "without locations only as NOT VIA LONDON off London; ONLY routes not "
                                             "admitted; cross-London flows only when an end or the path is in London"),
                   "g_three_leg_cap_seconds": G_CAP_S},
        "coverage": {"flow_file": meta["fcnt"], "timetable": meta["mcnt"], "stations": meta["n_stations"],
                     "calling_sequences": meta["n_sequences"], "msn_tiplocs": meta["msn_tiplocs"],
                     "tiplocs_called_without_station": meta["unmapped_tiploc"],
                     "tiplocs_called_without_station_first20": meta["unmapped_tiploc_first20"],
                     "calls_without_station": meta["unmapped_tiploc_calls"],
                     "crs_not_in_locations": meta["crs_not_in_loc"], "crs_not_in_locations_first20": meta["crs_not_in_loc_first20"],
                     "crs_with_several_nlc": meta["crs_ambiguous"], "crs_with_several_nlc_first20": meta["crs_ambiguous_first20"],
                     "locations_live": meta["locations_live"], "clusters_live": meta["clusters_live"],
                     "routes_live": meta["routes_live"], "routes_by_kind": meta["routes_by_kind"],
                     "not_london_route_codes": len(meta["not_london_routes"]),
                     "triangles": meta["triangles"], "station_pairs": meta["pairs"],
                     "station_pairs_unpriced_route_anyperm": anyp.get("pairs_unpriced"),
                     "station_pairs_unpriced_route_anyperm_by_reason": anyp.get("unpriced_pairs_by_reason"),
                     "nfo": meta["nfo"], "nfo_composite_pairs_touched_route_anyperm": anyp.get("nfo_composite_pairs_touched"),
                     "default_train_pricing": d.get("train_pricing"), "default_robust_triangles": d.get("robust_triangles"),
                     "fare_toc_records": meta["fare_tocs"], "noncarrier_setter_codes": meta["noncarrier_setters"]},
        "points": points,
        "brackets": brackets,
        "g_flow_zero_domain": gz,
        "retail_check_list": {k: {kk: v[kk] for kk in ("o", "b", "d", "k", "setters")} for k, v in arm0.items()},
        "rule19_vs_20261014": compare_v2(),
    }
    crits.append(crit8(rec))
    rec["criteria"] = crits
    text = json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    # the shared compare-and-swap writer when it sits next to the repository; otherwise a plain write
    sys.path.insert(0, str(ROOT.parent))
    try:
        from safe_write import create, rewrite
    except ImportError:
        create = rewrite = None
    if rewrite is None:
        OUT.write_text(text, encoding="utf-8", newline="\n")
    elif OUT.exists():
        rewrite(OUT, "B153 record", lambda _old: text, session=SESSION)
    else:
        create(OUT, "B153 record", text, session=SESSION)
    for c in crits:
        print(f"{c['name']} [{c['kind']}] {c['passed']}: {c['detail'][:300]}")
    return rec


def run_all(names=None, with_g=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    log("B1 checks")
    run_b1()
    D = load_all()
    write_json(CACHE / "meta.json", D["meta"])
    run_points(D, names or (list(POINTS) + list(BRACKETS)))
    if with_g:
        run_g(D)
    log(f"all done, peak {peak_mb():.0f} MB")


# ---------------------------------------------------------------------------
# selftest


def _fixture_net(fares, clusters=None, reversible=(), loc=None, rte=None, rte_locs=None):
    """fares: {(o, d): (fare, usage, toc, route[, xlon])} over codes; stations are the codes not starting with C."""
    idx = {"SDS": defaultdict(list)}
    for i, ((o, d), f) in enumerate(sorted(fares.items())):
        v, u, toc, route = f[:4]
        xl = f[4] if len(f) > 4 else "0"
        add_fare(idx["SDS"], o, d, "R" if (o, d) in reversible else "S", (v, route, u, toc, f"{i:07d}", xl))
    members = defaultdict(set)
    cl = defaultdict(set)
    for c, ms in (clusters or {}).items():
        for m in ms:
            members[c].add(m)
            cl[m].add(c)
    stations = sorted({x for k in fares for x in k if x[0] != "C"} | {m for ms in (clusters or {}).values() for m in ms})
    net = Net(stations, loc or {}, cl, idx, stations, rte=rte, rte_locs=rte_locs)
    return net, members, cl


def _additive(n=6, grid=5, bump=None):
    phi = [0, 137, 262, 411, 523, 688][:n]
    st = [f"S{i:03d}" for i in range(n)]
    fares = {}
    for i in range(n):
        for j in range(i + 1, n):
            v = int(round((phi[j] - phi[i]) / grid)) * grid
            fares[(st[i], st[j])] = (v, "A", "AAA" if (i + j) % 2 else "BBB", "00000")
    if bump:
        k, add = bump
        v, u, t, r = fares[k]
        fares[k] = (v + add, u, t, r)
    net, _, _ = _fixture_net(fares)
    n_ = net.n
    tri = np.array(sorted((i * n_ + j) * n_ + k for i in range(n_) for j in range(i + 1, n_) for k in range(j + 1, n_)), np.int64)
    o, b, d = legs(tri, n_)
    pairs = np.unique(np.concatenate([o * n_ + b, b * n_ + d, o * n_ + d]))
    pp = price_pairs(net, pairs, "SDS", "00000", False)
    ct = cycle_table(tri, n_, pairs, pp)
    return net, tri, pairs, pp, ct


def selftest():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    # B153-1: record counts, end line, hash
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        good = ["/!! Start of file", "/!! Records: 3", "RX1", "RX2", "RX3", "/!! End of file (13/10/2026)"]
        (td / "g.FFL").write_text("\n".join(good) + "\n", encoding="latin-1")
        (td / "a.FFL").write_text("\n".join(good[:3] + good[4:]) + "\n", encoding="latin-1")
        (td / "b.FFL").write_text("\n".join(good[:-1]) + "\n", encoding="latin-1")
        mca_ok = {"BS": 3, "BS_open": 2, "LT": 2, "BS_unclosed": 0, "LT_orphan": 0}
        h_ok = {"checked": 3, "mismatch": 0}
        check(crit1(h_ok, {"g": file_check(td / "g.FFL")}, mca_ok)["passed"] is True, "B1 clean fixture should pass")
        check(crit1(h_ok, {"a": file_check(td / "a.FFL")}, mca_ok)["passed"] is False, "B1 missing record should fail")
        check(crit1(h_ok, {"b": file_check(td / "b.FFL")}, mca_ok)["passed"] is False, "B1 missing end line should fail")
        check(crit1({"checked": 3, "mismatch": 1}, {"g": file_check(td / "g.FFL")}, mca_ok)["passed"] is False, "B1 hash mismatch should fail")
        check(crit1(h_ok, {"g": file_check(td / "g.FFL")}, dict(mca_ok, LT=1))["passed"] is False, "B1 unpaired BS should fail")
        # MCA parse: one schedule with a passing point, flags, cancel
        mca = [b"BSNX00001261013261212" + b" " * 58 + b"P",
               b"LOAAAAAAA 0800 0800" + b" " * 10 + b"TB" + b" " * 10,
               b"LIBBBBBBB 0810 0811      08100811" + b" " * 9 + b"T " + b" " * 10,
               b"LIPPPPPPP           0815 00000000" + b" " * 21,
               b"LICCCCCCC 0820 0821      08200000" + b" " * 9 + b"D " + b" " * 10,
               b"LTDDDDDDD 0830 0830" + b" " * 6 + b"TF",
               b"BSNX00002261013261212" + b" " * 58 + b"C"]
        (td / "x.MCA").write_bytes(b"\n".join(x.ljust(80) for x in mca) + b"\n")
        seqs, cnt, unm, full_of = parse_mca(td / "x.MCA", {"AAAAAAA": 0, "BBBBBBB": 1, "CCCCCCC": 2, "DDDDDDD": 3, "PPPPPPP": 4})
        check(cnt["BS_open"] == 1 and cnt["LT"] == 1, f"MCA counts {dict(cnt)}")
        check(seqs == {((0, 1), (1, 3), (2, 2), (3, 2))}, f"MCA sequence {seqs}")
        check(full_of.get(((0, 1), (1, 3), (2, 2), (3, 2))) == ((0, 1, 4, 2, 3), (0, 1, 3, 4)), f"MCA full path {full_of}")
        tri = triples_from(seqs, 5)
        check(sorted(tri.tolist()) == sorted([(0 * 5 + 1) * 5 + 2, (0 * 5 + 1) * 5 + 3]), f"triples {tri.tolist()}")
        order, reps = triple_reps(seqs, 5, tri)
        check(reps.tolist() == [[0, 0, 1, 2], [0, 0, 1, 3]], f"triple reps {reps.tolist()}")

    # B153-2, from stored retail rows
    res2 = {"x": {"through": 100, "leg1": 50, "leg2": 50, "min_ticket": {"through": 80, "leg1": 50, "leg2": 50},
                  "min_ticket_code": {"through": "SOS", "leg1": "SDS", "leg2": "SDS"}}}

    def rows2(through=100, leg1=50, leg2=50, shown=None):
        return [{"triangle": "x", "leg": "A-C through", "retail_anytime_pence": through, "retail_lowest_pence_if_different": shown},
                {"triangle": "x", "leg": "A-B leg1", "retail_anytime_pence": leg1, "retail_lowest_pence_if_different": None},
                {"triangle": "x", "leg": "B-C leg2", "retail_anytime_pence": leg2, "retail_lowest_pence_if_different": None}]
    check(crit2(res2, [])["passed"] is None, "B2 no retail should be None")
    check(crit2(res2, rows2()[:2])["passed"] is None, "B2 a missing leg should be None")
    check(crit2(res2, rows2())["passed"] is True, "B2 all equal should pass")
    check(crit2(res2, rows2(leg2=55))["passed"] is False, "B2 a differing Anytime Day Single should fail")
    check(crit2(res2, rows2(through=None, shown=80))["passed"] is True, "B2 a leg shown at the lower of SDS and SOS should pass")
    check(crit2(res2, rows2(through=None, shown=70))["passed"] is False, "B2 a shown price the feed does not hold should fail")
    check(crit2(res2, rows2(through=None, shown=None))["passed"] is None, "B2 a leg with nothing read should be None")

    # pricing: cluster and reverse
    net, members, cl = _fixture_net({("C001", "S002"): (300, "A", "AAA", "00000"), ("S003", "S001"): (200, "A", "BBB", "00000")},
                                    clusters={"C001": {"S001"}}, reversible={("S003", "S001")})
    i1, i2, i3 = net.nlcs.index("S001"), net.nlcs.index("S002"), net.nlcs.index("S003")
    r = net.price(i1, i2, "SDS")
    check(r is not None and r[0] == 300 and r[5] is False, f"cluster flow should price S001->S002, got {r}")
    r = net.price(i1, i3, "SDS")
    check(r is not None and r[0] == 200, f"reversible flow should price S001->S003, got {r}")
    # p2p first
    net, _, _ = _fixture_net({("C001", "S002"): (300, "A", "AAA", "00000"), ("S001", "S002"): (350, "A", "BBB", "00000")},
                             clusters={"C001": {"S001"}})
    a, b_ = net.nlcs.index("S001"), net.nlcs.index("S002")
    check(net.price(a, b_, "SDS")[0] == 300 and net.price(a, b_, "SDS", p2p_first=True)[0] == 350, "p2p knob")
    # route knob: an empty-route flow counts by default, not under 00000 only; a via-route flow never; 'any' takes it
    net, _, _ = _fixture_net({("S001", "S002"): (300, "A", "AAA", "01000"), ("S001", "S003"): (100, "A", "AAA", "00312")})
    a, b_, c_ = net.nlcs.index("S001"), net.nlcs.index("S002"), net.nlcs.index("S003")
    check(net.price(a, b_, "SDS") is not None and net.price(a, b_, "SDS", "00000") is None, "route knob on 01000")
    check(net.price(a, c_, "SDS") is None and net.price(a, c_, "SDS", "relaxed") is None, "via route must not price")
    check(net.price(a, c_, "SDS", "any")[0] == 100, "bracket 'any' admits every route")
    # compatible route: a via-route flow is admitted when the via station is on the path, refused when it is not;
    # an excluded station on the path refuses; a cross-London flow off London is refused; ONLY routes never
    rte = {"00000": "ANY PERMITTED", "00800": "VIA S005", "00900": "NOT VIA S006", "00048": "CHILTERN ONLY."}
    rl = {"00800": {"I": frozenset({"S005"}), "E": frozenset()}, "00900": {"I": frozenset(), "E": frozenset({"S006"})}}
    net, _, _ = _fixture_net({("S001", "S004"): (900, "A", "AAA", "00000", "1"), ("S002", "S004"): (500, "A", "AAA", "00800"),
                              ("S003", "S004"): (400, "A", "AAA", "00900"), ("S004", "S001"): (100, "A", "AAA", "00048"),
                              ("S005", "S006"): (1, "A", "AAA", "00000")}, rte=rte, rte_locs=rl)
    s1, s2, s3, s4, s5, s6 = (net.nlcs.index(f"S00{i}") for i in range(1, 7))
    check(net.leg_ok("00800", "0", s2, s4, (s2, s5, s4)) and not net.leg_ok("00800", "0", s2, s4, (s2, s6, s4)), "compatible: via")
    check(net.leg_ok("00900", "0", s3, s4, (s3, s5, s4)) and not net.leg_ok("00900", "0", s3, s4, (s3, s6, s4)), "compatible: not via")
    check(not net.leg_ok("00000", "1", s1, s4, (s1, s5, s4)), "compatible: cross-London flow off London refused")
    check(net.candidates(s4, s1, "SDS") == [], "compatible: ONLY routes never candidates")
    # legs on the train: point-to-point first, and the lower of SDS and SOS leg by leg (the default is compatible)
    check(DEFAULT["route"] == "compatible" and POINTS["route_anyperm"] == {"route": "anyperm"}, "default point is compatible")
    net, _, _ = _fixture_net({("C001", "S003"): (300, "A", "AAA", "00000"), ("S001", "S003"): (350, "A", "BBB", "00000"),
                              ("S001", "S002"): (100, "A", "AAA", "00000"), ("S002", "S003"): (120, "A", "AAA", "00000")},
                             clusters={"C001": {"S001"}})
    net.idx["SOS"] = defaultdict(list)
    add_fare(net.idx["SOS"], "S001", "S002", "S", (40, "00079", "A", "CCC", "0000099", "0"))
    seq = ((0, 1), (1, 3), (2, 2))
    Dt = {"net": net, "tri": triples_from({seq}, 3), "seqs": {seq}, "full_of": {seq: ((0, 1, 2), (0, 1, 2))}}
    lg0, _ = train_legs(Dt, {}, "SDS", False)
    lg1, _ = train_legs(Dt, {}, "SDS", True)
    check(int(lg0["od"]["fare"][0]) == 300 and int(lg1["od"]["fare"][0]) == 350, "train legs: p2p first on the train")
    rl_ = {"00079": {"I": frozenset({"S002"}), "E": frozenset()}}
    net.rte, net.rte_locs = {"00079": "VIA S002"}, rl_
    a0t = arm0_feed(Dt, {}, {"x": {"tri_index": 0}})
    check(a0t["x"]["min_ticket"] == {"through": 300, "leg1": 40, "leg2": 120} and a0t["x"]["min_ticket_code"]["leg1"] == "SOS",
          f"train legs: lower of SDS and SOS {a0t}")

    # B153-3: two-leg, three-leg, below every chain, and the untested rest
    gf_idx = defaultdict(list)
    gf_idx[("S001", "S002")].append((100, "00000", "A", "AAA", "0000001", "0"))
    gf_idx[("S002", "S003")].append((150, "00000", "A", "BBB", "0000002", "0"))
    gf_idx[("S003", "S004")].append((200, "00000", "A", "BBB", "0000003", "0"))

    def g3(gl):
        return crit3(g_classify(gf_idx, gl, {}, {}, {}, ckpt=None))
    check(g3([("S001", "S003", 250, "00000", "GGG", "0000009")])["passed"] is True, "B3 exact two-leg should pass")
    c3 = g3([("S001", "S004", 450, "00000", "GGG", "0000009")])
    check(c3["passed"] is True, f"B3 exact three-leg should pass {c3['detail']}")
    c3 = g3([("S001", "S004", 50, "00000", "GGG", "0000009")])
    check(c3["passed"] is False and len(c3["below_chain_first20"]) == 1, f"B3 fare below every chain should fail and be named {c3['detail']}")
    c3 = g3([("S001", "S004", 470, "00000", "GGG", "0000009")])
    check(c3["passed"] is None, f"B3 fare above the chain with no exact sum should be the third state {c3['detail']}")
    check(crit3({"g_flows": 0})["passed"] is None, "B3 no G flow should be None")
    # classes of the FAIL cell: a next-round leg, an SOS leg, and the rest
    gen_ = "20261013"
    live_, fut_ = ("20250302", "29991231"), ("20261101", "29991231")
    fl_ = {"0000001": ("S001", "S002", "00000", "A", "S", "AAA", "0") + live_, "0000002": ("S002", "S003", "00000", "A", "S", "AAA", "0") + live_,
           "0000003": ("S002", "S003", "00000", "A", "S", "AAA", "0") + fut_, "0000004": ("S001", "S003", "00000", "G", "S", "GGG", "0") + live_,
           "0000005": ("S005", "S006", "00000", "A", "S", "AAA", "0") + live_, "0000006": ("S006", "S007", "00000", "A", "S", "AAA", "0") + live_,
           "0000007": ("S005", "S007", "00000", "G", "S", "GGG", "0") + live_, "0000008": ("S008", "S009", "00000", "A", "S", "AAA", "0") + live_,
           "0000009": ("S009", "S010", "00000", "A", "S", "AAA", "0") + live_, "0000010": ("S008", "S010", "00000", "G", "S", "GGG", "0") + live_}
    fa_ = {"0000001": [("SDS", 100, "  ")], "0000002": [("SDS", 150, "  ")], "0000003": [("SDS", 100, "  ")],
           "0000004": [("SDS", 200, "  ")], "0000005": [("SDS", 40, "  "), ("SOS", 10, "  ")], "0000006": [("SDS", 40, "  ")],
           "0000007": [("SDS", 50, "  ")], "0000008": [("SDS", 40, "  ")], "0000009": [("SDS", 40, "  ")], "0000010": [("SDS", 60, "  ")]}
    gl_ = [(fl_[f][0], fl_[f][1], fa_[f][0][1], "00000", "GGG", f) for f in ("0000004", "0000007", "0000010")]
    bidx = variant_index(fl_, fa_, gen_, {"SDS"})
    ch_ = cheapest_chains(chain_graph(bidx, {}, {}), gl_, [0, 1, 2])
    check(all(gl_[i][2] < round(ch_[i]) for i in range(3)), f"G below fixture: all three below the live chain {ch_}")
    gbc = g_below_classes(gl_, [0, 1, 2], ch_, fl_, fa_, gen_, {}, {}, {}, ["SDS", "SOS"])
    want = [1, 1, 0, 0, 1]
    check([gbc["classes"][k] for k in gbc["class_order"]] == want, f"G below classes {gbc['classes']}")
    check(gbc["variants"][gbc["class_order"][1]]["first_class_leg_tickets"] == {"SOS + SDS": 1}, f"G below leg tickets {gbc['variants']}")

    # B153-4
    net, tri, pairs, pp, ct = _additive()
    s = summarise(ct, net, floor_of(1.5))
    c4 = crit4(s["A_only"])
    check(c4["passed"] is False and c4["grid"] == "C", f"B4 rounded additive table should fail {s['A_only']['cells']}")
    net, tri, pairs, pp, ct = _additive(bump=(("S000", "S003"), 20))
    s = summarise(ct, net, floor_of(1.5))
    check(crit4(s["A_only"])["passed"] is True and crit4(s["A_only"])["grid"] == "B", "B4 bumped fare should pass")
    check(crit4({"n": 0})["passed"] is None and crit4({"n": 0})["grid"] == "unread", "B4 empty should be None")

    # B153-5: the flag reads the k = 1 signs
    check(crit5({"neg": 2, "zero_band": 4, "pos": 3}, 9, {"neg": 1, "zero_band": 1, "pos": 2})["passed"] is True, "B5 both signs at k = 1")
    check(crit5({"neg": 2, "zero_band": 4, "pos": 3}, 9, {"neg": 0, "zero_band": 1, "pos": 2})["passed"] is False, "B5 one sign at k = 1 should fail")
    check(crit5({"neg": 1, "pos": 3}, 7, {"neg": 1, "zero_band": 0, "pos": 1})["passed"] is False, "B5 missing cell should fail")
    check(crit5({"neg": 1, "zero_band": 0, "pos": 3}, 4, {"neg": 0, "zero_band": 0, "pos": 0})["passed"] is None, "B5 no k = 1 should be None")
    s5 = summarise(ct, net, floor_of(1.5))
    c5 = crit5(s5["all_priced"]["cells"], s5["triangles_counted"], s5["A_only"]["by_k"]["1"])
    check(c5["passed"] is not None, f"B5 on fixture reads a state {c5['detail']}")

    # B153-6 on synthetic triangle tables: k = 1 all zero, k >= 2 negative
    def six(k1_neg, k2_neg):
        fares = {}
        st = [f"S{i:03d}" for i in range(4)]
        fares[(st[0], st[1])] = (100, "A", "AAA", "00000")
        fares[(st[1], st[2])] = (100, "A", "AAA", "00000")
        fares[(st[0], st[2])] = (200 + (30 if k1_neg else 0), "A", "AAA", "00000")
        fares[(st[1], st[3])] = (100, "A", "BBB", "00000")
        fares[(st[2], st[3])] = (100, "A", "BBB", "00000")
        fares[(st[0], st[3])] = (200 + (40 if k2_neg else 0), "A", "CCC", "00000")
        net, _, _ = _fixture_net(fares)
        n_ = net.n
        tri = np.array(sorted((i * n_ + j) * n_ + k for i in range(n_) for j in range(i + 1, n_) for k in range(j + 1, n_)), np.int64)
        o, b, d = legs(tri, n_)
        pairs = np.unique(np.concatenate([o * n_ + b, b * n_ + d, o * n_ + d]))
        pp = price_pairs(net, pairs, "SDS", "00000", False)
        return summarise(cycle_table(tri, n_, pairs, pp), net, floor_of(1.5))
    lo = six(False, True)
    hi = six(True, False)
    check(lo["A_only"]["n_by_k"]["1"] > 0, f"B6 fixture should have k = 1 triangles {lo['A_only']['n_by_k']}")
    check(crit6({"p": lo, "q": lo})["passed"] is True, f"B6 lower should pass {lo['A_only']['neg_share_k1']} {lo['A_only']['neg_share_k2plus']}")
    check(crit6({"p": hi, "q": hi})["passed"] is False, "B6 not lower should fail")
    check(crit6({"p": lo, "q": hi})["passed"] is None, "B6 flip should be None")
    # within one through flow: shares compared, not minima
    w = within_through(np.array([-20, 10, 10, 10, -20, -20]), np.array([1, 1, 1, 1, 2, 2]), np.array(["F"] * 6, dtype=object), 7.5)
    check(w["k2plus_share_higher"] == 1 and w["pooled_neg_share_k1"] == 0.25 and w["pooled_neg_share_k2plus"] == 1.0, f"within-flow shares {w}")

    # arm 0: five distinct triangles
    net, tri, pairs, pp, ct = _additive(bump=(("S000", "S003"), 20))
    a0 = arm0_pairs(ct, net, floor_of(1.5))
    keys = {(v["o"], v["b"], v["d"]) for v in a0.values()}
    check(len(keys) == len(a0), f"arm 0 triangles must be distinct {a0}")

    # B153-8
    check(crit8({"coverage": {"a": 1}})["passed"] is False, "B8 no config should fail")
    check(crit8({"config": {"a": 1}, "coverage": {}})["passed"] is False, "B8 empty coverage should fail")
    check(crit8({"config": {"a": 1}, "coverage": {"a": 1}})["passed"] is True, "B8 complete should pass")

    for m in fails:
        print("SELFTEST FAIL:", m)
    print(f"selftest: {len(fails)} failures" + (f" (mutation {MUT})" if MUT else ""))
    return 1 if fails else 0


def mutation_test():
    import subprocess
    bad = 0
    for m in ("k1", "floor0", "nocluster", "RasS", "retail_eq"):
        env = dict(os.environ, B153_MUT=m)
        r = subprocess.run([sys.executable, "-B", __file__, "--selftest"], env=env, capture_output=True, text=True, encoding="utf-8")
        caught = r.returncode != 0
        print(f"mutation {m}: {'caught' if caught else 'NOT CAUGHT'} ({r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''})")
        bad += not caught
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mutation", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--points", nargs="*")
    ap.add_argument("--gflows", action="store_true")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--gbelow", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.mutation:
        sys.exit(mutation_test())
    if a.gbelow:
        CACHE.mkdir(parents=True, exist_ok=True)
        run_gbelow()
        return
    if a.run or a.gflows:
        run_all(a.points, with_g=a.gflows)
        if a.run and not a.points:
            assemble()
        return
    if a.assemble:
        assemble()
        return
    ap.print_help()


if __name__ == "__main__":
    main()
