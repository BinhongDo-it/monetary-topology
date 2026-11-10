"""B99: look up the RxNorm concept (RXCUI) of every NDC-11 in the 605 repackaging pairs.

The CMS Formulary Reference File keys drugs by RXCUI and, in the CY 2026 release, carries no
NDC column, so it cannot say which RXCUI an NDC sits under. The National Library of Medicine's
RxNav REST service (free, no key) answers that per NDC: getNDCStatus returns the NDC's status
and the RXCUI it maps to (for an obsolete or alien NDC, the RXCUI in its history, if any).

Cache: one JSON line per NDC in OUT_JSONL, written as soon as the answer arrives; a rerun skips
NDCs already in the cache, so an interrupted run resumes. A non-200 reply or a body that is not
JSON stops the run without writing a line for that NDC.

usage: python -I fetch_b99_rxnav_ndc.py NADAC_GROUP_CHECK_JSON OUT_JSONL
"""
import json
import os
import sys
import time
import urllib.request

API = "https://rxnav.nlm.nih.gov/REST/ndcstatus.json?ndc="
UA = {"User-Agent": "Mozilla/5.0 (research fetch; B99)"}
PAUSE = 0.06      # stays under the published 20 requests per second


def main(argv) -> int:
    src, out = argv
    pairs = json.load(open(src, encoding="utf-8"))["pairs"]
    ndcs = sorted({row[0] for p in pairs for row in p["rows_repack"] + p["rows_source"]})
    done = set()
    if os.path.exists(out):
        with open(out, encoding="utf-8") as fh:
            done = {json.loads(line)["ndc"] for line in fh if line.strip()}
    todo = [n for n in ndcs if n not in done]
    print(f"{len(ndcs)} NDCs, {len(done)} cached, {len(todo)} to fetch", flush=True)
    with open(out, "a", encoding="utf-8", newline="\n") as fh:
        for i, ndc in enumerate(todo):
            req = urllib.request.Request(API + ndc, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status != 200:
                    raise SystemExit(f"{ndc}: HTTP {r.status}")
                body = json.loads(r.read().decode("utf-8"))
            fh.write(json.dumps({"ndc": ndc, "reply": body}, sort_keys=True) + "\n")
            fh.flush()
            if i % 200 == 0:
                print(i, ndc, flush=True)
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
