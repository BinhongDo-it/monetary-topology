"""B153 pre-design census of the fares package (counts only, nothing written).

Answers, before any fare is read as a reading: how many flow and fare records
the file holds and whether that matches its header; how many flows carry a
fare-setter code, and how many are 'A' (a fare actually set) versus 'G'
(concatenated); how many distinct setters; the ticket codes that are standard
class singles with 'ANYTIME' in their description; and the price grid
(greatest common divisor of the fares) per such ticket code. Prints timings
per pass so the single-pass cost is measured, not guessed.

    python -I -B experiments/b153_census.py [--dir data/raw/rail_fares/fares]
"""
import argparse
import math
import time
from collections import Counter, defaultdict
from pathlib import Path


def read_lines(p: Path):
    with p.open("rb") as f:
        for raw in f:
            yield raw.decode("latin-1").rstrip("\r\n")


def header_records(p: Path):
    for s in read_lines(p):
        if not s.startswith("/"):
            return None
        if s.startswith("/!! Records:"):
            return int(s.split(":", 1)[1])
    return None


def last_line(p: Path) -> str:
    with p.open("rb") as f:
        f.seek(max(0, p.stat().st_size - 400))
        tail = f.read().decode("latin-1").splitlines()
    return tail[-1] if tail else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parents[1] / "data" / "raw" / "rail_fares" / "fares"))
    a = ap.parse_args()
    d = Path(a.dir)
    ffl = next(d.glob("*.FFL"))
    tty = next(d.glob("*.TTY"))
    toc = next(d.glob("*.TOC"))
    fsc = next(d.glob("*.FSC"))
    stem = ffl.stem
    gen_ddmmyyyy = None
    for s in read_lines(ffl):
        if s.startswith("/!! Generated:"):
            g = s.split(":", 1)[1].strip()
            gen_ddmmyyyy = g[6:10] + g[3:5] + g[0:2]
        if not s.startswith("/"):
            break
    print("file stem", stem, "generated (yyyymmdd)", gen_ddmmyyyy)

    # ticket types
    t0 = time.perf_counter()
    anytime = {}
    tty_n = 0
    for s in read_lines(tty):
        if s.startswith("/") or len(s) < 46:
            continue
        tty_n += 1
        code, end, start, desc, cls, typ = s[1:4], s[4:12], s[12:20], s[28:43], s[43], s[44]
        endk, startk = end[4:] + end[2:4] + end[:2], start[4:] + start[2:4] + start[:2]
        if not (startk <= gen_ddmmyyyy <= endk):
            continue
        if cls == "2" and typ == "S" and "ANY" in desc.upper():
            anytime[code] = desc.strip()
    print(f"TTY records {tty_n}, header {header_records(tty)}; standard singles with ANY in description, live on generation date: {len(anytime)}")
    for c in sorted(anytime):
        print(f"   {c} {anytime[c]}")

    # fare TOCs
    toc_f = [s for s in read_lines(toc) if not s.startswith("/") and s[:1] == "F"]
    print(f"TOC file: {len(toc_f)} F (fare TOC) records, header {header_records(toc)}")

    # clusters
    clusters = set()
    member_rows = 0
    for s in read_lines(fsc):
        if s.startswith("/"):
            continue
        member_rows += 1
        clusters.add(s[1:5])
    print(f"FSC: {len(clusters)} cluster ids, {member_rows} membership rows, header {header_records(fsc)}")
    print(f"   setup pass {time.perf_counter() - t0:.1f} s")

    # flow file, one pass
    t0 = time.perf_counter()
    nF = nT = 0
    usage = Counter(); toc_blank = 0; tocs = Counter(); direction = Counter(); route = Counter()
    nsd = Counter(); live = 0; origin_cluster = 0
    flow_meta = {}
    per_ticket = Counter(); grid = defaultdict(int); fare_99 = 0
    usage_by_toc_A = Counter()
    for s in read_lines(ffl):
        if s.startswith("/"):
            continue
        rt = s[1:2]
        if rt == "F":
            nF += 1
            o, dd, rc, u, di, end, start, tc, ns, fid = s[2:6], s[6:10], s[10:15], s[18], s[19], s[20:28], s[28:36], s[36:39], s[40], s[42:49]
            usage[u] += 1; direction[di] += 1; route[rc] += 1; nsd[ns] += 1
            if tc.strip() == "":
                toc_blank += 1
            tocs[tc] += 1
            if u == "A":
                usage_by_toc_A[tc] += 1
            if o in clusters or dd in clusters:
                origin_cluster += 1
            endk, startk = end[4:] + end[2:4] + end[:2], start[4:] + start[2:4] + start[:2]
            is_live = startk <= gen_ddmmyyyy <= endk
            live += is_live
            flow_meta[fid] = (u, is_live)
        elif rt == "T":
            nT += 1
            fid, code, fare = s[2:9], s[9:12], s[12:20]
            if code in anytime and fid in flow_meta and flow_meta[fid][1]:
                v = int(fare)
                if v == 99999999:
                    fare_99 += 1
                    continue
                per_ticket[(code, flow_meta[fid][0])] += 1
                grid[code] = math.gcd(grid[code], v)
    el = time.perf_counter() - t0
    print(f"FFL: {nF} flow + {nT} fare = {nF + nT} records; header {header_records(ffl)}; last line {last_line(ffl)!r}")
    print(f"   flow pass {el:.1f} s on {ffl.stat().st_size:,} bytes")
    print(f"   usage {dict(usage)}; live on generation date {live}; blank TOC {toc_blank}; distinct TOC codes {len(tocs)}")
    print(f"   distinct TOC codes on A flows {len(usage_by_toc_A)}; top 12 A-flow TOCs {usage_by_toc_A.most_common(12)}")
    print(f"   direction {dict(direction)}; NS_DISC_IND {dict(nsd)}; flows with a cluster at an end {origin_cluster}")
    print(f"   route codes: {len(route)} distinct; top 8 {route.most_common(8)}")
    print(f"   anytime-single fares on live flows by (ticket, usage): {sorted(per_ticket.items())}")
    print(f"   price grid (gcd, pence) per ticket: {dict(grid)}; 99999999 placeholders {fare_99}")


if __name__ == "__main__":
    main()
