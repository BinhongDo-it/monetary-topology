"""Retrieve the full text of named Federal Register documents.

The census in experiments/b30_23_sro_census.py names the population and the seams
off titles alone. The criterion it serves counts distinct class values in a filed
fee schedule, and no title carries that, so the schedules themselves have to be
read. Two title-level proxies were tried against the seams and both failed, which
is why this step exists rather than a cleverer screen.

This retrieves one document per call argument, by the document number the census
already has, and writes it under data/raw/fr_text/. It is deliberately one document
at a time: before fifty are pulled, one is pulled and looked at, because whether a
fee schedule can be counted at all out of this text is the question that decides
whether the rest is worth retrieving.

RESUME AND INTEGRITY. A document already on disk is skipped only if it ends with the
Federal Register's own end marker, so a truncated download is refetched rather than
read. Nothing is overwritten in place: the write goes to a .partial and is renamed.

    python data/fetch_fr_fulltext.py 2019-04285
    python data/fetch_fr_fulltext.py 2019-04285 2018-16420
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "raw", "fr_sec")
OUT = os.path.join(HERE, "raw", "fr_text")
END = "[FR Doc."          # every Federal Register document closes with this


def index():
    """document number -> publication date, from the index already on disk."""
    m = {}
    for name in sorted(os.listdir(INDEX)):
        if not name.endswith(".jsonl"):
            continue
        with open(os.path.join(INDEX, name), encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 0 or not line.strip():
                    continue
                r = json.loads(line)
                m[r["document_number"]] = (r["publication_date"], r["title"])
    return m


def complete(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            body = f.read()
    except OSError:
        return False
    return len(body) > 500 and END in body[-4000:]


def fetch(doc, date):
    y, m, d = date.split("-")
    url = (f"https://www.federalregister.gov/documents/full_text/text/"
           f"{y}/{m}/{d}/{doc}.txt")
    req = urllib.request.Request(
        url, headers={"User-Agent": "tariff-structure-research/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace"), url


def main(docs):
    os.makedirs(OUT, exist_ok=True)
    idx = index()
    for doc in docs:
        if doc not in idx:
            print(f"{doc}: not in the index on disk. Fetch the index first.")
            continue
        date, title = idx[doc]
        path = os.path.join(OUT, f"{doc}.txt")
        if complete(path):
            print(f"{doc}  {date}  already on disk, "
                  f"{os.path.getsize(path)} bytes")
            continue
        body, url = fetch(doc, date)
        if END not in body[-4000:]:
            print(f"{doc}: retrieved {len(body)} bytes with no end marker. "
                  "Not written. The source may have paginated this document.")
            continue
        tmp = path + ".partial"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        os.replace(tmp, path)
        print(f"{doc}  {date}  {len(body):8d} bytes   {title[:70]}")
        time.sleep(0.5)
    print(f"\nunder data/raw/{os.path.basename(OUT)}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("give one or more Federal Register document numbers")
    main(sys.argv[1:])
