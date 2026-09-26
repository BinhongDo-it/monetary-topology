"""B114, block zero: open the Sarafu transaction archive, check it against its own documentation,
and print what is in it.

What this is for. B114 asks whether money that enters one part of a payment network stays there
for as long as its holders take to spend it, or for as long as it takes to leave that part of the
network. Sarafu, a digital community currency used in Kenya from January 2020 to June 2021, is a
network in which both can be read from the same records: every transfer is on file with a
timestamp, new currency is marked as a disbursement, and every account carries an area and a
business type (Mattsson, Criscione and Ruddick, "Sarafu Community Inclusion Currency 2020-2021",
Scientific Data 9, 426, 2022; data on UK Data Service ReShare, record 855142).

This block reads the archive as it was downloaded, without unpacking it, and prints:
  0  the members of the archive, and the header of each table
  1  the checks the tables must pass before anything is read from them
  2  three totals the data descriptor states, recomputed from the transactions
  3  coverage: transactions by month and subtype, and accounts by area and area type
  4  the two clocks per area: days of balance against all transfers out, and against transfers
     to other areas, with the within-area share of transfer value
  5  new money by entry area: the share of each month's disbursements that is still in the area it
     entered, week by week, beside what a class chain built from the network's own flows gives and
     what a chain that pays every class's spending into one pool gives
  6  where the new money that leaves its entry area lands first, and whether that first stop passes it
     on: the share in the first stop and beyond it, observed and from both chains, and the mix of
     destinations among the money that has left
  7  the rules against the two clocks: each area's spending clock, out-of-area clock and reclaimed share
     by month, around 2020-10-19 (long-inactive accounts zeroed) and 2021-02-01 (2% monthly demurrage),
     and each entry month's cohort with the clocks of the weeks it lived through
  8  the chains of block 5 run wallet by wallet, with each wallet's spending speed taken from itself or
     from its area, and its payees taken from its own counterparts, from its area's mix, or from the
     whole network by receipts; the area-speed chains lump exactly to block 5's chains

Four criteria follow the objects (B114-1 to B114-4); they are computed from the same pass and
printed with --criteria, and --write puts the objects and the criteria into results/b114_sarafu.json.
The record takes about three minutes on two cores: B114-4 runs the wallet chains at 18 settings.

    python experiments/b114_sarafu.py              # blocks 0 to 8
    python experiments/b114_sarafu.py --criteria   # blocks 0 to 8, then the criteria
    python experiments/b114_sarafu.py --write      # the criteria, and the record written to results/
    python experiments/b114_sarafu.py --selftest   # seeded faults on synthetic archives and fixtures
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b114" / "raw"
ARCHIVE_NAME = "Sarafu2021_UKdb_submission_complete_d.zip"
MANIFEST = RAW / "manifest.json"

TXN_COLUMNS = ("id", "timeset", "transfer_subtype", "source", "target", "weight", "token_name")
USER_COLUMNS = ("id", "start", "final_bal", "area_name", "area_type", "held_roles", "business_type",
                "xDAI_blockchain_address")
# The archive's README lists the codes in capitals, and the table carries them that way; the
# descriptor's prose writes them in lower case. They are compared in capitals.
SUBTYPES = {"STANDARD", "DISBURSEMENT", "RECLAMATION", "AGENT_OUT"}
# README: "source - ... Unique identifier (xDAI_blockchain_address) of sender." Accounts are keyed
# by that address; the users table's own `id` is a database index and several staff rows share one
# wallet.
ACCOUNT_KEY = "xDAI_blockchain_address"

# Totals the data descriptor states (Scientific Data 9, 426, section "Technical Validation").
DESCRIPTOR = {
    "demurrage_expected": 352_806,        # expected fees of the 2% monthly demurrage from 2021-02-01
    "demurrage_reclaimed": 352_834,       # reclamations over 2021-02-01 to 2021-02-03
    "agent_out_total": 6_172_075,         # agent_out transactions from group accounts to the token agent
    "expected_total_balance": 19_419_736,  # inflow minus outflow over all accounts, held_role admin excluded
}


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def members(zf: zipfile.ZipFile) -> dict[str, str]:
    """The two tables, found by name pattern rather than by an assumed exact file name."""
    names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    txns = [n for n in names if "txns" in Path(n).name.lower()]
    users = [n for n in names if "users" in Path(n).name.lower()]
    out = {}
    if len(txns) == 1:
        out["txns"] = txns[0]
    if len(users) == 1:
        out["users"] = users[0]
    return out


def read_table(zf: zipfile.ZipFile, name: str) -> tuple[list[str], list[list[str]], list[str]]:
    problems = []
    raw = zf.read(name)
    text = raw.decode("utf-8-sig")
    if not text.endswith("\n"):
        problems.append(f"{name}: does not end with a newline")
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if r]
    if not rows:
        return [], [], problems + [f"{name}: empty"]
    header, body = rows[0], rows[1:]
    bad = sum(1 for r in body if len(r) != len(header))
    if bad:
        problems.append(f"{name}: {bad} row(s) with a column count other than the header's")
    return header, [r for r in body if len(r) == len(header)], problems


def parse_time(s: str) -> dt.datetime:
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"timestamp {s!r}")


class Archive:
    def __init__(self, path: Path):
        self.path = path
        self.problems: list[str] = []
        self.notes: list[str] = []
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad is not None:
                self.problems.append(f"archive member fails its CRC: {bad}")
            self.listing = [(i.filename, i.file_size) for i in zf.infolist()]
            found = members(zf)
            for key in ("txns", "users"):
                if key not in found:
                    self.problems.append(f"no single {key} table in the archive")
            self.txn_header, txn_rows, p1 = read_table(zf, found["txns"]) if "txns" in found else ([], [], [])
            self.user_header, user_rows, p2 = read_table(zf, found["users"]) if "users" in found else ([], [], [])
            self.problems += p1 + p2
        self.txns = self._txns(txn_rows)
        self.users = self._users(user_rows)
        if self.txns and self.users:
            self.check_endpoints()

    def _txns(self, rows):
        h = self.txn_header
        missing = [c for c in TXN_COLUMNS if c not in h]
        if missing:
            self.problems.append(f"transactions table has no {missing}")
            return []
        ix = {c: h.index(c) for c in TXN_COLUMNS}
        out, bad_time, bad_weight, bad_subtype, other_token = [], 0, 0, Counter(), Counter()
        for r in rows:
            try:
                t = parse_time(r[ix["timeset"]])
            except ValueError:
                bad_time += 1
                continue
            try:
                w = float(r[ix["weight"]])
            except ValueError:
                bad_weight += 1
                continue
            sub = r[ix["transfer_subtype"]].upper()
            if sub not in SUBTYPES:
                bad_subtype[sub] += 1
            token = r[ix["token_name"]]
            if token != "Sarafu":
                # the descriptor says the field was fixed as Sarafu; a row in another unit is not
                # part of the Sarafu ledger, so it is named and left out of every sum
                other_token[(token, sub, t.strftime("%Y-%m-%d"), w)] += 1
                continue
            try:
                order = int(r[ix["id"]])
            except ValueError:
                order = -1
            out.append((t, sub, r[ix["source"]], r[ix["target"]], w, order))
        if bad_time:
            self.problems.append(f"{bad_time} transaction(s) with an unreadable timestamp")
        if bad_weight:
            self.problems.append(f"{bad_weight} transaction(s) with a non-numeric amount")
        if any(w < 0 for _, _, _, _, w, _ in out):
            self.problems.append("negative transaction amounts")
        if bad_subtype:
            self.problems.append(f"unknown subtypes {dict(bad_subtype)}")
        for (token, sub, day, w), n in sorted(other_token.items()):
            self.notes.append(f"{n} row(s) in {token!r}, not Sarafu, left out: {sub} {w:g} on {day}")
        return out

    def _users(self, rows):
        """One entry per wallet address.

        Identical rows are one row. Rows that share an address and differ are allowed only when
        every one of them is a staff account (held role ADMIN): staff rows share wallets. Any other
        shared address is a problem, because the balance check would not know whose balance it is.
        """
        h = self.user_header
        missing = [c for c in USER_COLUMNS if c not in h]
        if missing:
            self.problems.append(f"users table has no {missing}")
            return {}
        ix = {c: h.index(c) for c in USER_COLUMNS}
        seen, identical = set(), 0
        by_key = defaultdict(list)
        for r in rows:
            if tuple(r) in seen:
                identical += 1
                continue
            seen.add(tuple(r))
            by_key[r[ix[ACCOUNT_KEY]]].append(r)
        if identical:
            self.notes.append(f"{identical} row(s) in the users table repeat an earlier row exactly, counted once")
        out, shared_staff = {}, 0
        for key, group in by_key.items():
            roles = {r[ix["held_roles"]].upper() for r in group}
            if len(group) > 1:
                if roles == {"ADMIN"}:
                    shared_staff += 1
                elif roles == {"NONE"}:
                    self.notes.append(f"{len(group)} account(s) created in error (held role None) share the address {key!r}")
                else:
                    self.problems.append(f"{len(group)} different non-staff rows share one address")
                    continue
            r = group[0]
            bals = {r_[ix["final_bal"]] for r_ in group}
            try:
                bal = float(r[ix["final_bal"]]) if len(bals) == 1 else None
            except ValueError:
                bal = None
            out[key] = {"final_bal": bal, "area_name": r[ix["area_name"]], "area_type": r[ix["area_type"]],
                        "held_roles": r[ix["held_roles"]].upper(), "business_type": r[ix["business_type"]],
                        "start": r[ix["start"]], "rows": len(group)}
        if shared_staff:
            self.notes.append(f"{shared_staff} staff wallet(s) carry more than one staff row")
        return out

    def check_endpoints(self) -> None:
        missing = Counter()
        for _, _, s, g, _, _ in self.txns:
            for a in (s, g):
                if a not in self.users:
                    missing[a] += 1
        if missing:
            self.problems.append(f"{sum(missing.values())} transaction endpoint(s) are not in the users table")


# ---------------------------------------------------------------------------
# Checks against the descriptor
# ---------------------------------------------------------------------------

def descriptor_totals(a: Archive) -> dict:
    demurrage = sum(w for t, sub, _, _, w, _ in a.txns
                    if sub == "RECLAMATION" and dt.datetime(2021, 2, 1) <= t < dt.datetime(2021, 2, 4))
    agent_out = sum(w for _, sub, _, _, w, _ in a.txns if sub == "AGENT_OUT")
    flow = defaultdict(float)
    for _, _, s, g, w, _ in a.txns:
        flow[s] -= w
        flow[g] += w
    admins = {u for u, v in a.users.items() if v["held_roles"] == "ADMIN"}
    total = sum(v for u, v in flow.items() if u not in admins and u in a.users)
    matched = mismatched = 0
    worst = 0.0
    for u, v in a.users.items():
        if u in admins or v["final_bal"] is None:
            continue
        d = abs(flow.get(u, 0.0) - v["final_bal"])
        worst = max(worst, d)
        if d <= 0.01:
            matched += 1
        else:
            mismatched += 1
    return {"demurrage_reclaimed": demurrage, "agent_out_total": agent_out,
            "balance_from_flows_excluding_admin": total, "accounts_matching_final_balance": matched,
            "accounts_not_matching_final_balance": mismatched, "worst_balance_gap": worst,
            "admins": len(admins)}


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def block0(a: Archive) -> None:
    print("== 0. archive members, and the header of each table")
    for name, size in a.listing:
        print(f"   {size:>12,d}  {name}")
    print(f"   transactions header: {a.txn_header}")
    print(f"   users header: {a.user_header}")


def block1(a: Archive) -> None:
    print("\n== 1. checks before reading")
    print(f"   {len(a.txns):,d} Sarafu transactions, {len(a.users):,d} wallets")
    for n in a.notes:
        print(f"   note: {n}")
    if a.problems:
        for p in a.problems:
            print(f"   PROBLEM {p}")
    else:
        print("   no problem found")


def block2(a: Archive) -> None:
    print("\n== 2. descriptor totals recomputed. Look at: each pair side by side")
    got = descriptor_totals(a)
    print(f"   demurrage reclaimed 2021-02-01 to 02-03: {got['demurrage_reclaimed']:,.2f} "
          f"(descriptor {DESCRIPTOR['demurrage_reclaimed']:,d}; expected fees {DESCRIPTOR['demurrage_expected']:,d})")
    print(f"   agent_out total: {got['agent_out_total']:,.2f} (descriptor {DESCRIPTOR['agent_out_total']:,d})")
    print(f"   balance from flows, admin accounts excluded: {got['balance_from_flows_excluding_admin']:,.2f} "
          f"(descriptor {DESCRIPTOR['expected_total_balance']:,d}; {got['admins']} admin accounts)")
    print(f"   accounts whose recomputed balance matches final_bal to 0.01: {got['accounts_matching_final_balance']:,d}; "
          f"not matching {got['accounts_not_matching_final_balance']:,d}; worst gap {got['worst_balance_gap']:,.2f}")


def block3(a: Archive) -> None:
    print("\n== 3. coverage. Look at: the first and last month of each subtype, and the thinnest areas")
    by_month = defaultdict(Counter)
    value = defaultdict(Counter)
    for t, sub, _, _, w, _ in a.txns:
        m = t.strftime("%Y-%m")
        by_month[m][sub] += 1
        value[m][sub] += w
    subs = ["STANDARD", "DISBURSEMENT", "RECLAMATION", "AGENT_OUT"]
    print("   month    " + "".join(f"{s:>14s}" for s in subs) + "   (count; value in thousand Sarafu)")
    for m in sorted(by_month):
        print(f"   {m}  " + "".join(f"{by_month[m][s]:>7d}/{value[m][s] / 1e3:>6.0f}" for s in subs))
    areas = Counter((v["area_name"], v["area_type"]) for v in a.users.values())
    print("\n   accounts by area and area type:")
    for (area, kind), n in areas.most_common():
        print(f"   {n:>7,d}  {area} / {kind}")
    kinds = Counter(v["business_type"] for v in a.users.values())
    print("\n   accounts by business type: " + ", ".join(f"{k} {n:,d}" for k, n in kinds.most_common()))
    roles = Counter(v["held_roles"] for v in a.users.values())
    print("   accounts by held role: " + ", ".join(f"{k} {n:,d}" for k, n in roles.most_common()))


SYSTEM_ROLES = {"ADMIN", "VENDOR", "TOKEN_AGENT"}


def class_of(u: dict) -> str:
    """Staff wallets, the in-kind vendor and the cash-out agents are one class, as in the holding
    period measurement on this data, which filters them out; every other wallet is its area."""
    if u["held_roles"] in SYSTEM_ROLES or u["business_type"].lower() == "system":
        return "system"
    return u["area_name"]


def class_clocks(a: Archive) -> dict:
    """Per class: time-average balance rebuilt from flows, transfer value out, and out to others.

    Transfers are STANDARD and AGENT_OUT; disbursements and reclamations move the balance but are
    not spending. Balances start at zero on 2020-01-25, the day the precursor tokens were converted.
    """
    cls = {k: class_of(v) for k, v in a.users.items()}
    txns = sorted(a.txns, key=lambda x: (x[0], x[5]))
    if not txns:
        return {}
    t0, t1 = txns[0][0], txns[-1][0]
    bal = defaultdict(float)
    area = defaultdict(float)          # integral of balance over time, Sarafu-days
    last = defaultdict(lambda: t0)
    out_all, out_other, within = defaultdict(float), defaultdict(float), defaultdict(float)
    for t, sub, s, g, w, _ in txns:
        cs, cg = cls[s], cls[g]
        for c in {cs, cg}:
            area[c] += bal[c] * (t - last[c]).total_seconds() / 86400
            last[c] = t
        bal[cs] -= w
        bal[cg] += w
        if sub in ("STANDARD", "AGENT_OUT"):
            out_all[cs] += w
            if cg == cs:
                within[cs] += w
            else:
                out_other[cs] += w
    days = (t1 - t0).total_seconds() / 86400
    out = {}
    for c in set(cls.values()):
        area[c] += bal[c] * (t1 - last[c]).total_seconds() / 86400
        avg = area[c] / days
        rate_all, rate_other = out_all[c] / days, out_other[c] / days
        if avg <= 0:
            # the system class pays new money in and has a negative balance: it has no holding period
            rate_all = rate_other = 0.0
        out[c] = {"wallets": sum(1 for v in cls.values() if v == c), "avg_balance": avg,
                  "final_balance": bal[c], "transfers_out": out_all[c], "to_other_classes": out_other[c],
                  "within_share": within[c] / out_all[c] if out_all[c] else None,
                  "days_all": avg / rate_all if rate_all else None,
                  "days_other": avg / rate_other if rate_other else None}
    return out


def block4(a: Archive) -> None:
    print("\n== 4. the two clocks per class. Look at: days@all against days@other, and the thinnest classes")
    got = class_clocks(a)
    print(f"   {'class':22s}{'wallets':>8s}{'avg bal':>11s}{'transfers':>12s}{'to others':>11s}{'within%':>9s}"
          f"{'days@all':>10s}{'days@other':>11s}")
    for c, v in sorted(got.items(), key=lambda kv: -kv[1]["transfers_out"]):
        def f(x, spec):
            return f"{'.':>{len(format(0, spec))}s}" if x is None else format(x, spec)
        print(f"   {c:22s}{v['wallets']:>8,d}{v['avg_balance'] / 1e3:>10.0f}k{v['transfers_out'] / 1e6:>11.2f}m"
              f"{v['to_other_classes'] / 1e6:>10.2f}m"
              f"{'.' if v['within_share'] is None else format(100 * v['within_share'], '8.1f'):>9s}"
              f"{'.' if v['days_all'] is None else format(v['days_all'], '10.1f'):>10s}"
              f"{'.' if v['days_other'] is None else format(v['days_other'], '11.1f'):>11s}")


CONVERSION_END = dt.datetime(2020, 1, 28)   # disbursements before this date convert precursor tokens
MIN_COHORT = 10_000.0                         # Sarafu disbursed into one area in one month
AGES = (0, 1, 2, 4, 8, 13, 26, 39, 52)       # weeks after the end of the entry month
WEEK = dt.timedelta(days=7)


def month_key(t: dt.datetime) -> str:
    return t.strftime("%Y-%m")


def month_end(key: str) -> dt.datetime:
    y, m = int(key[:4]), int(key[5:7])
    return dt.datetime(y + (m == 12), m % 12 + 1, 1)


def tag_pass(a: Archive):
    """Follow each month's new money, by the area it entered, through every later transfer.

    A wallet's balance is treated as well mixed: a transfer out carries each tag in proportion to
    that wallet's balance. System wallets stand outside circulation: what they disburse enters it,
    what reaches them leaves it. Disbursements before CONVERSION_END convert precursor tokens and
    carry no tag. Returns the class order, the cohort list, weekly holdings by class and cohort,
    the removal by cohort, the disbursed amount by cohort, end-of-day class balances and the flows
    between classes by quarter.
    """
    import numpy as np
    cls = {k: class_of(v) for k, v in a.users.items()}
    classes = sorted({c for c in cls.values() if c != "system"})
    ci = {c: i for i, c in enumerate(classes)}
    txns = sorted(a.txns, key=lambda x: (x[0], x[5]))
    months = sorted({month_key(t) for t, *_ in txns if t >= CONVERSION_END})
    mi = {m: i for i, m in enumerate(months)}
    C, M = len(classes), len(months)
    wallets = sorted(a.users)
    wi = {w: i for i, w in enumerate(wallets)}
    wclass = np.array([ci.get(cls[w], -1) for w in wallets])
    tag = np.zeros((len(wallets), C * M))
    mov = np.zeros((len(wallets), C * M))      # the part of `tag` that has been paid on at least once
    has = np.zeros(len(wallets), dtype=bool)
    bal = np.zeros(len(wallets))
    removed = np.zeros(C * M)
    disbursed = np.zeros(C * M)
    moved_within = np.zeros(C * M)     # tagged value paid between two wallets of the same class
    moved_across = np.zeros(C * M)     # tagged value paid to a wallet of another class
    snaps_within, snaps_across, snaps_moved = [], [], []
    guard = {"events": 0, "shortfall": 0.0}
    t0 = txns[0][0]
    snap_times = []
    t_next = dt.datetime(t0.year, t0.month, t0.day) + WEEK
    snaps = []
    members = [np.where(wclass == i)[0] for i in range(C)]
    day0 = dt.datetime(t0.year, t0.month, t0.day)
    n_days = (txns[-1][0] - day0).days + 1
    class_bal = np.zeros((n_days, C))
    cbal = np.zeros(C)
    last_day = 0
    flows = defaultdict(lambda: np.zeros((C, C + 1)))   # quarter -> [from class, to class or sink]
    day_flows = np.zeros((n_days, C, C + 2))   # day -> [from class, to class | transfers to system | reclaimed]

    def quarter(t):
        return f"{t.year}Q{(t.month - 1) // 3 + 1}"

    for t, sub, s, g, w, _ in txns:
        while t >= t_next:
            snaps.append(np.stack([tag[members[i]].sum(axis=0) for i in range(C)]))
            snaps_moved.append(np.stack([mov[members[i]].sum(axis=0) for i in range(C)]))
            snaps_within.append(moved_within.copy())
            snaps_across.append(moved_across.copy())
            snap_times.append(t_next)
            t_next += WEEK
        d = (t - day0).days
        if d > last_day:
            class_bal[last_day:d] = cbal
            last_day = d
        i, j = wi[s], wi[g]
        cs, cg = wclass[i], wclass[j]
        if cs < 0 and cg < 0:
            continue
        if cs < 0:                                   # enters circulation
            bal[j] += w
            cbal[cg] += w
            if sub == "DISBURSEMENT" and t >= CONVERSION_END:
                k = cg * M + mi[month_key(t)]
                tag[j, k] += w
                disbursed[k] += w
                has[j] = True
            continue
        # leaves wallet i
        if bal[i] <= 0 or w > bal[i] + 1e-9:
            guard["events"] += 1
            guard["shortfall"] += w - max(bal[i], 0.0)
            frac = 1.0
        else:
            frac = w / bal[i]
        if has[i]:
            moved = tag[i] * frac
            tag[i] -= moved
            mov[i] -= mov[i] * frac
        else:
            moved = None
        bal[i] -= w
        cbal[cs] -= w
        q = quarter(t)
        if sub in ("STANDARD", "AGENT_OUT"):
            flows[q][cs, C if cg < 0 else cg] += w
            day_flows[d, cs, C if cg < 0 else cg] += w
        if cg < 0:                                   # leaves circulation
            if moved is not None:
                removed += moved
            if sub == "RECLAMATION":
                flows[q][cs, C] += w
                day_flows[d, cs, C + 1] += w
            continue
        bal[j] += w
        cbal[cg] += w
        if moved is not None:
            tag[j] += moved
            mov[j] += moved
            has[j] = True
            if sub in ("STANDARD", "AGENT_OUT"):
                if cs == cg:
                    moved_within += moved
                else:
                    moved_across += moved
    class_bal[last_day:] = cbal
    # tagged value enters only by disbursement and leaves only by removal, so what each cohort
    # disbursed must equal what is still tagged plus what was removed
    residual = disbursed - removed - tag.sum(axis=0)
    worst = float(np.abs(residual).max()) if residual.size else 0.0
    if worst > 1e-6 * max(1.0, float(disbursed.max(initial=0.0))):
        raise AssertionError(f"tagged value is not conserved: worst cohort residual {worst:.6g}")
    return {"conservation_residual": worst, "classes": classes, "months": months, "snaps": np.array(snaps), "snap_times": snap_times,
            "removed": removed, "disbursed": disbursed, "guard": guard, "class_bal": class_bal,
            "snaps_within": np.array(snaps_within), "snaps_across": np.array(snaps_across),
            "snaps_moved": np.array(snaps_moved),
            "day0": day0, "flows": dict(flows), "day_flows": day_flows}


def period_bounds(key):
    """A flow window named "2020Q3" (a quarter) or "2020H2" (a half-year): its first day, the day
    after its last, and the quarters it is made of."""
    y, kind, n = int(key[:4]), key[4], int(key[5:])
    if kind == "Q":
        return dt.datetime(y, 3 * (n - 1) + 1, 1), dt.datetime(y + (n == 4), 3 * n % 12 + 1, 1), [key]
    quarters = [f"{y}Q{q}" for q in ((1, 2) if n == 1 else (3, 4))]
    return dt.datetime(y, 6 * (n - 1) + 1, 1), dt.datetime(y + (n == 2), 6 * n % 12 + 1, 1), quarters


def period_key(day, window):
    if window == "half":
        return f"{day.year}H{(day.month - 1) // 6 + 1}"
    return f"{day.year}Q{(day.month - 1) // 3 + 1}"


def chains(res, quarter_key):
    """Daily class chains for one flow window: the network's own flows, and the one-pool version.

    Both use each class's average balance over the window, its total transfer rate and its rate into
    the sink; they differ only in where a class's transfers land: where they did, or across all
    classes in proportion to what each received.
    """
    import numpy as np
    C = len(res["classes"])
    start, end, quarters = period_bounds(quarter_key)
    a0 = max(0, (start - res["day0"]).days)
    a1 = min(res["class_bal"].shape[0], (end - res["day0"]).days)
    present = [q for q in quarters if q in res["flows"]]
    if a1 <= a0 or not present:
        return None, None
    days = a1 - a0
    avg = res["class_bal"][a0:a1].mean(axis=0)
    F = sum(res["flows"][q] for q in present) / days
    received = F[:, :C].sum(axis=0)
    share = received / received.sum() if received.sum() > 0 else np.zeros(C)
    net = np.zeros((C, C + 1))
    pool = np.zeros((C, C + 1))
    for c in range(C):
        if avg[c] <= 0:
            net[c, c] = pool[c, c] = 1.0
            continue
        out = F[c, :C] / avg[c]
        sink = F[c, C] / avg[c]
        rate = out.sum()
        scale = min(1.0, 1.0 / max(rate + sink, 1e-12))
        net[c, :C] = out * scale
        net[c, C] = sink * scale
        net[c, c] += 1.0 - net[c].sum()
        pool[c, :C] = rate * scale * share
        pool[c, C] = sink * scale
        pool[c, c] += 1.0 - pool[c].sum()
    return net, pool


def hybrid_rows(net, pool, c):
    """The entry class c moves as the network did; every other class as the one-pool chain would.
    Read beyond the first stop, this asks only how fast a stop passes money on, with the first hop
    taken as it happened."""
    P = pool.copy()
    P[c] = net[c]
    return P


CHAIN_STARTS = ("start", "mid", "end")      # the chains start on the entry month's first day, 15 days before its end, or at its end


def chain_start(end, how):
    if how == "start":
        return dt.datetime(end.year - (end.month == 1), (end.month - 2) % 12 + 1, 1)
    return end if how == "end" else end - dt.timedelta(days=15)


def cohort_rows(res, min_cohort=MIN_COHORT, start_at="mid", window="quarter"):
    """Pooled over each entry class's cohorts of at least MIN_COHORT: the share still in the entry
    class, among the cohort's money still in circulation, at each age in AGES, observed and from
    the two chains started at the middle of the entry month."""
    import numpy as np
    classes, months, snaps, times = res["classes"], res["months"], res["snaps"], res["snap_times"]
    C, M = len(classes), len(months)
    out = {}
    for c in range(C):
        obs = defaultdict(lambda: [0.0, 0.0])
        moves = defaultdict(lambda: [0.0, 0.0, 0.0])     # within, across, disbursed
        movd = defaultdict(lambda: [0.0, 0.0, 0.0])      # moved in entry class, moved anywhere, circulating
        per_cohort = defaultdict(list)
        mod = {"network": defaultdict(lambda: [0.0, 0.0]), "pool": defaultdict(lambda: [0.0, 0.0])}
        mod["hybrid"] = defaultdict(lambda: [0.0, 0.0])
        comp = {name: defaultdict(lambda: np.zeros(C)) for name in ("observed", "network", "pool", "hybrid")}
        cohort_vecs = defaultdict(list)
        details = []
        n_cohorts, mass = 0, 0.0
        for m, key in enumerate(months):
            k = c * M + m
            if res["disbursed"][k] < min_cohort:
                continue
            n_cohorts += 1
            mass += res["disbursed"][k]
            end = month_end(key)
            first = bisect.bisect_left(times, end)
            det = {"month": key, "disbursed": float(res["disbursed"][k]), "observed": {}, "network": {}, "pool": {},
                   "in_area_of_moved": {}, "turnover": {}}
            details.append(det)
            for age in AGES:
                s_ix = first + age
                if s_ix >= len(times):
                    continue
                col = snaps[s_ix][:, k]
                circ = col.sum()
                if circ <= 0:
                    continue
                obs[age][0] += col[c]
                obs[age][1] += circ
                comp["observed"][age] += col
                cohort_vecs[age].append(col / circ)
                mcol = res["snaps_moved"][s_ix][:, k]
                det["observed"][age] = col[c] / circ
                if mcol.sum() > 0:
                    det["in_area_of_moved"][age] = mcol[c] / mcol.sum()
                det["turnover"][age] = (res["snaps_within"][s_ix][k] + res["snaps_across"][s_ix][k]) / res["disbursed"][k]
                movd[age][0] += mcol[c]
                movd[age][1] += mcol.sum()
                movd[age][2] += circ
                per_cohort[age].append(col[c] / circ)
                moves[age][0] += res["snaps_within"][s_ix][k]
                moves[age][1] += res["snaps_across"][s_ix][k]
                moves[age][2] += res["disbursed"][k]
            # the chains, started with the cohort's disbursed mass at mid-month
            start = chain_start(end, start_at)
            v = {"network": np.zeros(C + 1), "pool": np.zeros(C + 1), "hybrid": np.zeros(C + 1)}
            for name in v:
                v[name][c] = res["disbursed"][k]
            day = start
            ages_left = sorted(AGES)
            cache = {}
            while ages_left and first + ages_left[0] < len(times):
                target = times[first + ages_left[0]]
                while day < target:
                    q = period_key(day, window)
                    if q not in cache:
                        cache[q] = chains(res, q)
                    net, pool = cache[q]
                    if net is None:
                        break
                    if (q, c) not in cache:
                        cache[(q, c)] = hybrid_rows(net, pool, c)
                    for name, P in (("network", net), ("pool", pool), ("hybrid", cache[(q, c)])):
                        nxt = v[name][:C] @ P          # classes and the sink
                        nxt[C] += v[name][C]           # what left before stays left
                        v[name] = nxt
                    day += dt.timedelta(days=1)
                age = ages_left.pop(0)
                for name in v:
                    circ = v[name][:C].sum()
                    if circ > 0:
                        mod[name][age][0] += v[name][c]
                        mod[name][age][1] += circ
                        comp[name][age] += v[name][:C]
                        if name in det:
                            det[name][age] = v[name][c] / circ
        if n_cohorts:
            out[classes[c]] = {"cohorts": n_cohorts, "disbursed": mass,
                               "observed": {g: obs[g][0] / obs[g][1] for g in AGES if obs[g][1] > 0},
                               "network": {g: mod["network"][g][0] / mod["network"][g][1] for g in AGES if mod["network"][g][1] > 0},
                               "pool": {g: mod["pool"][g][0] / mod["pool"][g][1] for g in AGES if mod["pool"][g][1] > 0},
                               "turnover": {g: (moves[g][0] + moves[g][1]) / moves[g][2] for g in AGES if moves[g][2] > 0},
                               "within": {g: moves[g][0] / (moves[g][0] + moves[g][1]) for g in AGES
                                          if moves[g][0] + moves[g][1] > 0},
                               "moved_share": {g: movd[g][1] / movd[g][2] for g in AGES if movd[g][2] > 0},
                               "in_area_of_moved": {g: movd[g][0] / movd[g][1] for g in AGES if movd[g][1] > 0},
                               "cohort_min": {g: min(per_cohort[g]) for g in AGES if per_cohort[g]},
                               "cohort_max": {g: max(per_cohort[g]) for g in AGES if per_cohort[g]},
                               "cohorts_at": {g: len(per_cohort[g]) for g in AGES},
                               "hybrid": {g: mod["hybrid"][g][0] / mod["hybrid"][g][1] for g in AGES if mod["hybrid"][g][1] > 0},
                               "composition": {name: {g: comp[name][g].copy() for g in AGES if comp[name][g].sum() > 0}
                                               for name in comp},
                               "cohort_vectors": {g: list(cohort_vecs[g]) for g in AGES if cohort_vecs[g]},
                               "cohort_detail": details}
    return out


def tagged(a: Archive):
    """The tag pass and the cohort rows, computed once per archive for blocks 5 and 6."""
    if getattr(a, "_tagged", None) is None:
        a._tagged = tag_pass(a)
        a._rows = cohort_rows(a._tagged)
    return a._tagged, a._rows


def first_stop(res, c):
    """The class that receives the largest value of class c's transfers to other classes over the
    whole archive, and the share of those transfers it receives; None when c pays no other class."""
    import numpy as np
    C = len(res["classes"])
    tot = np.zeros(C)
    for F in res["flows"].values():
        tot += F[c, :C]
    tot[c] = 0.0
    if tot.sum() <= 0:
        return None, None
    d = int(tot.argmax())
    return d, float(tot[d] / tot.sum())


def conduit_rows(res, rows):
    """Per entry class: its first stop, and at each age the share of the cohorts' circulating money
    in the first stop and beyond it (every class but the entry class and the first stop), observed
    and from the two chains; with the destination mix of the money that has left the entry class."""
    classes = res["classes"]
    out = {}
    for name, r in rows.items():
        c = classes.index(name)
        d, d_share = first_stop(res, c)
        if d is None:
            continue
        rec = {"first_stop": classes[d], "first_stop_share_of_payments_out": d_share}
        for kind in ("observed", "network", "pool", "hybrid"):
            at, beyond, mix = {}, {}, {}
            for g, vec in r["composition"][kind].items():
                circ = vec.sum()
                left = circ - vec[c]
                at[g] = vec[d] / circ
                beyond[g] = (left - vec[d]) / circ
                if left > 0:
                    mix[g] = {classes[k]: vec[k] / left for k in range(len(classes)) if k != c}
            rec[kind] = {"at_first_stop": at, "beyond": beyond, "mix_of_money_out": mix}
        vecs = r["cohort_vectors"]
        rec["observed"]["beyond_cohort_min"] = {g: min(1.0 - x[c] - x[d] for x in vs) for g, vs in vecs.items()}
        rec["observed"]["beyond_cohort_max"] = {g: max(1.0 - x[c] - x[d] for x in vs) for g, vs in vecs.items()}
        out[name] = rec
    return out


def block5(a: Archive) -> None:
    import numpy as np
    print("\n== 5. new money by entry area: share still in the entry area, among that money still in circulation."
          "\n   Look at: where the observed row sits between the network chain and the one-pool chain")
    res, rows = tagged(a)
    g = res["guard"]
    print(f"   {len(res['months'])} entry months from {res['months'][0]}; transfers larger than the sending balance: "
          f"{g['events']:,d}, short by {g['shortfall']:,.2f} in all; tagged value conserved to {res['conservation_residual']:.2e}")
    received = np.zeros(len(res["classes"]))
    for q, F in res["flows"].items():
        received += F[:, :len(res["classes"])].sum(axis=0)
    share = dict(zip(res["classes"], received / received.sum()))
    for name, r in sorted(rows.items(), key=lambda kv: -kv[1]["disbursed"]):
        print(f"\n   {name}: {r['cohorts']} monthly cohorts of at least {MIN_COHORT:,.0f}, {r['disbursed'] / 1e3:,.0f}k disbursed;"
              f" share of all transfer value received {100 * share[name]:.1f}%")
        print("   age (weeks)      " + "".join(f"{x:>7d}" for x in AGES))
        for label, scale in (("observed %", 100), ("  lowest cohort", 100), ("  highest cohort", 100),
                             ("network %", 100), ("pool %", 100),
                             ("paid on % of it", 100), ("  in area %", 100),
                             ("times paid on", 1), ("paid in area %", 100)):
            key = {"observed %": "observed", "  lowest cohort": "cohort_min", "  highest cohort": "cohort_max",
                   "network %": "network", "pool %": "pool", "paid on % of it": "moved_share",
                   "  in area %": "in_area_of_moved", "times paid on": "turnover", "paid in area %": "within"}[label]
            vals = r[key]
            digits = 2 if scale == 1 else 1
            print(f"   {label:16s} " + "".join(f"{scale * vals[x]:>7.{digits}f}" if x in vals else f"{'.':>7s}" for x in AGES))


def block6(a: Archive) -> None:
    print("\n== 6. where new money that leaves its entry area lands first, and whether that first stop passes it on."
          "\n   Look at: the share beyond the first stop, observed against the two chains; the one-pool chain moves money"
          "\n   on at the first stop's own spending speed, the network chain only as fast as the first stop pays other areas;"
          "\n   'pool after hop 1' takes the entry area's own payments as they were and runs every other area as one pool")
    res, rows = tagged(a)
    clocks = class_clocks(a)
    cond = conduit_rows(res, rows)
    for name, r in sorted(rows.items(), key=lambda kv: -kv[1]["disbursed"]):
        if name not in cond or r["cohorts"] < 3:
            continue
        rec = cond[name]
        stop = rec["first_stop"]
        ck = clocks.get(stop, {})
        days = "." if ck.get("days_all") is None else f"{ck['days_all']:.1f} days"
        within = "." if ck.get("within_share") is None else f"{100 * ck['within_share']:.1f}%"
        print(f"\n   {name}: {r['cohorts']} cohorts; first stop by payment value {stop}, which takes "
              f"{100 * rec['first_stop_share_of_payments_out']:.1f}% of what {name} pays other areas "
              f"(its spending clock {days}, pays {within} within)")
        print("   age (weeks)          " + "".join(f"{x:>7d}" for x in AGES))
        for label, part, kind in (("in the first stop %", "at_first_stop", "observed"), ("  network %", "at_first_stop", "network"),
                                  ("  pool %", "at_first_stop", "pool"), ("  pool after hop 1 %", "at_first_stop", "hybrid"),
                                  ("beyond it %", "beyond", "observed"),
                                  ("  lowest cohort", "beyond_cohort_min", "observed"), ("  highest cohort", "beyond_cohort_max", "observed"),
                                  ("  network %", "beyond", "network"), ("  pool %", "beyond", "pool"),
                                  ("  pool after hop 1 %", "beyond", "hybrid")):
            vals = rec[kind][part]
            print(f"   {label:20s} " + "".join(f"{100 * vals[x]:>7.1f}" if x in vals else f"{'.':>7s}" for x in AGES))
        mix = {kind: rec[kind]["mix_of_money_out"] for kind in ("observed", "network", "pool")}
        early = min((g for g in AGES if g in mix["observed"]), default=None)
        late = max((g for g in AGES if g in mix["observed"]), default=None)
        if early is None:
            continue
        dests = sorted(mix["observed"][late], key=lambda k: -mix["observed"][late][k])[:5]
        print(f"   money that has left {name}, by destination, % (observed / network / pool)"
              f" at {early} and {late} weeks:")
        for k in dests:
            cells = []
            for g in (early, late):
                cells.append(" / ".join("." if g not in mix[kind] else f"{100 * mix[kind][g][k]:.1f}"
                                        for kind in ("observed", "network", "pool")))
            print(f"     {k:22s} {cells[0]:>20s}   {cells[1]:>20s}")


RULE_DATES = (("2020-10-19", "long-inactive accounts zeroed"), ("2021-02-01", "2% monthly demurrage begins"))
WINDOW_WEEKS = 13


def window_clocks(res, c, start, end):
    """Spending clock, out-of-area clock, within share and reclaimed share of balance per 30 days for
    class c over [start, end), from end-of-day balances and daily flows; None where undefined."""
    C = len(res["classes"])
    a0 = max(0, (start - res["day0"]).days)
    a1 = min(res["class_bal"].shape[0], (end - res["day0"]).days)
    if a1 <= a0:
        return None
    n = a1 - a0
    avg = float(res["class_bal"][a0:a1, c].mean())
    F = res["day_flows"][a0:a1, c].sum(axis=0)
    out_all = float(F[:C + 1].sum())
    out_other = out_all - float(F[c])
    return {"days": n, "avg_balance": avg, "transfers_out": out_all,
            "days_all": avg / (out_all / n) if out_all > 0 and avg > 0 else None,
            "days_other": avg / (out_other / n) if out_other > 0 and avg > 0 else None,
            "within": float(F[c]) / out_all if out_all > 0 else None,
            "reclaimed_per_30_days": float(F[C + 1]) / n * 30 / avg if avg > 0 else None}


def monthly_clocks(res):
    classes = res["classes"]
    months = sorted({(res["day0"] + dt.timedelta(days=d)).strftime("%Y-%m") for d in range(res["class_bal"].shape[0])})
    out = {}
    for c, name in enumerate(classes):
        out[name] = {}
        for m in months:
            start = dt.datetime(int(m[:4]), int(m[5:7]), 1)
            got = window_clocks(res, c, start, month_end(m))
            if got is not None:
                out[name][m] = got
    return out


def block7(a: Archive) -> None:
    print("\n== 7. the rules against the two clocks. Look at: whether the spending clock and the out-of-area clock move"
          "\n   together at 2020-10-19 and 2021-02-01, and whether a cohort's retention follows the one or the other")
    for day, what in RULE_DATES:
        print(f"   {day}: {what}")
    res, rows = tagged(a)
    mc = monthly_clocks(res)

    def f(x, spec, scale=1.0):
        return "." if x is None else format(scale * x, spec)

    for name, r in sorted(rows.items(), key=lambda kv: -kv[1]["disbursed"]):
        if r["cohorts"] < 10:
            continue
        print(f"\n   {name}, by month: spending clock and out-of-area clock (days), within %, reclaimed % of balance per 30 days,"
              f" transfers out (thousand)")
        for m, v in mc[name].items():
            print(f"     {m}   {f(v['days_all'], '7.1f'):>7s}  {f(v['days_other'], '8.1f'):>8s}  {f(v['within'], '5.1f', 100):>5s}"
                  f"  {f(v['reclaimed_per_30_days'], '6.2f', 100):>6s}  {v['transfers_out'] / 1e3:>8.0f}")
        print(f"   {name}, by entry month: share still in the area at 4, 8 and 13 weeks (observed | network | pool),"
              f" and the clocks of the {WINDOW_WEEKS} weeks after the entry month")
        print(f"     {'month':8s}{'k':>6s}   {'observed':^17s}   {'network':^17s}   {'pool':^17s}   {'days@all':>8s}{'days@other':>11s}"
              f"{'paid on':>8s}{'in area':>8s}")
        for det in r["cohort_detail"]:
            end = month_end(det["month"])
            w = window_clocks(res, res["classes"].index(name), end, end + WINDOW_WEEKS * WEEK)
            full = w is not None and w["days"] == WINDOW_WEEKS * 7
            cells = []
            for kind in ("observed", "network", "pool"):
                cells.append(" ".join(f(det[kind].get(g), "5.1f", 100) .rjust(5) for g in (4, 8, 13)))
            tail = (f"{f(w['days_all'] if w else None, '8.1f'):>8s}{f(w['days_other'] if w else None, '11.1f'):>11s}"
                    f"{f(det['turnover'].get(13), '8.2f'):>8s}{f(det['in_area_of_moved'].get(13), '8.1f', 100):>8s}")
            print(f"     {det['month']:8s}{det['disbursed'] / 1e3:>6.0f}   {cells[0]:17s}   {cells[1]:17s}   {cells[2]:17s}   {tail}"
                  f"{'' if full else '  (window cut by the end of the data)'}")


# ---------------------------------------------------------------------------
# Block 8: the same chains run wallet by wallet, with each wallet's own spending speed and payees
# ---------------------------------------------------------------------------

WALLET_VARIANTS = (("own speed, own payees", "own", "own"), ("own speed, area payees", "own", "area"),
                   ("area speed, own payees", "area", "own"), ("area speed, area payees", "area", "area"),
                   ("own speed, pool payees", "own", "pool"), ("area speed, pool payees", "area", "pool"))


def wallet_panel(a: Archive, res):
    """Per quarter and per wallet in circulation: the sum over days of end-of-day balance, payments to
    each other wallet in circulation, value leaving circulation, and each month's new money by wallet.
    Summed over an area these are the class balances and flows block 5's chains use, so the wallet
    chains with area speed and area or pool payees lump exactly to those chains."""
    import numpy as np
    cls = {k: class_of(v) for k, v in a.users.items()}
    ci = {c: i for i, c in enumerate(res["classes"])}
    circ = [w for w in sorted(a.users) if cls[w] in ci]
    wi = {w: i for i, w in enumerate(circ)}
    wclass = np.array([ci[cls[w]] for w in circ], dtype=np.int64)
    N = len(circ)
    day0, n_days = res["day0"], res["class_bal"].shape[0]
    quarters = sorted(res["flows"])
    qk = {q: k for k, q in enumerate(quarters)}
    months = res["months"]
    mi = {m: i for i, m in enumerate(months)}
    bal = np.zeros(N)
    last_day = np.zeros(N, dtype=np.int64)
    seg_w, seg_a, seg_b, seg_v = [], [], [], []
    edges = [defaultdict(float) for _ in quarters]
    sink = np.zeros((len(quarters), N))
    new_money = defaultdict(float)
    for t, sub, s, g, w, _ in sorted(a.txns, key=lambda x: (x[0], x[5])):
        i, j = wi.get(s), wi.get(g)
        if i is None and j is None:
            continue
        d = (t - day0).days
        for x in (i, j):
            if x is not None and d > last_day[x]:
                seg_w.append(x); seg_a.append(last_day[x]); seg_b.append(d); seg_v.append(bal[x])
                last_day[x] = d
        q = qk.get(period_key(t, "quarter"))
        if i is None:
            bal[j] += w
            if sub == "DISBURSEMENT" and t >= CONVERSION_END:
                new_money[(mi[month_key(t)], j)] += w
            continue
        bal[i] -= w
        if j is None:
            if q is not None and sub in ("STANDARD", "AGENT_OUT", "RECLAMATION"):
                sink[q, i] += w
            continue
        bal[j] += w
        if q is not None and sub in ("STANDARD", "AGENT_OUT"):
            edges[q][(i, j)] += w
    for x in range(N):
        seg_w.append(x); seg_a.append(last_day[x]); seg_b.append(n_days); seg_v.append(bal[x])
    seg_w, seg_a, seg_b, seg_v = map(np.asarray, (seg_w, seg_a, seg_b, seg_v))
    balday = np.zeros((len(quarters), N))
    qdays = []
    for k, q in enumerate(quarters):
        start, end, _ = period_bounds(q)
        lo, hi = max(0, (start - day0).days), min(n_days, (end - day0).days)
        qdays.append((lo, hi))
        overlap = np.clip(np.minimum(seg_b, hi) - np.maximum(seg_a, lo), 0, None)
        balday[k] = np.bincount(seg_w, weights=seg_v * overlap, minlength=N)
    edge_arrays = []
    for k in range(len(quarters)):
        if edges[k]:
            src = np.fromiter((p[0] for p in edges[k]), dtype=np.int64, count=len(edges[k]))
            dst = np.fromiter((p[1] for p in edges[k]), dtype=np.int64, count=len(edges[k]))
            val = np.fromiter(edges[k].values(), dtype=float, count=len(edges[k]))
        else:
            src = dst = np.zeros(0, dtype=np.int64)
            val = np.zeros(0)
        edge_arrays.append((src, dst, val))
    by_month = defaultdict(lambda: ([], []))
    for (m, j), w in sorted(new_money.items()):
        by_month[m][0].append(j)
        by_month[m][1].append(w)
    return {"N": N, "wclass": wclass, "quarters": quarters, "qdays": qdays, "balday": balday, "sink": sink,
            "edges": edge_arrays, "new_money": {m: (np.array(js, dtype=np.int64), np.array(ws)) for m, (js, ws) in by_month.items()}}


def panel_window(res, panel, window):
    """The quarterly wallet panel, or the same panel summed into half-years (the flow window knob)."""
    import numpy as np
    if window == "quarter":
        return panel
    cache = panel.setdefault("_half", None)
    if cache is not None:
        return cache
    day0, n_days = res["day0"], res["class_bal"].shape[0]
    halves = sorted({period_key(period_bounds(q)[0], "half") for q in panel["quarters"]})
    out = {"N": panel["N"], "wclass": panel["wclass"], "quarters": halves, "qdays": [], "new_money": panel["new_money"]}
    balday, sink, edges = [], [], []
    for h in halves:
        start, end, parts = period_bounds(h)
        ks = [k for k, q in enumerate(panel["quarters"]) if q in parts]
        out["qdays"].append((max(0, (start - day0).days), min(n_days, (end - day0).days)))
        balday.append(sum(panel["balday"][k] for k in ks))
        sink.append(sum(panel["sink"][k] for k in ks))
        edges.append(tuple(np.concatenate([panel["edges"][k][x] for k in ks]) for x in range(3)))
    out.update({"balday": np.array(balday), "sink": np.array(sink), "edges": edges})
    panel["_half"] = out
    return out


def wallet_operator(res, panel, k, speed, payees):
    """One day's step for quarter k, for one speed source and one payee rule."""
    import numpy as np
    C, N, wclass = len(res["classes"]), panel["N"], panel["wclass"]
    lo, hi = panel["qdays"][k]
    days = hi - lo
    if days <= 0:
        return None
    src, dst, val = panel["edges"][k]
    avg = panel["balday"][k] / days
    out = np.bincount(src, weights=val, minlength=N) / days
    snk = panel["sink"][k] / days
    rec = np.bincount(dst, weights=val, minlength=N) / days
    avg_a = np.bincount(wclass, weights=avg, minlength=C)
    F = np.zeros((C, C))
    np.add.at(F, (wclass[src], wclass[dst]), val / days)
    F_a, S_a = F.sum(axis=1), np.bincount(wclass, weights=snk, minlength=C)
    if speed == "own":
        tot = out + snk
        with np.errstate(divide="ignore", invalid="ignore"):
            rate = np.where(avg > 0, tot / np.where(avg > 0, avg, 1.0), np.where(tot > 0, np.inf, 0.0))
        leave = np.where(np.isinf(rate), 1.0, np.minimum(rate, 1.0))
        share_c = np.where(tot > 0, out / np.where(tot > 0, tot, 1.0), 0.0)
    else:
        tot_a = F_a + S_a
        with np.errstate(divide="ignore", invalid="ignore"):
            rate_a = np.where(avg_a > 0, tot_a / np.where(avg_a > 0, avg_a, 1.0), 0.0)
            share_a = np.where(tot_a > 0, F_a / np.where(tot_a > 0, tot_a, 1.0), 0.0)
        leave = np.minimum(rate_a, 1.0)[wclass]
        share_c = share_a[wclass]
    circ_rate = leave * share_c
    op = {"stay": 1.0 - leave, "edges": None, "area_c": None, "pool_c": None}
    with np.errstate(divide="ignore", invalid="ignore"):
        D = np.where(F_a[:, None] > 0, F / np.where(F_a[:, None] > 0, F_a[:, None], 1.0), 0.0)
        rec_a = np.bincount(wclass, weights=rec, minlength=C)
        rho = np.where(rec_a[wclass] > 0, rec / np.where(rec_a[wclass] > 0, rec_a[wclass], 1.0), 0.0)
        g = rec / rec.sum() if rec.sum() > 0 else np.zeros(N)
    if payees == "own":
        has = out > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            w = circ_rate[src] * val / np.where(out[src] * days > 0, out[src] * days, 1.0)
        op["edges"] = (src, dst, w)
        op["area_c"] = np.where(has, 0.0, circ_rate)
    elif payees == "area":
        op["area_c"] = circ_rate
    else:
        op["pool_c"] = circ_rate
    op.update({"D": D, "rho": rho, "g": g})
    return op


def wallet_step(V, op, wclass, C):
    import numpy as np
    n, N = V.shape
    new = V * op["stay"][None, :]
    if op["edges"] is not None and op["edges"][0].size:
        src, dst, w = op["edges"]
        flat = (np.arange(n)[:, None] * N + dst[None, :]).ravel()
        new += np.bincount(flat, weights=(V[:, src] * w[None, :]).ravel(), minlength=n * N).reshape(n, N)
    if op["area_c"] is not None and op["area_c"].any():
        flat = (np.arange(n)[:, None] * C + wclass[None, :]).ravel()
        LA = np.bincount(flat, weights=(V * op["area_c"][None, :]).ravel(), minlength=n * C).reshape(n, C)
        new += (LA @ op["D"])[:, wclass] * op["rho"][None, :]
    if op["pool_c"] is not None:
        new += (V @ op["pool_c"])[:, None] * op["g"][None, :]
    return new


def wallet_chain_rows(res, panel, min_cohort=MIN_COHORT, start_at="mid", window="quarter", variants=WALLET_VARIANTS):
    """For each variant and entry class: the share of the cohorts' chain mass still in the entry class
    among the mass in circulation, pooled over cohorts as block 5 pools them, at each age in AGES."""
    import numpy as np
    classes, months, times = res["classes"], res["months"], res["snap_times"]
    panel = panel_window(res, panel, window)
    C, M, wclass = len(classes), len(months), panel["wclass"]
    qk = {q: k for k, q in enumerate(panel["quarters"])}
    acc = {name: defaultdict(lambda: defaultdict(lambda: [0.0, 0.0])) for name, _, _ in variants}
    ops = {}
    for m, key in enumerate(months):
        rows = [c for c in range(C) if res["disbursed"][c * M + m] >= min_cohort]
        if not rows or m not in panel["new_money"]:
            continue
        js, ws = panel["new_money"][m]
        V0 = np.zeros((len(rows), panel["N"]))
        for r, c in enumerate(rows):
            mask = wclass[js] == c
            np.add.at(V0[r], js[mask], ws[mask])
            want = res["disbursed"][c * M + m]
            if abs(V0[r].sum() - want) > 1e-6 * max(1.0, want):
                raise AssertionError(f"new money by wallet does not add up to the cohort: {V0[r].sum():.6g} against {want:.6g}")
        end = month_end(key)
        first = bisect.bisect_left(times, end)
        for name, speed, payees in variants:
            V, day = V0.copy(), chain_start(end, start_at)
            ages_left = sorted(AGES)
            while ages_left and first + ages_left[0] < len(times):
                target = times[first + ages_left[0]]
                while day < target:
                    k = qk.get(period_key(day, window))
                    if k is None:
                        break
                    if (k, speed, payees) not in ops:
                        ops[(k, speed, payees)] = wallet_operator(res, panel, k, speed, payees)
                    op = ops[(k, speed, payees)]
                    if op is None:
                        break
                    V = wallet_step(V, op, wclass, C)
                    day += dt.timedelta(days=1)
                age = ages_left.pop(0)
                flat = (np.arange(len(rows))[:, None] * C + wclass[None, :]).ravel()
                tot = np.bincount(flat, weights=V.ravel(), minlength=len(rows) * C).reshape(len(rows), C)
                for r, c in enumerate(rows):
                    if tot[r].sum() > 0:
                        acc[name][classes[c]][age][0] += tot[r, c]
                        acc[name][classes[c]][age][1] += tot[r].sum()
    shares = {name: {cl: {g: v[0] / v[1] for g, v in by.items() if v[1] > 0} for cl, by in per.items()}
              for name, per in acc.items()}
    masses = {name: {cl: {g: v[1] for g, v in by.items()} for cl, by in per.items()} for name, per in acc.items()}
    return shares, masses


def block8(a: Archive) -> None:
    print("\n== 8. the chains wallet by wallet: which of the two, a wallet's own spending speed or its own payees,"
          "\n   closes the gap between the area chain and what the tagged money did. Look at: 'area speed, own payees'"
          "\n   against 'own speed, area payees', each beside the observed share")
    res, rows = tagged(a)
    panel = wallet_panel(a, res)
    got, _ = wallet_chain_rows(res, panel)
    worst_net = max((abs(got["area speed, area payees"][cl][g] - r["network"][g])
                     for cl, r in rows.items() for g in r["network"] if g in got["area speed, area payees"].get(cl, {})), default=0.0)
    worst_pool = max((abs(got["area speed, pool payees"][cl][g] - r["pool"][g])
                      for cl, r in rows.items() for g in r["pool"] if g in got["area speed, pool payees"].get(cl, {})), default=0.0)
    print(f"   {panel['N']:,d} wallets in circulation; the wallet chains that lump to block 5's chains differ from them by at most"
          f" {worst_net:.1e} (network) and {worst_pool:.1e} (one pool)")
    for name, r in sorted(rows.items(), key=lambda kv: -kv[1]["disbursed"]):
        if r["cohorts"] < 10 or name in NOT_AREAS:
            continue
        print(f"\n   {name}: {r['cohorts']} cohorts")
        print("   age (weeks)                  " + "".join(f"{x:>7d}" for x in AGES))
        print(f"   {'observed %':28s} " + "".join(f"{100 * r['observed'][x]:>7.1f}" if x in r["observed"] else f"{'.':>7s}" for x in AGES))
        for vname, _, _ in WALLET_VARIANTS:
            vals = got[vname].get(name, {})
            print(f"   {vname + ' %':28s} " + "".join(f"{100 * vals[x]:>7.1f}" if x in vals else f"{'.':>7s}" for x in AGES))


BLOCKS = (block0, block1, block2, block3, block4, block5, block6, block7, block8)


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------

NOT_AREAS = {"other"}          # the users table's label for accounts with no area; not a group anyone pays within
CELL_MIN_COHORTS = 3           # an (area, age) cell is read when at least this many cohorts reach that age
SWEEP = {"min_cohort": (5_000.0, 10_000.0, 20_000.0), "start_at": CHAIN_STARTS, "window": ("quarter", "half")}
DEFAULT_SETTING = {"min_cohort": MIN_COHORT, "start_at": "mid", "window": "quarter"}
DESCRIPTOR_TOLERANCE = 1.0     # the descriptor prints whole Sarafu

RIVAL_PREMISE = ("a sum of money that leaves its holder leaves the group the holder is in, and how long it stays"
                 " is set by how fast the holder spends")
RIVAL_ENTAILMENT = ("new money disbursed into an area is spent at that area's own spending speed, and each payment"
                    " lands across areas in proportion to what each area receives; so the entry area's excess share"
                    " decays at the holding period towards the one-pool split, and the one-pool chain built from each"
                    " area's own balance and turnover is that trajectory, share by share and week by week")

RIVAL_MAPPING = {"one-pool chain outside the cohort range at every setting": "the rival misses: counts toward PASS",
                 "one-pool chain inside at every setting, our chain outside at every setting": "grid C: counts toward FAIL",
                 "one-pool chain inside at every setting, our chain inside at every setting": "grid A: no bearing on the rival",
                 "one-pool chain inside at every setting, our chain moving with a knob": "not read",
                 "one-pool chain moving with a knob, or no object": "not read",
                 "grid letter": "placed only when both chains are steady over the knobs: B ours inside and the rival's"
                                " outside, A both inside, C the rival's inside and ours outside, both_unmet both outside"}
WALLET_RIVAL_MAPPING = {
    "rival's wallet chain outside the cohort range at every setting": "the rival misses: counts toward PASS",
    "rival's wallet chain inside at every setting, our wallet chain outside at every setting": "grid C: counts toward FAIL",
    "rival's wallet chain inside at every setting, our wallet chain inside at every setting": "grid A: no bearing on the rival",
    "rival's wallet chain inside at every setting, ours moving with a knob": "not read",
    "rival's wallet chain moving with a knob, or no object": "not read",
    "chains": "the rival's: each wallet at its own quarterly speed, payments landing across wallets by what each receives;"
              " ours: each wallet at its own quarterly speed, payments landing on the wallet's own payees"}
OWN_MAPPING = {"nearer ours": "the whole cohort range on our chain's side of the midpoint: counts toward PASS",
               "nearer the rival's": "the whole cohort range on the one-pool side of the midpoint: counts toward FAIL",
               "straddle": "the range crosses the midpoint: not read",
               "moves with a knob": "not read", "no object": "not read"}


def rival_cell(lo, hi, net, pool):
    return {(True, False): "B", (True, True): "A", (False, True): "C",
            (False, False): "both_unmet"}[(lo <= net <= hi, lo <= pool <= hi)]


def own_cell(lo, hi, net, pool):
    mid = (net + pool) / 2
    if net > pool:
        return "nearer ours" if lo > mid else "nearer the rival's" if hi < mid else "straddle"
    if net < pool:
        return "nearer ours" if hi < mid else "nearer the rival's" if lo > mid else "straddle"
    return "straddle"


def settings_grid():
    return [{"min_cohort": m, "start_at": st, "window": w}
            for m in SWEEP["min_cohort"] for st in SWEEP["start_at"] for w in SWEEP["window"]]


def sweep_cells(res):
    """Every (area, age) cell that at least CELL_MIN_COHORTS cohorts reach at the default setting, read
    at every setting of the three knobs. A cell whose state is not the same at all settings is not read."""
    base = cohort_rows(res, **DEFAULT_SETTING)
    cells = [(name, g) for name, r in sorted(base.items()) if name not in NOT_AREAS
             for g in AGES if r["cohorts_at"].get(g, 0) >= CELL_MIN_COHORTS]
    out = {f"{name} | {g} weeks": {"area": name, "age": g, "settings": []} for name, g in cells}
    for setting in settings_grid():
        rows = base if setting == DEFAULT_SETTING else cohort_rows(res, **setting)
        for name, g in cells:
            r = rows.get(name, {})
            rec = out[f"{name} | {g} weeks"]
            have = r and g in r.get("cohort_min", {}) and g in r.get("network", {}) and g in r.get("pool", {})
            if not have:
                rec["settings"].append({**setting, "rival": "no object", "own": "no object",
                                        "pool_in_range": "no object", "network_in_range": "no object"})
                continue
            lo, hi, net, pool = r["cohort_min"][g], r["cohort_max"][g], r["network"][g], r["pool"][g]
            rec["settings"].append({**setting, "low": lo, "high": hi, "network": net, "pool": pool,
                                    "cohorts": r["cohorts_at"][g], "rival": rival_cell(lo, hi, net, pool),
                                    "own": own_cell(lo, hi, net, pool),
                                    "pool_in_range": "inside" if lo <= pool <= hi else "outside",
                                    "network_in_range": "inside" if lo <= net <= hi else "outside"})
    for rec in out.values():
        # the two chains are two questions, each settled over the knobs on its own: the rival's verdict
        # needs only the one-pool chain to be steady; a cell is placed in the grid only when both are
        for which in ("rival", "own", "pool_in_range", "network_in_range"):
            rec[which] = settle(x[which] for x in rec["settings"])
    return out


WALLET_RIVAL = "own speed, pool payees"      # the rival with each holder's own holding speed
WALLET_OURS = "own speed, own payees"        # the network chain at the grain of payment relations
WALLET_RIVAL_PREMISE = ("a sum of money that leaves its holder leaves the group the holder is in; each holder keeps it for"
                        " as long as that holder's own spending speed says, and when it is spent it lands wherever"
                        " money is received, in proportion to what each wallet receives")
WALLET_RIVAL_ENTAILMENT = ("the chain in which every wallet spends at its own quarterly speed and every payment lands across"
                           " wallets in proportion to what each receives gives the entry area's share of new money week by"
                           " week; with holders' speeds as they were, that share is the rival's prediction")


def sweep_wallet_cells(res, panel):
    """The cells of B114-2, read against the two wallet chains at every setting of the three knobs."""
    base = cohort_rows(res, **DEFAULT_SETTING)
    cells = [(name, g) for name, r in sorted(base.items()) if name not in NOT_AREAS
             for g in AGES if r["cohorts_at"].get(g, 0) >= CELL_MIN_COHORTS]
    out = {f"{name} | {g} weeks": {"area": name, "age": g, "settings": []} for name, g in cells}
    variants = [v for v in WALLET_VARIANTS if v[0] in (WALLET_OURS, WALLET_RIVAL)]
    for setting in settings_grid():
        rows = base if setting == DEFAULT_SETTING else cohort_rows(res, **setting)
        shares, _ = wallet_chain_rows(res, panel, setting["min_cohort"], setting["start_at"], setting["window"], variants)
        for name, g in cells:
            r = rows.get(name, {})
            rec = out[f"{name} | {g} weeks"]
            ours, theirs = shares[WALLET_OURS].get(name, {}).get(g), shares[WALLET_RIVAL].get(name, {}).get(g)
            if not r or g not in r.get("cohort_min", {}) or ours is None or theirs is None:
                rec["settings"].append({**setting, "rival": "no object", "pool_in_range": "no object",
                                        "network_in_range": "no object"})
                continue
            lo, hi = r["cohort_min"][g], r["cohort_max"][g]
            rec["settings"].append({**setting, "low": lo, "high": hi, "wallet_network": ours, "wallet_pool": theirs,
                                    "rival": rival_cell(lo, hi, ours, theirs),
                                    "pool_in_range": "inside" if lo <= theirs <= hi else "outside",
                                    "network_in_range": "inside" if lo <= ours <= hi else "outside"})
    for rec in out.values():
        for which in ("rival", "pool_in_range", "network_in_range"):
            rec[which] = settle(x[which] for x in rec["settings"])
    return out


def settle(states):
    """One state if every setting gives the same one; otherwise the cell is not read."""
    distinct = set(states)
    return distinct.pop() if len(distinct) == 1 else "moves with a knob"


def criterion_instrument(problems, totals, residual, disbursed_max, descriptor=None):
    descriptor = DESCRIPTOR if descriptor is None else descriptor
    gaps = {"demurrage_reclaimed": totals["demurrage_reclaimed"] - descriptor["demurrage_reclaimed"],
            "agent_out_total": totals["agent_out_total"] - descriptor["agent_out_total"]}
    conserved = residual is not None and residual <= 1e-6 * max(1.0, disbursed_max)
    passed = not problems and conserved and all(abs(v) <= DESCRIPTOR_TOLERANCE for v in gaps.values())
    return {"name": "B114-1", "kind": "instrument", "passed": bool(passed),
            "statement": "the archive passes its reading checks, the tag pass conserves value, and the demurrage and"
                         " cash-out totals the data descriptor states come back from the transfers to the Sarafu",
            "detail": f"{len(problems)} problem(s); demurrage reclaimed {totals['demurrage_reclaimed']:,.2f} against"
                      f" {descriptor['demurrage_reclaimed']:,d}; agent_out {totals['agent_out_total']:,.2f} against"
                      f" {descriptor['agent_out_total']:,d}; tagged value conserved to {residual:.2e}. Printed without a"
                      f" verdict: balance total excluding admin accounts {totals['balance_from_flows_excluding_admin']:,.2f}"
                      f" against {descriptor['expected_total_balance']:,d}; rebuilt balances matching final_bal"
                      f" {totals['accounts_matching_final_balance']:,d}, not matching"
                      f" {totals['accounts_not_matching_final_balance']:,d} (largest gap {totals['worst_balance_gap']:,.2f})"}


def rival_reading(cell):
    """What one cell says about the rival: "miss", "C", "A", or not read."""
    pool, net = cell["pool_in_range"], cell["network_in_range"]
    if pool == "outside":
        return "miss"
    if pool == "inside" and net == "outside":
        return "C"
    if pool == "inside" and net == "inside":
        return "A"
    return "not read"


def criterion_rival(cells, name="B114-2", premise=RIVAL_PREMISE, entailment=RIVAL_ENTAILMENT,
                    statement="the rival's trajectory, the one-pool chain, misses the range of the observed entry-area share"
                              " across monthly cohorts, area by area and age by age, at every setting of the station's knobs"):
    readings = [rival_reading(c) for c in cells.values()]
    letters = [c["rival"] for c in cells.values()]
    split = {g: letters.count(g) for g in ("A", "B", "C", "both_unmet") if letters.count(g)}
    counted = [x for x in readings if x in ("miss", "C")]
    if counted and "C" not in counted:
        passed = True
    elif counted and all(x == "C" for x in counted):
        passed = False
    else:
        passed = None
    grid = "unread" if not split else next(iter(split)) if len(split) == 1 else "mixed"
    placed = sum(split.values())
    judged = readings.count("miss") + readings.count("C") + readings.count("A")
    holds = readings.count("C") + readings.count("A")
    rec = {"name": name, "kind": "rival", "passed": passed, "grid": grid, "rival_shape": "point",
           "rival_premise": premise, "rival_entailment": entailment,
           "rival_holds_share": None if not judged else round(holds / judged, 6),
           "statement": statement,
           "detail": f"{len(readings)} cells; the rival misses in {readings.count('miss')}, holds with ours outside (C) in"
                     f" {readings.count('C')}, holds with ours inside (A) in {readings.count('A')}, not read in"
                     f" {readings.count('not read')}; placed in the grid: "
                     + (", ".join(f"{g} {n}" for g, n in split.items()) if split else "none")}
    if grid == "mixed":
        rec["grid_split"] = split
    if len(letters) > placed:
        rec["grid_note"] = {"not placed": f"{len(letters) - placed} cell(s) where a chain moves with a knob or has no object"
                                          f" at some setting; {readings.count('miss') - split.get('B', 0) - split.get('both_unmet', 0)}"
                                          f" of them still read as a miss by the rival, whose chain is steady there"}
    return rec


def criterion_own(cells):
    states = [c["own"] for c in cells.values()]
    ours, theirs = states.count("nearer ours"), states.count("nearer the rival's")
    passed = True if ours and not theirs else False if theirs and not ours else None
    return {"name": "B114-3", "kind": "own_reading", "passed": passed,
            "statement": "the observed entry-area share sits nearer the network chain built from the areas' own payment"
                         " flows than the one-pool chain, the whole cohort range on one side of their midpoint",
            "detail": f"{len(states)} cells; nearer ours {ours}; nearer the rival's {theirs}; "
                      + ", ".join(f"{x} {states.count(x)}" for x in sorted(set(states))
                                  if x not in ("nearer ours", "nearer the rival's"))}


def clean(obj):
    """Numbers through one format, keys as text, arrays as lists, so the record reads the same on
    every machine."""
    import numpy as np
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [clean(v) for v in obj.tolist()]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(format(float(obj), ".9g"))
    if isinstance(obj, dt.datetime):
        return obj.strftime("%Y-%m-%d")
    return obj


def build_record(a: Archive) -> dict:
    res, rows = tagged(a)
    totals = descriptor_totals(a)
    cells = sweep_cells(res)
    panel = wallet_panel(a, res)
    wallet_shares, wallet_mass = wallet_chain_rows(res, panel)
    wallet_cells = sweep_wallet_cells(res, panel)
    criteria = [criterion_instrument(a.problems, totals, res["conservation_residual"], float(res["disbursed"].max())),
                criterion_rival(cells), criterion_own(cells),
                criterion_rival(wallet_cells, name="B114-4", premise=WALLET_RIVAL_PREMISE, entailment=WALLET_RIVAL_ENTAILMENT,
                                statement="the rival's strongest chain, every wallet at its own spending speed with payments"
                                          " landing by what each wallet receives, misses the range of the observed entry-area"
                                          " share across monthly cohorts, area by area and age by age, at every setting of the"
                                          " station's knobs; ours is the wallet chain on each wallet's own payees")]
    mc = monthly_clocks(res)
    windows = {}
    for name, r in rows.items():
        c = res["classes"].index(name)
        windows[name] = {}
        for det in r["cohort_detail"]:
            end = month_end(det["month"])
            windows[name][det["month"]] = window_clocks(res, c, end, end + WINDOW_WEEKS * WEEK)
    rows_out = {name: {k: v for k, v in r.items() if k != "cohort_vectors"} for name, r in rows.items()}
    coverage = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    for t, sub, _, _, w, _ in a.txns:
        cell = coverage[t.strftime("%Y-%m")][sub]
        cell[0] += 1
        cell[1] += w
    return clean({
        "stage": "B114",
        "config": {"archive": ARCHIVE_NAME, "archive_sha256": sha256_of(a.path), "conversion_end": CONVERSION_END,
                   "min_cohort": MIN_COHORT, "ages_weeks": list(AGES), "chain_start": "mid", "flow_window": "quarter",
                   "cell_min_cohorts": CELL_MIN_COHORTS, "not_areas": sorted(NOT_AREAS), "sweep": SWEEP,
                   "window_weeks": WINDOW_WEEKS, "system_roles": sorted(SYSTEM_ROLES),
                   "descriptor_tolerance": DESCRIPTOR_TOLERANCE, "rule_dates": list(RULE_DATES),
                   "wallet_variants": [list(v) for v in WALLET_VARIANTS], "wallet_rival": WALLET_RIVAL,
                   "wallet_ours": WALLET_OURS, "wallet_rate_window": "quarter, and half-year in the sweep"},
        "mapping": {"B114-2": RIVAL_MAPPING, "B114-3": OWN_MAPPING, "B114-4": WALLET_RIVAL_MAPPING},
        "objects": {"notes": a.notes, "problems": a.problems, "descriptor": DESCRIPTOR, "descriptor_totals": totals,
                    "coverage_by_month": coverage, "clocks": class_clocks(a), "guard": res["guard"],
                    "conservation_residual": res["conservation_residual"], "classes": res["classes"],
                    "cohorts": rows_out, "conduit": conduit_rows(res, rows), "monthly_clocks": mc,
                    "cohort_window_clocks": windows, "cells": cells,
                    "wallets_in_circulation": panel["N"], "wallet_chains": wallet_shares,
                    "wallet_chain_mass": wallet_mass, "wallet_cells": wallet_cells},
        "criteria": criteria,
    })


def print_criteria(record: dict) -> None:
    print("\n== criteria")
    for name, mapping in record["mapping"].items():
        print(f"  {name} mapping: " + "; ".join(f"{k} -> {v}" for k, v in mapping.items()))
    for c in record["criteria"]:
        verdict = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        grid = f" grid {c['grid']}" + (f" {c['grid_split']}" if "grid_split" in c else "") if "grid" in c else ""
        print(f"  {c['name']} [{c['kind']}] {verdict}{grid}: {c['statement']}\n      {c['detail']}")
    cells = record["objects"]["cells"]
    print("\n  cells (area | age): rival state, own state; default low-high, network, pool")
    for key, rec in cells.items():
        base = next((x for x in rec["settings"] if x["min_cohort"] == MIN_COHORT and x["start_at"] == "mid"
                     and x["window"] == "quarter"), {})
        nums = ("" if "low" not in base else
                f"{100 * base['low']:.1f}-{100 * base['high']:.1f}, {100 * base['network']:.1f}, {100 * base['pool']:.1f}")
        print(f"   {key:28s} {rec['rival']:18s} {rec['own']:20s} {nums}")


def print_wallet_cells(record: dict) -> None:
    cells = record["objects"]["wallet_cells"]
    print("\n  B114-4 cells (area | age): state; default low-high, our wallet chain, the rival's wallet chain")
    for key, rec in cells.items():
        base = next((x for x in rec["settings"] if x["min_cohort"] == MIN_COHORT and x["start_at"] == "mid"
                     and x["window"] == "quarter"), {})
        nums = ("" if "low" not in base else f"{100 * base['low']:.1f}-{100 * base['high']:.1f},"
                f" {100 * base['wallet_network']:.1f}, {100 * base['wallet_pool']:.1f}")
        state = rec["rival"] if rec["rival"] != "moves with a knob" else f"moves (rival's chain {rec['pool_in_range']})"
        print(f"   {key:28s} {state:34s} {nums}")


def write_record(record: dict, path: Path) -> None:
    path.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Self-test: a synthetic archive with every seeded fault the checks exist for
# ---------------------------------------------------------------------------

def _archive(path: Path, txns: str, users: str, extra: dict | None = None) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("data/sarafu_txns_20200125-20210615.csv", txns)
        zf.writestr("data/sarafu_users_20210615.csv", users)
        for k, v in (extra or {}).items():
            zf.writestr(k, v)


def cmd_selftest() -> int:
    import numpy as np
    A, U1, U2, T = "0xa", "0xu1", "0xu2", "0xt"
    txns = ("id,timeset,transfer_subtype,source,target,weight,token_name,token_address\n"
            f"1,2020-01-25 10:00:00.000,DISBURSEMENT,{A},{U1},400,Sarafu,0x\n"
            f"2,2020-02-01 10:00:00.000,STANDARD,{U1},{U2},100,Sarafu,0x\n"
            f"3,2021-02-01 08:00:00.000,RECLAMATION,{U2},{A},2,Sarafu,0x\n"
            f"4,2020-03-01 09:00:00.000,AGENT_OUT,{U1},{T},50,Sarafu,0x\n"
            f"5,2020-10-19 09:00:00.000,RECLAMATION,{U1},{A},10,Sarafu,0x\n"
            f"6,2020-04-30 07:00:00.000,DISBURSEMENT,{A},{U1},1000,Kenyan Shilling,0x\n")
    head = "id,start,final_bal,gender,area_name,area_type,held_roles,business_type,xDAI_blockchain_address\n"
    users = (head +
             f"1,2020-01-01,-388,,other,other,ADMIN,system,{A}\n"
             f"2,2020-01-02,-388,,other,other,ADMIN,system,{A}\n"
             f"3,2020-01-25,240,f,Kilifi,periurban,BENEFICIARY,farming,{U1}\n"
             f"4,2020-01-26,98,m,Kinango Kwale,rural,GROUP_ACCOUNT,savings,{U2}\n"
             f"5,2020-01-01,50,,other,other,TOKEN_AGENT,system,{T}\n")
    checks = {}
    with tempfile.TemporaryDirectory() as d:
        good = Path(d) / "good.zip"
        _archive(good, txns, users + f"4,2020-01-26,98,m,Kinango Kwale,rural,GROUP_ACCOUNT,savings,{U2}\n")
        a = Archive(good)
        got = descriptor_totals(a)
        checks["a clean archive has no problem"] = a.problems == []
        checks["an exact repeat row is counted once, and said so"] = (len(a.users) == 4
                                                                        and any("repeat an earlier row" in n for n in a.notes))
        checks["staff rows sharing a wallet are one wallet, and said so"] = any("staff wallet" in n for n in a.notes)
        checks["a row in another unit is left out, and said so"] = (len(a.txns) == 5
                                                                     and any("Kenyan Shilling" in n for n in a.notes))
        checks["demurrage window sums only the reclamation inside it"] = got["demurrage_reclaimed"] == 2.0
        checks["agent_out total"] = got["agent_out_total"] == 50.0
        checks["balances rebuilt from flows match final_bal"] = (got["accounts_matching_final_balance"] == 3
                                                                   and got["accounts_not_matching_final_balance"] == 0)
        checks["admin wallets left out of the total"] = got["balance_from_flows_excluding_admin"] == 388.0
        clocks = class_clocks(a)
        checks["cash-out agent counts as system"] = clocks["system"]["wallets"] == 2
        checks["within share and transfers to others"] = (clocks["Kilifi"]["transfers_out"] == 150.0
                                                           and clocks["Kilifi"]["to_other_classes"] == 150.0
                                                           and clocks["Kilifi"]["within_share"] == 0.0)
        span = (dt.datetime(2021, 2, 1, 8) - dt.datetime(2020, 1, 25, 10)).total_seconds() / 86400
        kk_area = 100 * (dt.datetime(2021, 2, 1, 8) - dt.datetime(2020, 2, 1, 10)).total_seconds() / 86400
        checks["time-average balance integrates each balance over its own interval"] = (
            abs(clocks["Kinango Kwale"]["avg_balance"] - kk_area / span) < 1e-9)
        seeds = {
            "a row cut short": (txns[:-12], users, "column count"),
            "no final newline": (txns.rstrip("\n"), users, "newline"),
            "an unreadable timestamp": (txns.replace("2020-02-01 10:00:00.000", "Feb 1"), users, "timestamp"),
            "a non-numeric amount": (txns.replace(",100,", ",n/a,"), users, "non-numeric"),
            "an unknown subtype": (txns.replace("AGENT_OUT", "BURN"), users, "unknown subtypes"),
            "a missing column": (txns.replace("weight", "amount"), users, "no ['weight']"),
            "two different users on one address": (txns, users.replace(f"4,2020-01-26,98,m,Kinango Kwale,rural,GROUP_ACCOUNT,savings,{U2}",
                                                                       f"4,2020-01-26,98,m,Kinango Kwale,rural,GROUP_ACCOUNT,savings,{U1}"), "share one address"),
            "an endpoint with no wallet": (txns.replace(f"STANDARD,{U1},{U2}", f"STANDARD,{U1},0xnobody"), users, "not in the users table"),
        }
        for name, (tx, us, needle) in seeds.items():
            p = Path(d) / "seed.zip"
            _archive(p, tx, us)
            checks[f"caught: {name}"] = any(needle in q for q in Archive(p).problems)
        mismatch = Path(d) / "mismatch.zip"
        _archive(mismatch, txns, users.replace("GROUP_ACCOUNT,savings,", "GROUP_ACCOUNT,savings,").replace("4,2020-01-26,98", "4,2020-01-26,97"))
        checks["caught: a final balance that the flows do not give"] = (
            descriptor_totals(Archive(mismatch))["accounts_not_matching_final_balance"] == 1)
        two = Path(d) / "two.zip"
        _archive(two, txns, users, {"data/old_txns_copy.csv": txns})
        checks["caught: two transaction tables"] = any("no single txns" in q for q in Archive(two).problems)

    # Block five. A cohort small enough to follow by hand, in thousands so that it passes MIN_COHORT.
    # Kinango Kwale receives 100,000 of new money on 2020-02-10 into a wallet that already holds
    # 400,000 converted; 50,000 of that wallet's balance goes to a neighbour in the same area (10,000
    # of it new money), half of the neighbour's balance goes to Mukuru Nairobi (5,000 new money),
    # Mukuru Nairobi's 25,000 is reclaimed, and the neighbour then pays 60,000 against a balance of
    # 25,000, which the guard counts and which carries its last 5,000 of new money across.
    S_, a1, a2, b1, c1 = "0xs", "0xa1", "0xa2", "0xb1", "0xc1"
    tx5 = ("id,timeset,transfer_subtype,source,target,weight,token_name,token_address\n"
           f"1,2020-01-25 10:00:00.000,DISBURSEMENT,{S_},{a1},400000,Sarafu,0x\n"
           f"2,2020-01-25 11:00:00.000,DISBURSEMENT,{S_},{c1},1000,Sarafu,0x\n"
           f"3,2020-02-10 10:00:00.000,DISBURSEMENT,{S_},{a1},100000,Sarafu,0x\n"
           f"4,2020-02-12 10:00:00.000,STANDARD,{a1},{a2},50000,Sarafu,0x\n"
           f"5,2020-02-20 10:00:00.000,STANDARD,{a2},{b1},25000,Sarafu,0x\n"
           f"6,2020-03-10 10:00:00.000,RECLAMATION,{b1},{S_},25000,Sarafu,0x\n"
           f"7,2020-03-15 10:00:00.000,STANDARD,{a2},{b1},60000,Sarafu,0x\n"
           f"8,2020-04-10 10:00:00.000,STANDARD,{c1},{b1},100,Sarafu,0x\n")
    us5 = (head +
           f"1,2020-01-01,-476000,,other,other,ADMIN,system,{S_}\n"
           f"2,2020-01-25,450000,f,Kinango Kwale,rural,BENEFICIARY,farming,{a1}\n"
           f"3,2020-01-25,-35000,f,Kinango Kwale,rural,BENEFICIARY,food,{a2}\n"
           f"4,2020-01-25,60100,m,Mukuru Nairobi,urban,BENEFICIARY,shop,{b1}\n"
           f"5,2020-01-25,900,m,Kilifi,periurban,BENEFICIARY,labour,{c1}\n")

    def near(x, y):
        return x is not None and abs(x - y) < 1e-9

    with tempfile.TemporaryDirectory() as d:
        p5 = Path(d) / "five.zip"
        _archive(p5, tx5, us5)
        a5 = Archive(p5)
        checks["block five archive is clean"] = a5.problems == []
        try:
            res = tag_pass(a5)
            rows = cohort_rows(res).get("Kinango Kwale", {})
        except Exception as exc:          # a broken pass must show up as a failed check, not a crash
            print(f"  tag pass raised {exc!r}")
            res, rows = {"guard": {}, "class_bal": None}, {}
        want = {"observed": {0: 0.95, 1: 1.0, 2: 90 / 95, 4: 90 / 95},
                "moved_share": {0: 0.10, 1: 5 / 95, 2: 5 / 95, 4: 5 / 95},
                "in_area_of_moved": {0: 0.5, 1: 1.0, 2: 0.0, 4: 0.0},
                "turnover": {0: 0.15, 1: 0.15, 2: 0.20, 4: 0.20},
                "within": {0: 2 / 3, 1: 2 / 3, 2: 0.5, 4: 0.5}}
        for key, by_age in want.items():
            got_ = rows.get(key, {})
            checks[f"hand cohort: {key} at ages 0, 1, 2 and 4"] = (
                set(got_) == set(by_age) and all(near(got_[g], v) for g, v in by_age.items()))
        checks["hand cohort: one entry month, 100,000 disbursed"] = (rows.get("cohorts") == 1
                                                                      and near(rows.get("disbursed"), 100_000.0))
        checks["guard counts the payment larger than its balance"] = (res["guard"].get("events") == 1
                                                                      and near(res["guard"].get("shortfall"), 35_000.0))

        # Block seven, on the same hand cohort. February 2020 in Kinango Kwale: 400,000 for 9 days,
        # 500,000 for 10 and 475,000 for 10; 50,000 paid within and 25,000 to Mukuru Nairobi. March in
        # Mukuru Nairobi: 25,000 for 9 days, nothing for 5, 60,000 for 17, and 25,000 reclaimed.
        try:
            mc5 = monthly_clocks(res)
            feb = mc5["Kinango Kwale"]["2020-02"]
            mar = mc5["Mukuru Nairobi"]["2020-03"]
        except Exception as exc:
            print(f"  block seven raised {exc!r}")
            feb, mar = {}, {}
        checks["monthly clocks by hand: 178 days spending, 534 days out of area, two thirds within"] = (
            near(feb.get("days_all"), 178.0) and near(feb.get("days_other"), 534.0) and near(feb.get("within"), 2 / 3))
        checks["reclaimed share of balance by hand"] = near(mar.get("reclaimed_per_30_days"), 25_000 / (1_245_000 / 31) * 30 / 31)
        det5 = rows.get("cohort_detail", [{}])[0] if rows else {}
        checks["cohort detail carries the pooled numbers of its only cohort"] = (
            det5.get("month") == "2020-02" and near(det5.get("observed", {}).get(0), 0.95)
            and near(det5.get("observed", {}).get(1), 1.0) and near(det5.get("observed", {}).get(4), 90 / 95)
            and near(det5.get("in_area_of_moved", {}).get(2), 0.0) and near(det5.get("turnover", {}).get(4), 0.20)
            and all(near(det5.get(k, {}).get(g), rows[k][g]) for k in ("network", "pool") for g in rows[k]))
        qf = res.get("flows", {}).get("2020Q1") if isinstance(res.get("flows"), dict) else None
        df = res.get("day_flows")
        checks["daily flows add up to the quarter's flows, reclamations in their own column"] = (
            qf is not None and df is not None and np.allclose(df[:67, :, :3].sum(axis=0), qf[:, :3])
            and np.allclose(df[:67, :, 3].sum(axis=0) + df[:67, :, 4].sum(axis=0), qf[:, 3])
            and near(df[45, res["classes"].index("Mukuru Nairobi"), 4], 25_000.0))
        try:
            rec5 = build_record(a5)
            text5 = json.dumps(rec5, sort_keys=True)
            names5 = [c_["name"] for c_ in rec5["criteria"]]
            inst5 = rec5["criteria"][0]["passed"]
            sweep5 = rec5["objects"]["cells"]
        except Exception as exc:
            print(f"  record raised {exc!r}")
            text5, names5, inst5, sweep5 = "", [], None, None
        checks["the record builds, serialises, and the toy's totals fail the descriptor check"] = (
            bool(text5) and names5 == ["B114-1", "B114-2", "B114-3", "B114-4"] and inst5 is False and sweep5 == {}
            and rec5["objects"]["wallet_cells"] == {} and "diagnostic_only" not in rec5)
        cb = res["class_bal"]
        kk = res.get("classes", []).index("Kinango Kwale") if "Kinango Kwale" in res.get("classes", []) else None
        checks["end-of-day class balance before and on the day of the new money"] = (
            cb is not None and kk is not None and near(cb[15, kk], 400_000.0) and near(cb[16, kk], 500_000.0))


    # Block six. New money enters Misc Nairobi (X); X pays 60,000 within X, then half of that wallet
    # to Mukuru Nairobi (Y); Y, holding 100,000 converted, pays a fifth of its balance to Kinango
    # Kwale (Z). At the first snapshot after the entry month: X 70,000, Y 24,000, Z 6,000.
    x1, x2, y1, z1, w1 = "0xx1", "0xx2", "0xy1", "0xz1", "0xw1"
    tx6 = ("id,timeset,transfer_subtype,source,target,weight,token_name,token_address\n"
           f"1,2020-01-25 10:00:00.000,DISBURSEMENT,{S_},{y1},100000,Sarafu,0x\n"
           f"2,2020-01-25 10:30:00.000,DISBURSEMENT,{S_},{w1},1000,Sarafu,0x\n"
           f"3,2020-02-05 10:00:00.000,DISBURSEMENT,{S_},{x1},100000,Sarafu,0x\n"
           f"4,2020-02-08 10:00:00.000,STANDARD,{x1},{x2},60000,Sarafu,0x\n"
           f"5,2020-02-10 10:00:00.000,STANDARD,{x2},{y1},30000,Sarafu,0x\n"
           f"6,2020-02-20 10:00:00.000,STANDARD,{y1},{z1},26000,Sarafu,0x\n"
           f"7,2020-04-10 10:00:00.000,STANDARD,{w1},{z1},100,Sarafu,0x\n")
    us6 = (head +
           f"1,2020-01-01,-201000,,other,other,ADMIN,system,{S_}\n"
           f"2,2020-01-25,40000,f,Misc Nairobi,urban,BENEFICIARY,food,{x1}\n"
           f"3,2020-01-25,30000,f,Misc Nairobi,urban,BENEFICIARY,shop,{x2}\n"
           f"4,2020-01-25,104000,m,Mukuru Nairobi,urban,BENEFICIARY,shop,{y1}\n"
           f"5,2020-01-25,26100,m,Kinango Kwale,rural,BENEFICIARY,farming,{z1}\n"
           f"6,2020-01-25,900,m,Kilifi,periurban,BENEFICIARY,labour,{w1}\n")
    with tempfile.TemporaryDirectory() as d:
        p6 = Path(d) / "six.zip"
        _archive(p6, tx6, us6)
        a6 = Archive(p6)
        checks["block six archive is clean"] = a6.problems == []
        try:
            res6, rows6 = tagged(a6)
            cond6 = conduit_rows(res6, rows6).get("Misc Nairobi", {})
        except Exception as exc:
            print(f"  block six raised {exc!r}")
            cond6 = {}
        obs6 = cond6.get("observed", {})
        checks["first stop is the class paid most outside the entry class"] = cond6.get("first_stop") == "Mukuru Nairobi"
        checks["share in the first stop and beyond it, by hand"] = (
            near(obs6.get("at_first_stop", {}).get(0), 0.24) and near(obs6.get("beyond", {}).get(0), 0.06))
        checks["cohort range of the share beyond the first stop, one cohort"] = (
            near(obs6.get("beyond_cohort_min", {}).get(0), 0.06) and near(obs6.get("beyond_cohort_max", {}).get(0), 0.06))
        mix6 = obs6.get("mix_of_money_out", {}).get(0, {})
        checks["mix of the money that has left, by hand"] = (
            near(mix6.get("Mukuru Nairobi"), 0.8) and near(mix6.get("Kinango Kwale"), 0.2) and near(mix6.get("Kilifi"), 0.0))
        r6 = rows6.get("Misc Nairobi", {}) if cond6 else {}
        ix6 = res6["classes"].index("Misc Nairobi") if cond6 else None
        checks["chain composition gives the same entry share as block five's chain rows"] = bool(r6) and all(
            set(r6["composition"][kind]) == set(r6[kind]) and all(
                near(vec[ix6] / vec.sum(), r6[kind][g]) for g, vec in r6["composition"][kind].items())
            for kind in ("network", "pool", "hybrid"))

    # Pool after hop 1, where it must equal the network chain: new money enters Misc Nairobi and is
    # paid to three areas; Mukuru Nairobi and Kinango Kwale pay nobody, and Kilifi pays Mukuru Nairobi
    # but never receives, so every class but the entry class has the same row in both chains. The
    # one-pool chain still differs, because Kilifi's payments swell Mukuru Nairobi's receipts.
    w7, x7, x8, y7, z7 = "0xw7", "0xx7", "0xx8", "0xy7", "0xz7"
    tx7 = ("id,timeset,transfer_subtype,source,target,weight,token_name,token_address\n"
           f"1,2020-01-25 10:00:00.000,DISBURSEMENT,{S_},{w7},200000,Sarafu,0x\n"
           f"2,2020-02-05 10:00:00.000,DISBURSEMENT,{S_},{x7},100000,Sarafu,0x\n"
           f"3,2020-02-08 10:00:00.000,STANDARD,{x7},{x8},20000,Sarafu,0x\n"
           f"4,2020-02-10 10:00:00.000,STANDARD,{x7},{y7},30000,Sarafu,0x\n"
           f"5,2020-02-12 10:00:00.000,STANDARD,{x7},{z7},10000,Sarafu,0x\n"
           f"6,2020-02-15 10:00:00.000,STANDARD,{w7},{y7},100000,Sarafu,0x\n"
           f"7,2020-04-10 10:00:00.000,STANDARD,{w7},{y7},100,Sarafu,0x\n")
    us7 = (head +
           f"1,2020-01-01,-300000,,other,other,ADMIN,system,{S_}\n"
           f"2,2020-01-25,99900,m,Kilifi,periurban,BENEFICIARY,labour,{w7}\n"
           f"3,2020-01-25,40000,f,Misc Nairobi,urban,BENEFICIARY,food,{x7}\n"
           f"4,2020-01-25,20000,f,Misc Nairobi,urban,BENEFICIARY,shop,{x8}\n"
           f"5,2020-01-25,130100,m,Mukuru Nairobi,urban,BENEFICIARY,shop,{y7}\n"
           f"6,2020-01-25,10000,m,Kinango Kwale,rural,BENEFICIARY,farming,{z7}\n")
    with tempfile.TemporaryDirectory() as d:
        p7 = Path(d) / "seven.zip"
        _archive(p7, tx7, us7)
        a7 = Archive(p7)
        try:
            _, rows7 = tagged(a7)
            r7 = rows7.get("Misc Nairobi", {})
        except Exception as exc:
            print(f"  hop-one toy raised {exc!r}")
            r7 = {}
        checks["pool after hop 1 equals the network chain where only the entry row differs"] = (
            a7.problems == [] and bool(r7) and set(r7["hybrid"]) == set(r7["network"])
            and all(near(r7["hybrid"][g], r7["network"][g]) for g in r7["network"])
            and any(abs(r7["pool"][g] - r7["network"][g]) > 1e-3 for g in r7["network"]))

    # Block eight. Wallet chains: the two that use area speed with area or pool payees must lump to
    # block five's chains on every toy; and on a toy where the wallet holding the new money pays only
    # a neighbour who pays only it back, every chain with the wallets' own payees keeps all of it in
    # the entry area, with nothing lost, while area Misc Nairobi as a whole pays Mukuru Nairobi through
    # a third wallet and buys from the vendor.
    x31, x32, x33, y31 = "0xx31", "0xx32", "0xx33", "0xy31"
    tx8 = ("id,timeset,transfer_subtype,source,target,weight,token_name,token_address\n"
           f"1,2020-01-25 10:00:00.000,DISBURSEMENT,{S_},{x33},100000,Sarafu,0x\n"
           f"2,2020-01-25 10:30:00.000,DISBURSEMENT,{S_},{y31},50000,Sarafu,0x\n"
           f"3,2020-02-05 10:00:00.000,DISBURSEMENT,{S_},{x31},100000,Sarafu,0x\n"
           f"10,2020-01-29 10:00:00.000,DISBURSEMENT,{S_},{x33},100,Sarafu,0x\n"
           f"4,2020-02-10 10:00:00.000,STANDARD,{x31},{x32},10000,Sarafu,0x\n"
           f"5,2020-02-12 10:00:00.000,STANDARD,{x32},{x31},5000,Sarafu,0x\n"
           f"6,2020-02-15 10:00:00.000,STANDARD,{x33},{y31},80000,Sarafu,0x\n"
           f"7,2020-02-20 10:00:00.000,STANDARD,{x33},{S_},5000,Sarafu,0x\n"
           f"8,2020-03-01 10:00:00.000,STANDARD,{y31},{x33},10000,Sarafu,0x\n"
           f"9,2020-04-10 10:00:00.000,STANDARD,{y31},{x33},100,Sarafu,0x\n")
    us8 = (head +
           f"1,2020-01-01,-245100,,other,other,ADMIN,system,{S_}\n"
           f"2,2020-01-25,95000,f,Misc Nairobi,urban,BENEFICIARY,food,{x31}\n"
           f"3,2020-01-25,5000,f,Misc Nairobi,urban,BENEFICIARY,shop,{x32}\n"
           f"4,2020-01-25,25200,m,Misc Nairobi,urban,BENEFICIARY,shop,{x33}\n"
           f"5,2020-01-25,39900,m,Mukuru Nairobi,urban,BENEFICIARY,shop,{y31}\n")
    lumps, own_keep, area_leak = [], None, None
    with tempfile.TemporaryDirectory() as d:
        for label, tx_, us_ in (("five", tx5, us5), ("six", tx6, us6), ("eight", tx8, us8)):
            pth = Path(d) / f"w_{label}.zip"
            _archive(pth, tx_, us_)
            aw = Archive(pth)
            try:
                res_w, rows_w = tagged(aw)
                shares_w, mass_w = wallet_chain_rows(res_w, wallet_panel(aw, res_w))
            except Exception as exc:
                print(f"  wallet chains on toy {label} raised {exc!r}")
                lumps.append(False)
                continue
            ok_lump = bool(rows_w) and all(
                set(shares_w[vn].get(cl, {})) == set(r_[kind]) and all(abs(shares_w[vn][cl][g] - r_[kind][g]) < 1e-12 for g in r_[kind])
                for cl, r_ in rows_w.items() for vn, kind in (("area speed, area payees", "network"), ("area speed, pool payees", "pool")))
            lumps.append(ok_lump and aw.problems == [])
            if label == "eight":
                sh = {vn: shares_w[vn].get("Misc Nairobi", {}) for vn, _, _ in WALLET_VARIANTS}
                ms = {vn: mass_w[vn].get("Misc Nairobi", {}) for vn, _, _ in WALLET_VARIANTS}
                # area speed carries the area's rate out of circulation (the vendor purchase) to every
                # wallet, so only the chain with the wallets' own speed keeps the whole mass
                own_keep = (all(sh[vn] and all(abs(v - 1.0) < 1e-12 for v in sh[vn].values())
                                for vn in ("own speed, own payees", "area speed, own payees"))
                            and all(abs(m_ - 100_000.0) < 1e-6 for m_ in ms["own speed, own payees"].values())
                            and all(m_ < 100_000.0 - 1.0 for m_ in ms["area speed, own payees"].values()))
                area_leak = bool(sh["own speed, area payees"].get(4, 1.0) < 0.999 and sh["own speed, pool payees"].get(4, 1.0) < 0.999)
    checks["wallet chains with area speed lump to block five's network and one-pool chains on three toys"] = len(lumps) == 3 and all(lumps)
    checks["with the wallets' own payees the new money stays with the two wallets that pay each other, none lost"] = own_keep is True
    checks["with area or pool payees the same new money leaks out of the area"] = area_leak is True

    # B114-4 machinery. Half-year windows: the wallet chains with area speed must lump to block five's
    # chains run on half-year rates, on the same three toys.
    half_lumps = []
    with tempfile.TemporaryDirectory() as d:
        for label, tx_, us_ in (("five", tx5, us5), ("six", tx6, us6), ("eight", tx8, us8)):
            pth = Path(d) / f"h_{label}.zip"
            _archive(pth, tx_, us_)
            ah = Archive(pth)
            try:
                res_h8, _ = tagged(ah)
                rows_h8 = cohort_rows(res_h8, window="half")
                shares_h8, _ = wallet_chain_rows(res_h8, wallet_panel(ah, res_h8), window="half")
                half_lumps.append(bool(rows_h8) and all(
                    set(shares_h8[vn].get(cl, {})) == set(r_[kind]) and all(abs(shares_h8[vn][cl][g] - r_[kind][g]) < 1e-12 for g in r_[kind])
                    for cl, r_ in rows_h8.items() for vn, kind in (("area speed, area payees", "network"), ("area speed, pool payees", "pool"))))
            except Exception as exc:
                print(f"  half-year wallet chains on toy {label} raised {exc!r}")
                half_lumps.append(False)
    checks["on half-year rates the area-speed wallet chains lump to block five's chains on three toys"] = len(half_lumps) == 3 and all(half_lumps)

    saved_rows, saved_wallet = globals()["cohort_rows"], globals()["wallet_chain_rows"]

    def fake_rows_w(res_, min_cohort=MIN_COHORT, start_at="mid", window="quarter"):
        return {"Nyanza": {"cohorts_at": {13: 4, 26: 3}, "cohort_min": {13: 0.90, 26: 0.90}, "cohort_max": {13: 0.99, 26: 0.99}},
                "other": {"cohorts_at": {13: 5}, "cohort_min": {13: 0.9}, "cohort_max": {13: 0.99}}}

    def fake_wallet(res_, panel_, min_cohort=MIN_COHORT, start_at="mid", window="quarter", variants=WALLET_VARIANTS):
        ours = {"Nyanza": {13: 0.95, 26: 0.95 if window == "quarter" else 0.80}, "other": {13: 0.95}}
        theirs = {"Nyanza": {13: 0.50, 26: 0.40}, "other": {13: 0.50}}
        return {WALLET_OURS: ours, WALLET_RIVAL: theirs}, {}

    globals()["cohort_rows"], globals()["wallet_chain_rows"] = fake_rows_w, fake_wallet
    try:
        wc = sweep_wallet_cells({}, {})
    except Exception as exc:
        print(f"  wallet sweep raised {exc!r}")
        wc = {}
    finally:
        globals()["cohort_rows"], globals()["wallet_chain_rows"] = saved_rows, saved_wallet
    checks["wallet sweep: our chain is the network one, the rival's the pool one, steadiness per chain"] = (
        sorted(wc) == ["Nyanza | 13 weeks", "Nyanza | 26 weeks"]
        and wc["Nyanza | 13 weeks"]["rival"] == "B" and wc["Nyanza | 26 weeks"]["rival"] == "moves with a knob"
        and wc["Nyanza | 26 weeks"]["pool_in_range"] == "outside" and wc["Nyanza | 26 weeks"]["network_in_range"] == "moves with a knob"
        and all(len(v["settings"]) == 18 for v in wc.values()))
    c4 = criterion_rival(wc, name="B114-4", premise="p4", entailment="e4", statement="s4") if wc else {}
    checks["B114-4 carries its own name, premise and entailment, and passes on steady misses"] = (
        c4.get("name") == "B114-4" and c4.get("rival_premise") == "p4" and c4.get("rival_entailment") == "e4"
        and c4.get("statement") == "s4" and c4.get("passed") is True and c4.get("grid") == "B")
    # One day's step by hand: two wallets in one area, each holding 100 on average over ten days;
    # the first pays the second 10 a day and 5 a day out of circulation, the second pays nothing.
    pan = {"N": 2, "wclass": np.array([0, 0]), "qdays": [(0, 10)], "balday": np.array([[1000.0, 1000.0]]),
           "sink": np.array([[50.0, 0.0]]), "edges": [(np.array([0]), np.array([1]), np.array([100.0]))]}
    op_o = wallet_operator({"classes": ["A"]}, pan, 0, "own", "own")
    op_a = wallet_operator({"classes": ["A"]}, pan, 0, "area", "own")
    checks["one day by hand, own speed: 15% leaves the first wallet, 10% to the second, the second stays"] = (
        np.allclose(op_o["stay"], [0.85, 1.0]) and np.allclose(op_o["edges"][2], [0.10]) and np.allclose(op_o["area_c"], [0.0, 0.0]))
    checks["one day by hand, area speed: both leave at 7.5%, the idle wallet by the area's payees"] = (
        np.allclose(op_a["stay"], [0.925, 0.925]) and np.allclose(op_a["edges"][2], [0.05]) and np.allclose(op_a["area_c"], [0.0, 0.05]))
    pan_fast = {**pan, "balday": np.array([[50.0, 50.0]]), "sink": np.array([[0.0, 0.0]]),
                "edges": [(np.array([0]), np.array([1]), np.array([200.0]))]}
    op_f = wallet_operator({"classes": ["A"]}, pan_fast, 0, "area", "area")
    checks["a wallet or area paying out more than it holds in a day leaves at most all of it"] = (
        np.allclose(op_f["stay"], [0.0, 0.0]) and np.allclose(op_f["area_c"], [1.0, 1.0]))

    # The chains, on flows whose rows can be written down by hand: class A holds 100 and pays 10 a
    # day to itself, 20 to B and 5 out of circulation; B holds 200 and pays 40 a day to itself.
    import numpy as np
    days_q = 91
    res_c = {"classes": ["A", "B"], "day0": dt.datetime(2020, 1, 1),
             "class_bal": np.tile([100.0, 200.0], (days_q, 1)),
             "flows": {"2020Q1": np.array([[10.0, 20.0, 5.0], [0.0, 40.0, 0.0]]) * days_q}}
    net, pool = chains(res_c, "2020Q1")
    checks["network chain rows: stay, pay across, leave"] = (
        net is not None and np.allclose(net, [[0.75, 0.20, 0.05], [0.0, 1.0, 0.0]], atol=1e-12))
    checks["one-pool chain rows: spending spread by share of receipts"] = (
        pool is not None and np.allclose(pool, [[0.65 + 0.3 / 7, 1.8 / 7, 0.05], [0.2 / 7, 0.8 + 1.2 / 7, 0.0]], atol=1e-12))
    hyb = hybrid_rows(net, pool, 0) if net is not None else None
    checks["pool after hop 1: the entry row from the network, the others from the pool"] = (
        hyb is not None and np.allclose(hyb, [[0.75, 0.20, 0.05], [0.2 / 7, 0.8 + 1.2 / 7, 0.0]], atol=1e-12)
        and np.allclose(pool, [[0.65 + 0.3 / 7, 1.8 / 7, 0.05], [0.2 / 7, 0.8 + 1.2 / 7, 0.0]], atol=1e-12))
    res_s = {"classes": ["A"], "day0": dt.datetime(2020, 1, 1), "class_bal": np.tile([10.0], (days_q, 1)),
             "flows": {"2020Q1": np.array([[15.0, 10.0]]) * days_q}}
    net_s, _ = chains(res_s, "2020Q1")
    checks["a class that pays out more than it holds in a day is scaled to one"] = (
        net_s is not None and np.allclose(net_s, [[0.6, 0.4]], atol=1e-12))

    # Criteria. Cells by hand: our chain at 95, the rival's at 50.
    checks["rival cell B: ours inside, the rival's outside"] = rival_cell(0.90, 0.99, 0.95, 0.50) == "B"
    checks["rival cell C: the rival's inside, ours outside"] = rival_cell(0.40, 0.60, 0.95, 0.50) == "C"
    checks["rival cell A: both inside"] = rival_cell(0.40, 0.99, 0.95, 0.50) == "A"
    checks["rival cell both unmet: both outside"] = rival_cell(0.70, 0.80, 0.95, 0.50) == "both_unmet"
    checks["own cell: range above the midpoint 72.5 is nearer ours"] = own_cell(0.80, 0.99, 0.95, 0.50) == "nearer ours"
    checks["own cell: range below the midpoint is nearer the rival's"] = own_cell(0.40, 0.60, 0.95, 0.50) == "nearer the rival's"
    checks["own cell: a range across the midpoint is not read"] = own_cell(0.60, 0.90, 0.95, 0.50) == "straddle"
    checks["own cell: with the chains the other way round, below the midpoint is nearer ours"] = (
        own_cell(0.10, 0.20, 0.15, 0.60) == "nearer ours" and own_cell(0.50, 0.70, 0.15, 0.60) == "nearer the rival's")

    parts = {"B": ("outside", "inside"), "A": ("inside", "inside"), "C": ("inside", "outside"),
             "both_unmet": ("outside", "outside"), "moves with a knob": ("moves with a knob", "moves with a knob"),
             "miss, ours moving": ("outside", "moves with a knob"), "hold, ours moving": ("inside", "moves with a knob")}

    def cells_of(rival_states, own_states):
        out_ = {}
        for i, (r_, o_) in enumerate(zip(rival_states, own_states)):
            pool_, net_ = parts[r_]
            letter = r_ if r_ in ("A", "B", "C", "both_unmet") else "moves with a knob"
            out_[f"x{i}"] = {"rival": letter, "own": o_, "pool_in_range": pool_, "network_in_range": net_}
        return out_

    cr = criterion_rival(cells_of(["B", "B", "both_unmet", "A", "moves with a knob", "miss, ours moving"], ["nearer ours"] * 6))
    checks["rival criterion passes when the rival misses in every counted cell, split by cell"] = (
        cr["passed"] is True and cr["grid"] == "mixed" and cr["grid_split"] == {"A": 1, "B": 2, "both_unmet": 1}
        and cr["rival_holds_share"] == 0.2 and "grid_note" in cr and "1 of them still read as a miss" in cr["grid_note"]["not placed"])
    checks["where the rival's chain holds and ours moves with a knob, the cell is not read"] = (
        criterion_rival(cells_of(["B", "hold, ours moving"], ["nearer ours"] * 2))["passed"] is True
        and criterion_rival(cells_of(["hold, ours moving"], ["straddle"]))["passed"] is None)
    checks["a steady miss by the rival counts even where our chain moves with a knob"] = (
        criterion_rival(cells_of(["miss, ours moving"], ["straddle"]))["passed"] is True
        and criterion_rival(cells_of(["miss, ours moving"], ["straddle"]))["grid"] == "unread")
    cf = criterion_rival(cells_of(["C", "C", "A"], ["nearer the rival's"] * 3))
    checks["rival criterion fails when the rival holds and ours misses in every counted cell"] = (
        cf["passed"] is False and cf["grid"] == "mixed" and cf["grid_split"] == {"A": 1, "C": 2})
    cm = criterion_rival(cells_of(["B", "C"], ["nearer ours", "nearer the rival's"]))
    checks["rival criterion gives no verdict on a mixture"] = cm["passed"] is None and cm["grid_split"] == {"B": 1, "C": 1}
    ca = criterion_rival(cells_of(["A", "A"], ["straddle"] * 2))
    checks["rival criterion with only A cells: no verdict, grid A, never a FAIL"] = ca["passed"] is None and ca["grid"] == "A"
    cu = criterion_rival(cells_of(["moves with a knob"], ["moves with a knob"]))
    checks["rival criterion with nothing placed is unread and carries no verdict"] = (
        cu["passed"] is None and cu["grid"] == "unread" and "grid_split" not in cu)
    checks["own criterion: pass, fail, no verdict"] = (
        criterion_own(cells_of(["B"] * 3, ["nearer ours", "straddle", "nearer ours"]))["passed"] is True
        and criterion_own(cells_of(["C"] * 2, ["nearer the rival's", "straddle"]))["passed"] is False
        and criterion_own(cells_of(["B"] * 2, ["nearer ours", "nearer the rival's"]))["passed"] is None
        and criterion_own(cells_of(["A"], ["straddle"]))["passed"] is None)
    good_totals = {"demurrage_reclaimed": 352_834.0, "agent_out_total": 6_172_074.95,
                   "balance_from_flows_excluding_admin": 1.0, "accounts_matching_final_balance": 1,
                   "accounts_not_matching_final_balance": 0, "worst_balance_gap": 0.0}
    checks["instrument criterion passes on matching totals and fails on each seeded fault"] = (
        criterion_instrument([], good_totals, 1e-7, 1e6)["passed"] is True
        and criterion_instrument(["a problem"], good_totals, 1e-7, 1e6)["passed"] is False
        and criterion_instrument([], {**good_totals, "agent_out_total": 6_172_090.0}, 1e-7, 1e6)["passed"] is False
        and criterion_instrument([], {**good_totals, "demurrage_reclaimed": 352_800.0}, 1e-7, 1e6)["passed"] is False
        and criterion_instrument([], good_totals, 5.0, 1e6)["passed"] is False)
    checks["flow windows: quarters and half-years name their days"] = (
        period_bounds("2020Q4")[:2] == (dt.datetime(2020, 10, 1), dt.datetime(2021, 1, 1))
        and period_bounds("2021H1") == (dt.datetime(2021, 1, 1), dt.datetime(2021, 7, 1), ["2021Q1", "2021Q2"])
        and period_key(dt.datetime(2020, 8, 3), "half") == "2020H2" and period_key(dt.datetime(2020, 8, 3), "quarter") == "2020Q3")
    checks["chain start: first day of the entry month, mid-month, month end"] = (
        chain_start(dt.datetime(2020, 3, 1), "start") == dt.datetime(2020, 2, 1)
        and chain_start(dt.datetime(2021, 1, 1), "start") == dt.datetime(2020, 12, 1)
        and chain_start(dt.datetime(2020, 3, 1), "mid") == dt.datetime(2020, 2, 15)
        and chain_start(dt.datetime(2020, 3, 1), "end") == dt.datetime(2020, 3, 1))
    saved_rows = globals()["cohort_rows"]

    def fake_rows(res_, min_cohort=MIN_COHORT, start_at="mid", window="quarter"):
        moved = 0.95 if start_at == "end" else 0.50     # at month end the rival's value moves inside the range
        steady = {"cohort_min": {13: 0.90}, "cohort_max": {13: 0.99}, "network": {13: 0.95}, "pool": {13: 0.50}}
        return {"Kilifi": {"cohorts_at": {4: 3, 8: 2}, "cohort_min": {4: 0.90, 8: 0.90}, "cohort_max": {4: 0.99, 8: 0.99},
                           "network": {4: 0.95, 8: 0.95}, "pool": {4: moved, 8: 0.50}},
                "Nyanza": {"cohorts_at": {13: 4, 26: 3}, "cohort_min": {13: 0.90, 26: 0.90}, "cohort_max": {13: 0.99, 26: 0.99},
                           "network": {13: 0.95, 26: 0.95 if window == "quarter" else 0.80}, "pool": {13: 0.50, 26: 0.50}},
                "other": {"cohorts_at": {13: 5}, **steady}}

    globals()["cohort_rows"] = fake_rows
    try:
        cells_f = sweep_cells({})
    except Exception as exc:
        print(f"  sweep raised {exc!r}")
        cells_f = {}
    finally:
        globals()["cohort_rows"] = saved_rows
    checks["sweep: three cohorts to read a cell, labels that are not areas skipped, every setting read"] = (
        sorted(cells_f) == ["Kilifi | 4 weeks", "Nyanza | 13 weeks", "Nyanza | 26 weeks"]
        and all(len(v["settings"]) == 18 for v in cells_f.values()))
    checks["sweep: a state that moves with a knob is not read, a steady one is"] = (
        cells_f.get("Kilifi | 4 weeks", {}).get("rival") == "moves with a knob"
        and cells_f.get("Kilifi | 4 weeks", {}).get("own") == "moves with a knob"
        and cells_f.get("Nyanza | 13 weeks", {}).get("rival") == "B"
        and cells_f.get("Nyanza | 13 weeks", {}).get("own") == "nearer ours"
        and cells_f.get("Nyanza | 26 weeks", {}).get("rival") == "moves with a knob"
        and cells_f.get("Nyanza | 26 weeks", {}).get("pool_in_range") == "outside"
        and cells_f.get("Nyanza | 26 weeks", {}).get("network_in_range") == "moves with a knob")
    checks["settle: one state, or not read"] = (settle(["B", "B"]) == "B" and settle(["B", "both_unmet"]) == "moves with a knob"
                                                and settle(["B", "no object"]) == "moves with a knob")
    res_h = {"classes": ["A", "B"], "day0": dt.datetime(2020, 1, 1), "class_bal": np.tile([100.0, 200.0], (182, 1)),
             "flows": {"2020Q1": np.array([[10.0, 20.0, 5.0], [0.0, 40.0, 0.0]]) * 91,
                       "2020Q2": np.array([[10.0, 20.0, 5.0], [0.0, 40.0, 0.0]]) * 91}}
    net_h, _ = chains(res_h, "2020H1")
    checks["a half-year chain from two identical quarters equals the quarter's chain"] = (
        net_h is not None and np.allclose(net_h, [[0.75, 0.20, 0.05], [0.0, 1.0, 0.0]], atol=1e-12))
    ok = all(checks.values())
    for name, good_ in checks.items():
        print(f"  {'ok' if good_ else 'WRONG'}  {name}")
    print(f"\nselftest: {sum(checks.values())} of {len(checks)}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--block", type=int, action="append", help="run only these blocks (repeatable)")
    ap.add_argument("--archive", default=str(RAW / ARCHIVE_NAME))
    ap.add_argument("--criteria", action="store_true", help="print the criteria after the blocks")
    ap.add_argument("--write", action="store_true", help="print the criteria and write results/b114_sarafu.json")
    a = ap.parse_args()
    if a.selftest:
        return cmd_selftest()
    path = Path(a.archive)
    if not path.exists():
        print(f"no archive at {path}; download it from UK Data Service ReShare record 855142 first")
        return 1
    digest = sha256_of(path)
    manifest_path = path.parent / MANIFEST.name     # the manifest sits beside the archive it records
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if manifest.get(path.name) and manifest[path.name] != digest:
        print(f"PROBLEM the archive differs from the one first read (sha256 {manifest[path.name][:12]}...)")
        return 1
    if path.name not in manifest:
        manifest[path.name] = digest
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"archive {path.name}, sha256 {digest}")
    archive = Archive(path)
    if not a.write:
        for k, fn in enumerate(BLOCKS):
            if not a.block or k in a.block:
                fn(archive)
    if a.criteria or a.write:
        record = build_record(archive)
        print_criteria(record)
        print_wallet_cells(record)
        if a.write:
            out = ROOT / "results" / "b114_sarafu.json"
            write_record(record, out)
            print(f"\nwrote {out.relative_to(ROOT)}")
    return 0 if not archive.problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
