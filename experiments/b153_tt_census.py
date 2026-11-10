"""B153 pre-design census of the timetable package (counts only, nothing written).

Counts schedules, their public calling sequences, the distinct sequences, and
the number of (o, b, d) triples a train with n public calls yields, C(n, 3),
summed over distinct sequences. That number is the upper bound on the triangles
the station has to price, so the cost product can be multiplied out before any
fare is joined. Prints the pass time.

A call is public when the CIF record carries a public arrival or departure
other than '0000' (LO uses public departure, LT public arrival).

    python -I -B experiments/b153_tt_census.py [--dir data/raw/rail_fares/timetable]
"""
import argparse
import time
from collections import Counter
from math import comb
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parents[1] / "data" / "raw" / "rail_fares" / "timetable"))
    a = ap.parse_args()
    mca = next(Path(a.dir).glob("*.MCA"))
    t0 = time.perf_counter()
    n_bs = 0; n_stp = Counter(); seqs = Counter(); cur = None; bs_cancel = False
    with mca.open("rb") as f:
        for raw in f:
            rt = raw[:2]
            if rt == b"BS":
                n_bs += 1
                stp = raw[79:80].decode("latin-1")
                n_stp[stp] += 1
                bs_cancel = stp == "C"
                cur = [] if not bs_cancel else None
            elif cur is None:
                continue
            elif rt == b"LO":
                cur.append(raw[2:10].decode("latin-1").strip())
            elif rt == b"LI":
                pa, pd = raw[25:29], raw[29:33]
                if (pa.strip() and pa != b"0000") or (pd.strip() and pd != b"0000"):
                    cur.append(raw[2:10].decode("latin-1").strip())
            elif rt == b"LT":
                cur.append(raw[2:10].decode("latin-1").strip())
                seqs[tuple(cur)] += 1
                cur = None
    el = time.perf_counter() - t0
    tri = sum(comb(len(s), 3) for s in seqs)
    lens = Counter(len(s) for s in seqs)
    distinct_tiplocs = len({t for s in seqs for t in s})
    print(f"MCA {mca.stat().st_size:,} bytes, pass {el:.1f} s")
    print(f"schedules (BS) {n_bs}; STP indicator counts {dict(n_stp)}")
    print(f"completed non-cancel schedules {sum(seqs.values())}; distinct calling sequences {len(seqs)}; distinct TIPLOCs called {distinct_tiplocs}")
    print(f"sum C(n,3) over distinct sequences {tri:,}; max calls {max(lens)}; median calls {sorted(len(s) for s in seqs)[len(seqs)//2]}")
    uniq_tri = set()
    cap = 8_000_000  # memory guard: about 1 GB of tuples
    for s in seqs:
        n = len(s)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    uniq_tri.add((s[i], s[j], s[k]))
            if len(uniq_tri) > cap:
                break
        if len(uniq_tri) > cap:
            break
    print(f"distinct (o,b,d) TIPLOC triples {'>' if len(uniq_tri) > cap else ''}{len(uniq_tri):,}; total time {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
