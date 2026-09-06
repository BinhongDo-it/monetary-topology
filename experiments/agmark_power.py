"""Gate three for the eNAM carrier, computed from measured numbers not asserted.

agmark_support_floor.py measured, on untreated commodities across the thickness
gradient, the level of the support count and its month-on-month noise. This adds
the two things a power number needs and that the project insists on measuring
rather than assuming:

  - the serial correlation of the support series, so the effective number of
    independent observations is derived rather than taken as the month count
    (D22: the independent count is capped by structure, not by the nominal one);
  - the resulting detectable difference in mean log support, for a design that
    pools the treated commodities.

Nothing here scores any criterion. It says how big an effect this instrument
could see if one were there.
"""
import csv
import math
import pathlib
import statistics
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agmark"
MONTHS = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
N_TREATED = 11          # measured in the ledger: eNAM entrants with an Agmarknet series
Z90 = 1.645


def read(commodity):
    out = defaultdict(set)
    for f in sorted((DATA / commodity).glob("*.csv")):
        with f.open(encoding="utf-8", newline="") as fh:
            for row in csv.reader(fh):
                if len(row) < 10:
                    continue
                try:
                    a = float(row[5])
                except ValueError:
                    continue
                if a <= 0:
                    continue
                p = row[9].split()
                if len(p) != 3 or p[1] not in MONTHS:
                    continue
                out[(int(p[2]), MONTHS[p[1]])].add("%s|%s|%s" % (row[0], row[1], row[2]))
    return {k: len(v) for k, v in out.items()}


def acf1(x):
    n = len(x)
    m = sum(x) / n
    num = sum((x[i] - m) * (x[i + 1] - m) for i in range(n - 1))
    den = sum((v - m) ** 2 for v in x)
    return num / den if den else float("nan")


print("%-26s %6s %8s %8s %8s %9s %9s" %
      ("commodity", "months", "sd logS", "rho1", "N_eff", "se(mean)", "MDE 80%"))
out = []
for c in sorted(p.name for p in DATA.iterdir() if p.is_dir()):
    panel = read(c)
    ks = sorted(panel)
    s = [panel[k] for k in ks]
    if len(s) < 12:
        continue
    ls = [math.log(v) for v in s if v > 0]
    sd = statistics.stdev(ls)
    r = acf1(ls)
    n = len(ls)
    # Neff with an AR(1)-style inflation, floored at 1
    neff = n * (1 - r) / (1 + r) if r > -1 else float(n)
    neff = max(neff, 1.0)
    se = sd / math.sqrt(neff)
    out.append((c, n, sd, r, neff, se))
    print("%-26s %6d %8.4f %8.4f %8.1f %9.4f %9s" %
          (c, n, sd, r, neff, se, "-"))

print("\npooling the treated commodities: what difference in mean log support is visible")
print("  (se scales as 1/sqrt(N_TREATED); the per-commodity se is the measured one above)")
for c, n, sd, r, neff, se in out:
    se_pool = se / math.sqrt(N_TREATED)
    print("  if every treated commodity behaves like %-24s se_pool %.4f"
          % (c, se_pool))
    for power, z in [(0.50, 0.0), (0.80, 0.8416)]:
        mde = (Z90 + z) * se_pool
        print("      power %.2f -> detectable |d log support| %.4f  = %5.1f%% of the level"
              % (power, mde, 100 * (math.exp(mde) - 1)))
