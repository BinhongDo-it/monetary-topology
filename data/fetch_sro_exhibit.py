"""Retrieve the rule-text exhibit of a filing, given its Federal Register number.

The criterion counts distinct class values in a filed fee schedule. The Federal
Register carries the notice, not the schedule: the notice states the amendments and
says the schedule is elsewhere. The schedule travels as Exhibit 5, which the
Commission serves at a regular path built from two things the notice itself prints:

    [Release No. 34-85248; File No. SR-NYSECHX-2019-01]

giving  files/rules/sro/{exchange}/{year}/{release}-ex5.pdf

so one document number is enough to reach the exhibit, in two requests, with nothing
to search. Where a filing has several exhibits they are suffixed a through f and each
is tried.

A DECLARED AGENT STRING IS REQUIRED. Without one the Commission answers with a
~1.9 KB page reading "Request Rate Threshold Exceeded", which saves happily under a
.pdf name and is not a PDF. Size and magic bytes are both checked, so that page is
never mistaken for a document.

RESUME. A file already on disk that begins %PDF is skipped. Writes go through a
.partial and are renamed, so an interrupted download is never read as complete.

    python data/fetch_sro_exhibit.py 2019-25107
    python data/fetch_sro_exhibit.py 2019-25107 2019-04285
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "raw", "fr_sec")
OUT = os.path.join(HERE, "raw", "fr_text")
# The Commission requires a declared agent string carrying a real contact,
# and a contact address does not belong in a public file. It is read from the
# environment, and its absence is an error rather than a silent fallback: without
# it every request is refused, and a refusal that goes unprinted looks exactly
# like an exhibit that does not exist.
UA = os.environ.get("SEC_USER_AGENT", "")
RELEASE = re.compile(r"\[Release No\.\s*(34-\d+)\s*;\s*File No\.\s*(SR-([A-Za-z]+)-(\d{4})-\d+)")
SUFFIXES = ["", "a", "b", "c", "d", "e", "f"]
MINSIZE = 5000


def index():
    m = {}
    for name in sorted(os.listdir(INDEX)):
        if name.endswith(".jsonl"):
            with open(os.path.join(INDEX, name), encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i and line.strip():
                        r = json.loads(line)
                        m[r["document_number"]] = (r["publication_date"], r["title"])
    return m


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read()
    return body if binary else body.decode("utf-8", "replace")


def main(docs):
    if not UA:
        sys.exit("Set SEC_USER_AGENT to a project name plus a contact address "
                 "before running this.\nThe Commission refuses requests without "
                 "one, and that refusal is indistinguishable from a missing "
                 "exhibit.")
    os.makedirs(OUT, exist_ok=True)
    idx = index()
    for doc in docs:
        if doc not in idx:
            print(f"{doc}: not in the index on disk")
            continue
        date, title = idx[doc]
        y, m, d = date.split("-")
        text = get(f"https://www.federalregister.gov/documents/full_text/text/"
                   f"{y}/{m}/{d}/{doc}.txt")
        with open(os.path.join(OUT, f"{doc}.txt"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(text)
        hit = RELEASE.search(text)
        if not hit:
            print(f"{doc}: no release number in the text. Not an SRO notice?")
            continue
        release, fileno, exch, year = hit.group(1), hit.group(2), hit.group(3), hit.group(4)
        print(f"{doc}  {date}  {fileno}  release {release}")
        got = 0
        for sfx in SUFFIXES:
            name = f"{release}-ex5{sfx}.pdf"
            path = os.path.join(OUT, name)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    if f.read(4) == b"%PDF":
                        print(f"    {name:26s} already on disk")
                        got += 1
                        continue
            url = (f"https://www.sec.gov/files/rules/sro/{exch.lower()}/{year}/{name}")
            try:
                body = get(url, binary=True)
            except urllib.error.HTTPError as e:
                # printed, never swallowed: 403 means the agent string was refused
                # and 404 means this suffix does not exist, and those call for
                # opposite next steps
                if e.code != 404:
                    print(f"    {name:26s} HTTP {e.code}")
                elif sfx == "":
                    print(f"    {name:26s} HTTP 404")
                continue
            finally:
                time.sleep(0.4)
            if len(body) < MINSIZE or not body.startswith(b"%PDF"):
                # the rate-limit page saves under a .pdf name and is not one
                if sfx == "":
                    print(f"    {name:26s} {len(body)} bytes, not a PDF")
                continue
            tmp = path + ".partial"
            with open(tmp, "wb") as f:
                f.write(body)
            os.replace(tmp, path)
            print(f"    {name:26s} {len(body):9d} bytes")
            got += 1
        if not got:
            print("    no exhibit found under any suffix")
    print(f"\nunder data/raw/{os.path.basename(OUT)}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("give one or more Federal Register document numbers")
    main(sys.argv[1:])
