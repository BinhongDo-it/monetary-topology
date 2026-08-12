"""B5-3, B5-3b and B5-4: the calibration arm, and the collapse rule's first check.

Registered in ``docs/b5_orphan_prereg.md`` §4.4, §4.4a and §4.5.

**Nothing else in stage B5 may be read until this passes** (§8).

The arm, and the one it replaced
--------------------------------

The first version paired Ámbito's wholesale rate against **argentinadatos'**
wholesale rate, on the grounds that one number in two formats must come back
equal. Two dates checked by hand agreed to the cent, and the arm was registered
on that.

**Running it over the window showed the premise is false, and the guard is what
found it.** With BCRA's Comunicación A 3500 as an independent referee:

===========================  ========  ========  ========
deviation from BCRA A 3500    median      p90       max
===========================  ========  ========  ========
Ámbito ``mayorista``          2.6e-3    8.0e-3    1.07e-1
argentinadatos ``mayorista``  2.6e-3    1.55e-2   **1.60**
===========================  ========  ========  ========

On 13 December 2023 Ámbito and BCRA both jump from about 365 to about 800, the
Milei devaluation, and **argentinadatos sits at 365.45 for weeks**. Its longest
run of an unchanged sell quote is **71 days**, against 13 for its own ``tarjeta``
series. So the fault is in that one series and not in the publisher, and
``tarjeta`` survives as the dating instrument of §5.2.

**This is the arm doing its job.** It did not detect an error in this project's
pipeline, because there was not one; BCRA confirms the Ámbito side through a
completely separate parser. It detected that its own premise was wrong, which is
the only way a zero calibration can pay for itself when the pipeline is sound.

What runs instead: a bounded-agreement arm, with the bound derived rather than
observed
--------------------------------------------------------------------------------

**Ámbito ``mayorista`` against BCRA A 3500.** Two parsers with nothing in common:
comma decimals, thousands separators and ``DD/MM/YYYY`` on one side; JSON numbers
and ISO dates on the other. Two publishers, one of them a central bank.

They are **not the same quantity** — A 3500 is the central bank's reference and
``mayorista`` is the interbank market — so the answer is not exactly zero and the
criterion is not equality. What the arm has to catch is a **parse error**, and
the bounds come from that rather than from the data:

- **a systematic error** moves every row. The smallest parse error worth naming
  is a factor of ten, which is ``2·log(10) = 4.6`` in the units below. The
  registered bound on the **median** is ``0.02``, two hundred and thirty times
  tighter than the smallest thing it must catch.
- **a partial error** touches only some rows — a thousands-separator bug reaches
  only quotes above a thousand, which here means only the later years. The
  registered bound is that **no single date** exceeds ``0.5``. Any parse error is
  on a log scale and clears that easily; two readings of the same market do not.

The tail between the two bounds is **reported and not judged**. Two different
objects genuinely diverge on volatile days, and a criterion on the maximum would
be measuring Argentine volatility rather than this repository's parsers.

And the by-product
------------------

Ámbito serves intraday snapshots; A 3500 is one number per day, struck by survey.
On the dates where Ámbito carries several rows, **which snapshot is closest to
the central bank's** is readable, and that is the first outside evidence about
§3.5's median rule. **Diagnostic, not a gate**: whichever rule wins, the
registered rule stays the median for this stage, because changing it here would
be choosing a rule after seeing which one agreed (§4.4a).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from monetary_topology.parallel_rates import (
    ALL_AMBITO,
    PRE_WINDOW,
    WINDOW_END,
    WINDOW_START,
    chunk_files,
    collapse_to_daily,
    in_window,
    load_bcra_reference,
    mid_of,
    parse_argentinadatos_rows,
    parse_bcra_rows,
    parse_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results" / "b5_zero_calibration.json"

CASA = "mayorista"

#: ``b5_orphan_prereg.md`` §7, and **derived from what the arm must catch, not
#: from what the data does.** A factor-of-ten parse error is ``2·log(10) = 4.6``.
SYSTEMATIC_BOUND = 0.02
PARTIAL_BOUND = 0.5

#: The size of the smallest parse error the bounds are set against, kept beside
#: them so the derivation is legible without going to the document.
SMALLEST_PARSE_ERROR = 2.0 * math.log(10.0)


def ambito_rows(raw_dir: Path, key: str) -> list[dict]:
    """Every retrieved row for one Ámbito series, **uncollapsed**, in date order.

    Uncollapsed on purpose: B5-3b needs the snapshots. The loader in
    ``parallel_rates`` collapses on the way out, which is right for anything
    consuming a daily panel and wrong here.
    """
    _, fields = ALL_AMBITO[key]
    rows: list[dict] = []
    for path in chunk_files(raw_dir, key):
        rows.extend(parse_rows(json.loads(path.read_text(encoding="utf-8")), fields))
    rows.sort(key=lambda r: r["date"])
    return rows


def by_date(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in rows:
        out.setdefault(row["date"], []).append(row)
    return out


def index_part(mid_a: float, mid_b: float) -> float:
    """``S - S'`` between two readings: ``2 log(mid_b / mid_a)``.

    The same closed form the headline uses, so a sign or a factor-of-two error
    surfaces here rather than only there.
    """
    return 2.0 * (math.log(mid_b) - math.log(mid_a))


def quantile(values: list[float], fraction: float) -> float:
    if not values:
        return float("nan")
    return sorted(values)[int(fraction * (len(values) - 1))]


def b5_4_formats_differ(raw_dir: Path) -> dict:
    """**B5-4.** The two arms are not one file read twice.

    Two checks, and the second carries the content: **each parser must refuse the
    other's payload.** That is what proves the two collection paths exercise
    different code, which is the premise of §4.4. A pair that passed the byte
    test and failed this one would be two formats read by one lenient reader,
    and the arm would be testing that reader against itself.
    """
    ambito_bytes = b"".join(p.read_bytes() for p in chunk_files(raw_dir, CASA))
    bcra_paths = sorted(raw_dir.glob("bcra_ref_*.json"))
    bcra_bytes = b"".join(p.read_bytes() for p in bcra_paths)

    def squeeze(data: bytes) -> bytes:
        return b"".join(data.split())

    identical = squeeze(ambito_bytes) == squeeze(bcra_bytes)

    sample_ambito = json.loads(
        chunk_files(raw_dir, CASA)[0].read_text(encoding="utf-8")
    )
    sample_bcra = json.loads(bcra_paths[0].read_text(encoding="utf-8"))

    def refuses(parser, *args) -> bool:
        try:
            parser(*args)
        except Exception:  # noqa: BLE001 - any refusal counts; none does not
            return True
        return False

    return {
        "payloads_byte_identical": identical,
        "ambito_parser_refuses_bcra_payload": refuses(
            parse_rows, sample_bcra, ALL_AMBITO[CASA][1]
        ),
        "bcra_parser_refuses_ambito_payload": refuses(parse_bcra_rows, sample_ambito),
        "argentinadatos_parser_refuses_ambito_payload": refuses(
            parse_argentinadatos_rows, sample_ambito, CASA
        ),
        "passed": (
            not identical
            and refuses(parse_rows, sample_bcra, ALL_AMBITO[CASA][1])
            and refuses(parse_bcra_rows, sample_ambito)
        ),
    }


def b5_3_bounded(pairs: list[tuple[str, float, float]]) -> dict:
    """**B5-3.** Two parsers on one market, within bounds set by what they catch."""
    devs = [abs(index_part(a, b)) for _, a, b in pairs]
    over_partial = [
        {"date": d, "ambito": round(a, 4), "bcra": round(b, 4),
         "index_part": round(abs(index_part(a, b)), 6)}
        for d, a, b in pairs
        if abs(index_part(a, b)) > PARTIAL_BOUND
    ]
    median = quantile(devs, 0.5)
    return {
        "dates_compared": len(pairs),
        "median": round(median, 8),
        "p90": round(quantile(devs, 0.9), 8),
        "max": round(max(devs), 8) if devs else float("nan"),
        "systematic_bound": SYSTEMATIC_BOUND,
        "partial_bound": PARTIAL_BOUND,
        "smallest_parse_error_it_must_catch": round(SMALLEST_PARSE_ERROR, 4),
        "dates_over_partial_bound": len(over_partial),
        "worst_dates": over_partial[:20],
        # Reported and not judged: two different objects diverge on volatile
        # days, and a criterion on the maximum would measure Argentine
        # volatility rather than this repository's parsers.
        "dates_over_systematic_bound": sum(d > SYSTEMATIC_BOUND for d in devs),
        "passed": bool(pairs) and median <= SYSTEMATIC_BOUND and not over_partial,
    }


def b5_3b_collapse(multi: list[tuple[str, list[dict], float]], fields) -> dict:
    """**B5-3b.** Which snapshot sits closest to the central bank's fix.

    A **relative** comparison rather than a tolerance, because A 3500 and the
    interbank market are different objects and no tolerance between them would
    mean anything. Closest wins; ties count for both.

    Diagnostic. The registered rule does not move on this evidence (§4.4a).
    """
    wins = {"median": 0, "first": 0, "last": 0}
    for _, rows, target in multi:
        ordered = sorted(rows, key=lambda r: mid_of(r, fields))
        candidates = {
            "median": ordered[(len(ordered) - 1) // 2],
            "first": rows[0],
            "last": rows[-1],
        }
        gaps = {
            rule: abs(index_part(mid_of(row, fields), target))
            for rule, row in candidates.items()
        }
        best = min(gaps.values())
        for rule, gap in gaps.items():
            if math.isclose(gap, best, rel_tol=0.0, abs_tol=1e-12):
                wins[rule] += 1
    total = len(multi)
    shares = {k: (v / total if total else float("nan")) for k, v in wins.items()}
    ranked = sorted(shares, key=lambda k: shares[k], reverse=True)
    return {
        "dates_with_multiple_ambito_rows": total,
        "closest_counts": wins,
        "shares": {k: round(v, 4) for k, v in shares.items()},
        "winner": ranked[0] if total else None,
        "registered_rule": "median",
        "registered_rule_wins": bool(total) and ranked[0] == "median",
        "note": (
            "Diagnostic. The registered collapse rule stays the median for this "
            "stage whatever this shows; changing it here would be choosing a "
            "rule after seeing which one agreed (prereg 4.4a). Ties count for "
            "every rule that achieves the minimum, so the shares may sum above "
            "one."
        ),
    }


def main() -> int:
    fields = ALL_AMBITO[CASA][1]
    rows = ambito_rows(RAW, CASA)
    ref = load_bcra_reference(RAW)

    grouped = by_date(rows)
    shared = in_window(
        sorted(set(grouped) & set(ref)), (WINDOW_START, WINDOW_END)
    )
    collapsed = {r["date"]: r for r in collapse_to_daily(rows, fields)}

    pairs = [(d, mid_of(collapsed[d], fields), ref[d]) for d in shared]
    multi = [(d, grouped[d], ref[d]) for d in shared if len(grouped[d]) > 1]

    b5_4 = b5_4_formats_differ(RAW)
    b5_3 = b5_3_bounded(pairs)
    b5_3b = b5_3b_collapse(multi, fields)

    record = {
        "stage": "B5-calibration",
        "arm": "bounded agreement, Ambito mayorista against BCRA A 3500",
        "registered_in": "docs/b5_orphan_prereg.md 4.4, 4.4a, 4.5",
        "instrument_not_agent_class": True,
        "withdrawn_arm": {
            "was": "Ambito mayorista against argentinadatos mayorista",
            "why": (
                "argentinadatos' mayorista freezes: longest unchanged sell "
                "quote 71 days, and it sits at 365.45 through the 13 December "
                "2023 devaluation while Ambito and BCRA both move to about 800. "
                "The premise that the two are one number is false. Its tarjeta "
                "series does not have the fault and is kept for prereg 5.2."
            ),
        },
        "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
        "coverage": {
            "ambito_rows": len(rows),
            "ambito_dates": len(collapsed),
            "bcra_dates": len(ref),
            "shared_dates_in_window": len(shared),
            "multi_row_dates": len(multi),
            "pre_window_shared": len(in_window(shared, PRE_WINDOW)),
        },
        "B5-4": b5_4,
        "B5-3": b5_3,
        "B5-3b": b5_3b,
        "criteria": [
            {
                "name": "B5-4 two formats, each parser refuses the other",
                "passed": b5_4["passed"],
                "detail": (
                    f"byte-identical {b5_4['payloads_byte_identical']}, "
                    f"cross-refusals "
                    f"{b5_4['ambito_parser_refuses_bcra_payload']}/"
                    f"{b5_4['bcra_parser_refuses_ambito_payload']}"
                ),
            },
            {
                "name": "B5-3 two parsers agree within the derived bounds",
                "passed": b5_3["passed"],
                "detail": (
                    f"median {b5_3['median']:.3e} against {SYSTEMATIC_BOUND}, "
                    f"{b5_3['dates_over_partial_bound']} dates over "
                    f"{PARTIAL_BOUND}, on {b5_3['dates_compared']:,} dates"
                ),
            },
        ],
        "verdicts": {"B5-4": b5_4["passed"], "B5-3": b5_3["passed"]},
        "diagnostics": ["B5-3b"],
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("B5 calibration: the wholesale market read by two parsers\n")
    print(f"  Ambito  {len(rows):,} rows over {len(collapsed):,} dates")
    print(f"  BCRA    {len(ref):,} dates")
    print(f"  shared, in window: {len(shared):,} "
          f"({len(multi):,} carry several Ambito snapshots)\n")

    mark = "pass" if b5_4["passed"] else "FAIL"
    print(f"  B5-4  two formats, each parser refuses the other      {mark}")
    print(f"          byte-identical {b5_4['payloads_byte_identical']}; "
          f"cross-refusals "
          f"{b5_4['ambito_parser_refuses_bcra_payload']}/"
          f"{b5_4['bcra_parser_refuses_ambito_payload']}")

    mark = "pass" if b5_3["passed"] else "FAIL"
    print(f"  B5-3  agreement within the derived bounds             {mark}")
    print(f"          median {b5_3['median']:.3e} against {SYSTEMATIC_BOUND}, "
          f"p90 {b5_3['p90']:.3e}, max {b5_3['max']:.3e}")
    print(f"          {b5_3['dates_over_partial_bound']} dates over the partial "
          f"bound {PARTIAL_BOUND}; smallest parse error it must catch is "
          f"{SMALLEST_PARSE_ERROR:.2f}")
    for w in b5_3["worst_dates"][:5]:
        print(f"            {w['date']}  ambito {w['ambito']}  "
              f"bcra {w['bcra']}  z={w['index_part']:.3e}")

    print("\n  B5-3b which snapshot is closest to the central bank    diagnostic")
    print(f"          on {b5_3b['dates_with_multiple_ambito_rows']:,} multi-row "
          "dates: " + ", ".join(f"{k} {v:.1%}"
                                for k, v in b5_3b["shares"].items()))
    print(f"          closest most often: {b5_3b['winner']}; "
          f"registered rule is {b5_3b['registered_rule']} and does not move")

    print(f"\n  wrote {RESULTS.relative_to(ROOT)}")
    return 0 if (b5_4["passed"] and b5_3["passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
