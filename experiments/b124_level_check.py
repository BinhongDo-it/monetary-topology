"""B124: Theorem 46 read against the NHSBT matrix and the monitoring report's waiting times.

Theorem 46 (docs/b124_transport_dual.md): if centre levels are an allocation's shadow values,
centres joined through shared zones by routes in use have level differences equal to the
difference of the routes' terms. The National Liver Offering Scheme ranks DBD patients
nationally, so its route terms do not depend on the route, and centres so joined should have
equal levels. DCD stayed zonal, and so did DBD before 20 March 2018.

Two readings, both printed in full:

  structure  per year and donor type, from results/b124_nhsbt_matrix.json: the routes in use
             (cells not printed as 0, a "<5" cell counts as in use), the components, which
             centres share a component, and b1 = E - V + c of the routes in use;
  levels     per year and donor type, from Tables 16 and 17 of the report: each centre's median
             waiting time on the log scale, with the floor of its sampling error read from the
             published N and interquartile range (se = 1.2533 * (ln Q3 - ln Q1) / 1.349 / sqrt N,
             the normal-density approximation on the log scale), and the dispersion statistic
             Q = sum_j ((ln m_j - pooled mean) / se_j)^2 on 6 degrees of freedom.

Reading the waiting time as the shadow value is the step under test: Theorem 46 is about the
allocation's dual, and its consequence for waiting times holds to the extent that a centre's
waiting time is that dual.

Run:  python experiments/b124_level_check.py [--selftest]
"""

import argparse
import json
import math
import sys
from pathlib import Path

from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "results" / "b124_nhsbt_matrix.json"
OUT = ROOT / "results" / "b124_level_check.json"

CENTRES = ["Newcastle", "Leeds", "Cambridge", "Royal Free",
           "King’s College", "Birmingham", "Edinburgh"]
YEARS_MATRIX = ["2016/17", "2017/18", "2018/19", "2019/20"]
YEARS_WAIT = ["2017/18", "2018/19", "2019/20", "2020/21", "2021/22"]
POST = {"2018/19", "2019/20", "2020/21", "2021/22"}

# Tables 16 and 17 (pages 43 and 44): per centre and year, (N, median, Q1, Q3) in days.
WAIT = {
    "DBD": {
        "Newcastle":         [(30, 47, 17, 111), (22, 43, 17, 96), (26, 28.5, 14, 85), (27, 52, 20, 190), (23, 45, 13, 110)],
        "Leeds":             [(108, 64.5, 26, 228.5), (66, 41.5, 9, 145), (79, 33, 9, 136), (70, 52.5, 14, 159), (60, 27.5, 9, 113)],
        "Cambridge":         [(71, 74, 21, 200), (65, 36, 10, 88), (60, 17, 8.5, 67), (35, 23, 9, 76), (50, 37, 9, 90)],
        "Royal Free":        [(84, 99.5, 29.5, 236.5), (83, 33, 7, 133), (91, 37, 11, 96), (57, 39, 8, 95), (65, 28, 8, 154)],
        "King’s College": [(128, 125, 45, 374), (143, 54, 11, 252), (145, 54, 11, 164), (115, 32, 8, 140), (117, 33, 9, 98)],
        "Birmingham":        [(133, 48, 15, 137), (155, 42, 11, 105), (154, 58.5, 9, 204), (114, 71.5, 8, 262), (127, 34, 9, 146)],
        "Edinburgh":         [(81, 42, 12, 109), (88, 24.5, 6, 115.5), (52, 46.5, 19, 140), (58, 45.5, 9, 239), (39, 17, 7, 39)],
    },
    "DCD": {
        "Newcastle":         [(5, 106, 85, 304), (3, 304, 22, 452), (4, 144.5, 119, 371), (2, 110, 4, 216), (13, 152, 117, 394)],
        "Leeds":             [(26, 77.5, 13, 297), (21, 36, 12, 99), (21, 36, 12, 73), (15, 56, 26, 133), (16, 115.5, 52, 147)],
        "Cambridge":         [(32, 60, 28.5, 151.5), (40, 57.5, 21.5, 128), (33, 35, 14, 78), (35, 89, 46, 211), (48, 63, 21.5, 142.5)],
        "Royal Free":        [(13, 62, 24, 234), (28, 56.5, 29.5, 144), (37, 55, 23, 135), (11, 57, 23, 205), (23, 94, 27, 148)],
        "King’s College": [(46, 67, 27, 205), (38, 72.5, 34, 180), (37, 84, 38, 198), (31, 123, 54, 189), (46, 133.5, 52, 162)],
        "Birmingham":        [(52, 22.5, 13, 42.5), (38, 35.5, 16, 80), (33, 50, 30, 125), (11, 115, 7, 221), (25, 94, 60, 218)],
        "Edinburgh":         [(12, 41.5, 10, 94.5), (13, 71, 38, 333), (5, 51, 44, 151), (5, 42, 30, 777), (18, 52.5, 16, 151)],
    },
}


def structure(block):
    """Routes in use as a bipartite graph between zones and centres."""
    zones = list(block)
    edges = [(z, CENTRES[j]) for z in zones for j, v in enumerate(block[z]) if v != 0]
    verts = {("z", z) for z, _ in edges} | {("c", c) for _, c in edges}
    adj = {v: set() for v in verts}
    for z, c in edges:
        adj[("z", z)].add(("c", c))
        adj[("c", c)].add(("z", z))
    comps, seen = [], set()
    for v in sorted(verts):
        if v in seen:
            continue
        comp, stack = set(), [v]
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            stack.extend(adj[u] - comp)
        seen |= comp
        comps.append(sorted(c for k, c in comp if k == "c"))
    return {"routes_in_use": len(edges), "vertices": len(verts), "components": len(comps),
            "b1": len(edges) - len(verts) + len(comps),
            "centres_by_component": [c for c in comps if c],
            "all_centres_joined": any(len(c) == len(CENTRES) for c in comps)}


def levels(rows):
    """rows: [(centre, N, median, q1, q3)]. Returns per-centre log level, floor, and Q."""
    pts = []
    for c, n, m, q1, q3 in rows:
        se = 1.2533 * (math.log(q3) - math.log(q1)) / 1.349 / math.sqrt(n)
        pts.append({"centre": c, "N": n, "log_median": math.log(m), "se": se})
    w = [1 / p["se"] ** 2 for p in pts]
    mean = sum(wi * p["log_median"] for wi, p in zip(w, pts)) / sum(w)
    q = sum(wi * (p["log_median"] - mean) ** 2 for wi, p in zip(w, pts))
    df = len(pts) - 1
    sd = math.sqrt(sum((p["log_median"] - sum(x["log_median"] for x in pts) / len(pts)) ** 2
                       for p in pts) / df)
    return {"centres": pts, "pooled_log_mean": mean, "Q": q, "df": df, "Q_over_df": q / df,
            "p_equal": float(chi2.sf(q, df)), "sd_log_median": sd,
            "median_floor": sorted(p["se"] for p in pts)[len(pts) // 2]}


def build(matrix, wait):
    struct = {label: {y: structure(matrix["cells"][t][y]) for y in YEARS_MATRIX}
              for t, label in (("Table 1", "DBD"), ("Table 2", "DCD"))}
    lev = {label: {y: levels([(c, *wait[label][c][k]) for c in CENTRES])
                   for k, y in enumerate(YEARS_WAIT)} for label in ("DBD", "DCD")}
    joined_post = all(struct["DBD"][y]["all_centres_joined"] for y in ("2018/19", "2019/20"))
    pre = lev["DBD"]["2017/18"]["Q_over_df"]
    post = [lev["DBD"][y]["Q_over_df"] for y in ("2018/19", "2019/20")]
    dcd = [lev["DCD"][y]["Q_over_df"] for y in ("2018/19", "2019/20")]
    crit = [
        {"name": "B124-L1", "kind": "premise",
         "statement": "After the reform every DBD centre lies in one component of the routes in use",
         "passed": joined_post,
         "detail": {y: struct["DBD"][y]["centres_by_component"] for y in YEARS_MATRIX}},
        {"name": "B124-L2", "kind": "own_reading",
         "statement": "The DBD dispersion statistic Q/df is below its pre-reform value in both post-reform years with a matrix",
         "passed": all(v < pre for v in post),
         "detail": f"2017/18 {pre:.2f}; 2018/19 {post[0]:.2f}; 2019/20 {post[1]:.2f}"},
        {"name": "B124-L3", "kind": "own_reading",
         "statement": "In each post-reform year with a matrix the DBD Q/df is below the DCD Q/df",
         "passed": all(a < b for a, b in zip(post, dcd)),
         "detail": f"DBD {post[0]:.2f}, {post[1]:.2f}; DCD {dcd[0]:.2f}, {dcd[1]:.2f}"},
    ]
    return struct, lev, crit


def selftest(matrix):
    import copy
    struct, lev, crit = build(matrix, WAIT)
    w = copy.deepcopy(WAIT)
    for c in CENTRES:          # spread the post-reform DBD medians far apart
        for k in (1, 2):
            n, m, q1, q3 = w["DBD"][c][k]
            f = 3.0 ** CENTRES.index(c)
            w["DBD"][c][k] = (n, m * f, q1 * f, q3 * f)
    assert not build(matrix, w)[2][1]["passed"], "L2 did not flip on spread medians"
    m2 = copy.deepcopy(matrix)
    for z in m2["cells"]["Table 1"]["2018/19"]:
        row = m2["cells"]["Table 1"]["2018/19"][z]
        for j in range(len(row)):
            if z != CENTRES[j]:
                row[j] = 0       # cut every cross-zone route
    assert not build(m2, WAIT)[2][0]["passed"], "L1 did not flip on a zonal-only matrix"
    w = copy.deepcopy(WAIT)
    for c in CENTRES:          # make DCD post-reform medians identical
        for k in (1, 2):
            n, m, q1, q3 = w["DCD"][c][k]
            w["DCD"][c][k] = (n, 50, q1 * 50 / m, q3 * 50 / m)
    assert not build(matrix, w)[2][2]["passed"], "L3 did not flip on equal DCD medians"
    print("selftest: 3/3 seeds flip their flag")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if a.selftest:
        selftest(matrix)
        return 0
    struct, lev, crit = build(matrix, WAIT)
    print("structure of the routes in use")
    for label in ("DBD", "DCD"):
        for y in YEARS_MATRIX:
            s = struct[label][y]
            print(f"  {label} {y}  routes {s['routes_in_use']:2d}  vertices {s['vertices']:2d}  "
                  f"components {s['components']}  b1 {s['b1']:2d}  centres joined {s['all_centres_joined']}")
    print("levels: log median waiting time by centre, floor from N and IQR")
    for label in ("DBD", "DCD"):
        for y in YEARS_WAIT:
            L = lev[label][y]
            cells = "  ".join(f"{p['centre'][:4]} {math.exp(p['log_median']):6.1f}±{p['se']:.2f}" for p in L["centres"])
            tag = "post" if y in POST else "pre "
            print(f"  {label} {y} {tag}  sd {L['sd_log_median']:.3f}  floor {L['median_floor']:.3f}  "
                  f"Q/df {L['Q_over_df']:5.2f}  p {L['p_equal']:.2e}  | {cells}")
    for c in crit:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['name']}  [{c['kind']}]  {c['statement']}")
    rec = {"stage": "B124-L", "doc": "docs/b124_transport_dual.md",
           "config": {"floor": "se(ln median) = 1.2533 (ln Q3 - ln Q1) / 1.349 / sqrt N",
                      "in_use": "a cell not printed as 0, including <5",
                      "post_reform_years": sorted(POST)},
           "structure": struct, "levels": lev, "criteria": crit}
    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in crit) else 1


if __name__ == "__main__":
    sys.exit(main())
