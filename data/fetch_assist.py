# -*- coding: utf-8 -*-
"""C2. California's course articulation agreements, from ASSIST's public API.

**Why this carrier.** An articulation agreement is an administrative ruling that
a course at one college satisfies a course requirement at another. No money is
involved, nothing is traded, and there is no market to be frictional. If the
declared equivalences do not compose, friction is not available as an
explanation.

**What composition means here, and what it does not.** The unit counts do not
carry the test. Units are a scalar attached to a course, so any ratio built from
them telescopes around a loop and closes at 1 by construction; an arm built on
unit arithmetic would return its answer from its own setup. The test is on the
**relation**. If a scalar course value existed, then "articulates to the same
receiving course" would be an equivalence relation on sending courses, and the
sending-to-receiving graph would be a disjoint union of complete bipartite
blocks. An open square, meaning `a` and `b` both articulate to `p`, `b`
articulates to `q`, and `a` does not, is a witness against that, and it is a
combinatorial object with no number in it.

**The API needs an anti-forgery token, and that is why a bare request fails.**
Every one of these paths answers `400 {"title":"Bad Request","code":400}` to a
request that does not carry one, whatever its user agent, and the body is
ASP.NET Core's problem document rather than a gateway's, so the refusal comes
from the application. The site sets an `XSRF-TOKEN` cookie when the front page
is fetched and its client echoes that value back in an `X-XSRF-TOKEN` header on
every call. `handshake` below does the same: one GET of the front page into a
cookie jar, then the token is read from the jar and set as a header for the rest
of the run. Measured 2026-08-27 by watching what the site's own client sends.
Nothing here is a credential: the token is issued to anyone who asks and it is
re-minted on every run.

**Endpoints.** Year ids are the calendar year minus 1950.

    /api/institutions
        every school; `isCommunityCollege` splits senders from receivers.
    /api/institutions/{id}/agreements?asSendingOnly=true
        which schools this one has agreements with, and for which years. The
        parameter is what the site's own client sends and it is kept for that
        reason rather than because its effect has been measured here.
    /api/articulation/Agreements?Key={year}/{from}/to/{to}/AllMajors
        the agreements themselves, one call per ordered pair, all majors.
    /api/transferability/courses?institutionId={id}&academicYearId={y}&listType=IGETC
        which transfer areas a course counts for, per sending institution.

**The payload is doubly encoded.** The response is JSON whose `result` holds
`articulations`, `templateAssets`, `receivingInstitution` and
`sendingInstitution` as JSON *strings*, so each needs a second parse. A course
inside carries `courseIdentifierParentId`, a system-wide identifier, so courses
match on an id rather than on a title, and no fuzzy name matching enters this
stage anywhere.

**Three modes, in order, and the order is the point.** `--probe` takes one pair,
reports what came back, and keeps that one payload on disk: if the shape is not
what the parser above expects, the parser is wrong, nothing should be pulled,
and the raw document is there to correct it against.
`--pilot` takes a small grid and reports how many receiving courses have two or
more distinct sending colleges, which is the smallest structure a square needs.
**That count, not the average number of articulations per pair, is what decides
whether the full sweep is worth its cost**, and it is measured before the sweep
is paid for. `--pull` runs the sweep.

Resumable and truncation-aware: bytes land in `<name>.part`, a file is renamed
only after it parses as JSON and reports `isSuccessful`, and a complete file is
never refetched.

**Neither sandbox in this project can reach assist.org**, so `--probe` has to be
run on a machine with open egress before the parser here can be trusted.

Usage::

    python data/fetch_assist.py --probe
    python data/fetch_assist.py --pilot
    python data/fetch_assist.py --pull
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

BASE = "https://assist.org/api"
YEAR_BASE = 1950
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "assist"

#: Default catalogue year. `--year` overrides. 2024 is the last cycle certain to
#: be complete for every institution at the time this was written; a year whose
#: agreements are still being posted would undercount the graph for the
#: institutions that have not posted yet, which is a coverage artefact and not a
#: finding.
YEAR = 2024

#: Politeness. This is a public service run for students.
DELAY = 0.5

#: A browser user agent. The API answered a bare `urllib` request in 2021 and
#: returns 400 to one now, so something in front of it inspects the request.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

#: What the site's own client sends. `X-XSRF-TOKEN` is added by `handshake`.
HEADERS = {"Accept": "application/json, text/plain, */*", "User-Agent": UA}

#: Set by `handshake`. Every mode calls it first, so nothing reads this while
#: it is still None except code that has skipped the handshake, which is a bug
#: rather than a state to tolerate.
OPENER: urllib.request.OpenerDirector | None = None


def handshake(timeout: int = 30) -> str:
    """Fetch the front page into a cookie jar and find the token the API takes.

    The front page sets **two** cookies whose names differ by three characters
    and whose values differ entirely: `XSRF-TOKEN` and `X-XSRF-TOKEN`. That is
    ASP.NET Core's antiforgery pair, one half stored for validation and the
    other meant to be echoed in a header, and sending the wrong half returns the
    same `400 {"title":"Bad Request","code":400}` as sending nothing at all. The
    two are therefore indistinguishable by their failure, which is why this
    tries each and keeps whichever one a real call accepts rather than choosing
    on a reading of the names.

    Returns the cookie name that worked, never its value. The value is minted
    per run, is not a credential, and has no reason to be printed or stored.
    """
    global OPENER
    import urllib.error

    jar = http.cookiejar.CookieJar()
    OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    base = list(HEADERS.items())
    OPENER.addheaders = base
    OPENER.open("https://assist.org/", timeout=timeout).read()

    found = {c.name: c.value for c in jar if c.value}
    if not found:
        raise SystemExit("the front page set no cookies at all, so the session "
                         "mechanism has moved. Stop here.")

    # Verified against a real endpoint, cheaply. A handshake that reports
    # success without having made a call is the failure this whole sequence
    # already produced once.
    for name in ("X-XSRF-TOKEN", "XSRF-TOKEN"):
        raw = found.get(name)
        if not raw:
            continue
        OPENER.addheaders = base + [("X-XSRF-TOKEN", urllib.parse.unquote(raw))]
        try:
            OPENER.open(f"{BASE}/AcademicYears", timeout=timeout).read()
            return name
        except urllib.error.HTTPError:
            continue

    OPENER = None
    raise SystemExit(
        "neither %s was accepted as the header token. The cookies arrived, so "
        "the refusal is about which value is echoed rather than about the "
        "session. Watch what the site's own client sends before changing "
        "anything here: this file has already guessed wrong three times, and "
        "each guess cost a round trip."
        % " nor ".join(sorted(found)))


def get(url: str, timeout: int = 60) -> bytes:
    if OPENER is None:
        raise SystemExit("handshake() has not run, so no anti-forgery token is "
                         "attached and every call would return 400.")
    with OPENER.open(url, timeout=timeout) as fh:
        return fh.read()


def get_json(url: str):
    return json.loads(get(url).decode("utf-8"))


def inner(result: dict, field: str):
    """Second parse. The API nests JSON documents as strings inside `result`."""
    raw = result.get(field)
    if raw is None:
        return None
    return json.loads(raw) if isinstance(raw, str) else raw


def institutions() -> list[dict]:
    return get_json(f"{BASE}/institutions")


def agreements_of(school_id: int) -> list[dict]:
    return get_json(f"{BASE}/institutions/{school_id}/agreements?asSendingOnly=true")


def name_of(school: dict) -> str:
    names = school.get("names") or []
    return names[-1]["name"] if names else str(school.get("id"))


def agreements_url(year: int, sending: int, receiving: int) -> str:
    key = f"{year - YEAR_BASE}/{sending}/to/{receiving}/AllMajors"
    return f"{BASE}/articulation/Agreements?Key={key}"


def courses_in(articulations: list) -> dict:
    """Summarise one pair's payload: what it declares, and what it denies.

    Field names measured from a real payload on 2026-08-27, because the only
    published description of this API uses `pickOneGroup` and `fromClasses` and
    the service now nests `items` inside `items`. Reading it against that
    description returns zero edges while every transport check passes, which is
    the failure this function was written twice to avoid.

    Receiving side, keyed by `articulation.type`:

        Course           `articulation.course.courseIdentifierParentId`
        Series           `articulation.series.courses[]`, plus a conjunction
        Requirement      a requirement, carrying no course identifier
        Transferability  carries none either

    Sending side: `sendingArticulation.items[]` are course groups and their
    `items[]` are the courses, each with `courseIdentifierParentId`.

    **`noArticulationReason` has two values and they are not the same fact.**
    "No Course Articulated" says this college has nothing that satisfies the
    requirement. "This course must be taken at the university after transfer"
    says no college can, because the receiving institution reserves it. The
    first is a denial about one sender and is admissible as the absent side of
    an open square; the second is a property of the receiving course and would
    turn a system-wide exclusion into false evidence of an inconsistency. They
    are counted separately here so that no later stage has to guess which it
    has.
    """
    recv, send, edges = set(), set(), 0
    denied = held = other = 0
    for row in articulations:
        art = (row or {}).get("articulation") or {}
        kind = art.get("type")

        rid = None
        if kind == "Course":
            course = art.get("course")
            if isinstance(course, dict):
                rid = course.get("courseIdentifierParentId")
        elif kind == "Series":
            series = art.get("series")
            if isinstance(series, dict):
                ids = tuple(c.get("courseIdentifierParentId")
                            for c in series.get("courses") or []
                            if isinstance(c, dict))
                rid = ("series",) + ids if ids else None

        sa = art.get("sendingArticulation") or {}
        reason = sa.get("noArticulationReason")
        if reason == "No Course Articulated":
            denied += 1
        elif reason:
            held += 1
        elif reason is not None:
            other += 1

        if rid is None:
            continue
        recv.add(rid)
        for group in sa.get("items") or []:
            for course in (group or {}).get("items") or []:
                if not isinstance(course, dict):
                    continue
                cid = course.get("courseIdentifierParentId")
                if cid:
                    send.add(cid)
                    edges += 1
    return {"receiving": len(recv), "sending": len(send), "edges": edges,
            "denied_here": denied, "held_by_receiver": held, "other_reason": other}


def pull_pair(year: int, sending: int, receiving: int, force: bool = False) -> tuple[Path, str]:
    dest = OUT / f"{year}" / f"{sending}_to_{receiving}.json"
    if dest.exists() and not force:
        return dest, "have"
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob = get(agreements_url(year, sending, receiving))
    try:
        doc = json.loads(blob.decode("utf-8"))
    except json.JSONDecodeError as exc:
        part = dest.with_suffix(".json.part")
        part.write_bytes(blob)
        return part, "NOT JSON, left as .part (%s)" % exc
    if not doc.get("isSuccessful"):
        return dest, "declined by the API, nothing written"
    dest.write_bytes(blob)
    return dest, "ok %d B" % len(blob)


def probe(year: int) -> int:
    print("handshake         %s cookie taken from the front page"
          % handshake())
    schools = institutions()
    ccs = [s for s in schools if s.get("isCommunityCollege")]
    uni = [s for s in schools if not s.get("isCommunityCollege")]
    print("institutions      %d total, %d community colleges, %d receiving"
          % (len(schools), len(ccs), len(uni)))
    print("one school record %s" % sorted(schools[0].keys()))
    print("sample sender     %d %s" % (ccs[0]["id"], name_of(ccs[0])))
    print("sample receiver   %d %s" % (uni[0]["id"], name_of(uni[0])))

    url = agreements_url(year, ccs[0]["id"], uni[0]["id"])
    print("\nGET %s" % url)
    blob = get(url)
    doc = json.loads(blob.decode("utf-8"))
    print("bytes             %d" % len(blob))
    print("top level         %s" % sorted(doc.keys()))
    print("isSuccessful      %s" % doc.get("isSuccessful"))
    result = doc.get("result") or {}
    print("result keys       %s" % sorted(result.keys()))
    for field in ("articulations", "templateAssets"):
        val = result.get(field)
        print("%-17s %s, %d chars"
              % (field, type(val).__name__, len(val) if isinstance(val, str) else -1))
    arts = inner(result, "articulations") or []
    print("articulations     %d rows after the second parse" % len(arts))
    if arts:
        print("one row's keys    %s" % sorted((arts[0] or {}).keys()))
        art = (arts[0] or {}).get("articulation") or {}
        print("articulation keys %s" % sorted(art.keys()))
    assets = inner(result, "templateAssets") or []
    print("templateAssets    %d entries after the second parse" % len(assets))
    if assets:
        print("one asset's keys  %s" % sorted((assets[0] or {}).keys()))

    counts = courses_in(arts)
    print("parsed            %d receiving, %d sending, %d edges"
          % (counts["receiving"], counts["sending"], counts["edges"]))
    print("denials           %d no course at this college, %d reserved by the "
          "receiver" % (counts["denied_here"], counts["held_by_receiver"]))

    # The one file --probe writes. The receiving course is not a field on
    # `articulation` in any published description of this API, so it is most
    # likely reached by joining `templateCellId` against the cells inside
    # `templateAssets`. `courses_in` above guesses otherwise and is expected to
    # be wrong. Keeping the raw payload means the parser can be corrected
    # against the real document instead of against a description of it, which
    # is the whole reason this mode exists.
    OUT.mkdir(parents=True, exist_ok=True)
    keep = OUT / ("_probe_%d_%d_to_%d.json" % (year, ccs[0]["id"], uni[0]["id"]))
    keep.write_bytes(blob)
    print("\nwrote %s  (%d B)" % (keep, len(blob)))

    if not counts["edges"]:
        print("\nZero edges parsed, which is the expected outcome and not a "
              "transport problem: the payload above arrived intact. Correct "
              "`courses_in` against the file just written, then run --probe "
              "again. Nothing else should be pulled until it reports edges: a "
              "sweep on a wrong parse is how a partial graph gets mistaken for "
              "a complete one.")
        return 1
    return 0


def pilot(year: int, k: int) -> int:
    print("handshake         %s cookie taken from the front page"
          % handshake())
    schools = institutions()
    ccs = [s for s in schools if s.get("isCommunityCollege")][:k]
    uni = [s for s in schools if not s.get("isCommunityCollege")][:k]
    by_receiving = defaultdict(set)
    total_bytes = pairs = 0
    for cc in ccs:
        for u in uni:
            dest, status = pull_pair(year, cc["id"], u["id"])
            pairs += 1
            if dest.exists() and dest.suffix == ".json":
                total_bytes += dest.stat().st_size
                doc = json.loads(dest.read_text(encoding="utf-8"))
                arts = inner(doc.get("result") or {}, "articulations") or []
                for row in arts:
                    art = (row or {}).get("articulation") or {}
                    if art.get("type") != "Course":
                        continue
                    course = art.get("course")
                    rid = course.get("courseIdentifierParentId") if isinstance(course, dict) else None
                    sa = art.get("sendingArticulation") or {}
                    has_edge = any((g or {}).get("items") for g in sa.get("items") or [])
                    if rid is not None and has_edge:
                        by_receiving[(u["id"], rid)].add(cc["id"])
            print("  %-28s -> %-28s %s"
                  % (name_of(cc)[:28], name_of(u)[:28], status), flush=True)
            time.sleep(DELAY)

    testable = sum(1 for v in by_receiving.values() if len(v) >= 2)
    n_cc = len([s for s in schools if s.get("isCommunityCollege")])
    n_uni = len([s for s in schools if not s.get("isCommunityCollege")])
    full = n_cc * n_uni
    print("\n--- gate five: measured before the sweep is paid for ---")
    print("pairs pulled            %d of %d in the full grid" % (pairs, full))
    print("bytes                   %.2f MB, mean %.1f kB per pair"
          % (total_bytes / 1e6, total_bytes / max(1, pairs) / 1e3))
    print("projected full sweep    %.2f GB, %.0f min at %.1fs politeness"
          % (total_bytes / max(1, pairs) * full / 1e9, full * DELAY / 60, DELAY))
    print("receiving courses seen  %d" % len(by_receiving))
    print("with 2+ sending colleges %d   <- squares are only testable here"
          % testable)
    print("\nThe second number is the one that decides the sweep. The mean "
          "articulations per pair does not: a pair can be dense and still "
          "contribute no square if every receiving course it touches is "
          "reached by one college only.")
    return 0


def sweep(year: int) -> int:
    print("handshake         %s cookie taken from the front page"
          % handshake())
    schools = institutions()
    ccs = [s for s in schools if s.get("isCommunityCollege")]
    uni = [s for s in schools if not s.get("isCommunityCollege")]
    done = new = skipped = 0
    for cc in ccs:
        for u in uni:
            dest, status = pull_pair(year, cc["id"], u["id"])
            done += 1
            if status == "have":
                skipped += 1
                continue
            new += 1
            print("  [%4d/%4d] %-26s -> %-26s %s"
                  % (done, len(ccs) * len(uni), name_of(cc)[:26],
                     name_of(u)[:26], status), flush=True)
            time.sleep(DELAY)
    print("\n%d pairs, %d fetched now, %d already on disk" % (done, new, skipped))
    manifest = OUT / f"assist_{year}_manifest.json"
    files = sorted((OUT / str(year)).glob("*.json"))
    manifest.write_text(
        json.dumps({"year": year, "year_id": year - YEAR_BASE,
                    "endpoint": agreements_url(year, 0, 0),
                    "sending_institutions": len(ccs),
                    "receiving_institutions": len(uni),
                    "files": len(files),
                    "bytes": sum(f.stat().st_size for f in files)},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("wrote %s" % manifest)
    return 0


#: Header sets to try when the API refuses. Order matters: the first is what the
#: 2021 scraper that documented this API used, namely nothing at all, and the
#: second is what this file sent when it first returned 400, so the two together
#: say whether the `Accept` header was self-inflicted.
HEADER_SETS = (
    ("bare, no headers", {}),
    ("Accept json only", {"Accept": "application/json"}),
    ("browser UA only", {"User-Agent": UA}),
    ("browser UA + Accept", {"User-Agent": UA, "Accept": "application/json"}),
    ("browser UA + Accept + Referer",
     {"User-Agent": UA, "Accept": "application/json",
      "Referer": "https://assist.org/"}),
)

#: Path spellings seen in the wild. The first is the one the 2021 scraper used.
#: The third is the newer service whose published documentation asks for an API
#: key, and it is here to record whether the keyless path still answers.
PATHS = (
    "https://assist.org/api/institutions",
    "https://assist.org/api/Institutions",
    "https://prod.assistng.org/articulation/api/Institutions",
    "https://assist.org/api/AcademicYears",
)


def diagnose() -> int:
    """Make the refusal legible instead of guessing at it again.

    Three rounds of guessing a header produced three wrong answers, so this
    prints what is actually sent and what actually comes back rather than
    reporting a status code. The response body matters most: this API answers
    with ASP.NET Core's problem document, which often names the thing it could
    not bind. Writes nothing, and prints no token value.
    """
    import urllib.error

    def show(label, status, sent, body):
        safe = {k: ("<%d chars>" % len(v) if "TOKEN" in k.upper() else v)
                for k, v in sent.items()}
        print("  %-34s %s" % (label, status))
        print("      sent %s" % safe)
        print("      body %s" % (body[:400].replace("\n", " ") if body else "(empty)"))

    url = f"{BASE}/institutions"

    # ---- 1. urllib, opener with addheaders, which is what just failed -------
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = list(HEADERS.items())
    op.open("https://assist.org/", timeout=30).read()
    cookies = {c.name: c.value for c in jar}
    print("  cookies from the front page: %s"
          % {k: "<%d chars>" % len(v or "") for k, v in cookies.items()})
    tok = urllib.parse.unquote(cookies.get("XSRF-TOKEN") or "")
    op.addheaders = op.addheaders + [("X-XSRF-TOKEN", tok)]
    sent = dict(op.addheaders)
    try:
        body = op.open(url, timeout=30).read().decode("utf-8", "replace")
        show("urllib opener + addheaders", 200, sent, body)
    except urllib.error.HTTPError as exc:
        show("urllib opener + addheaders", exc.code, sent,
             exc.read().decode("utf-8", "replace"))

    # ---- 2. urllib, explicit Request headers, raw token, plus Referer -------
    for label, token, extra in (
            ("urllib Request, decoded token", tok, {}),
            ("urllib Request, raw cookie value", cookies.get("XSRF-TOKEN") or "", {}),
            ("urllib Request + Referer/Origin", tok,
             {"Referer": "https://assist.org/", "Origin": "https://assist.org"}),
    ):
        h = dict(HEADERS, **extra)
        h["X-XSRF-TOKEN"] = token
        h["Cookie"] = "; ".join("%s=%s" % (k, v) for k, v in cookies.items())
        req = urllib.request.Request(url, headers=h)
        try:
            body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            show(label, 200, h, body)
        except urllib.error.HTTPError as exc:
            show(label, exc.code, h, exc.read().decode("utf-8", "replace"))

    # ---- 3. requests, which preserves header case and has its own defaults --
    try:
        import requests
    except ImportError:
        print("  requests is not installed, skipping that round")
        return 1
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get("https://assist.org/", timeout=30)
    rtok = s.cookies.get("XSRF-TOKEN")
    if rtok:
        s.headers["X-XSRF-TOKEN"] = urllib.parse.unquote(rtok)
    r = s.get(url, timeout=30)
    show("requests.Session", r.status_code, dict(r.request.headers), r.text)
    if r.status_code == 200:
        try:
            doc = r.json()
            print("\n  USE requests.Session with the XSRF handshake.")
            print("  %d records, one record's keys %s"
                  % (len(doc), sorted(doc[0].keys())))
            return 0
        except Exception:                                  # noqa: BLE001
            pass

    print("\n  Nothing returned a list. The bodies above are the evidence; read "
          "what they name before changing anything here.")
    return 1


def areas(year: int) -> int:
    """Enumerate the transfer-area vocabulary before pulling anything with it.

    C2's first three arms all died on the same thing: both sides of an
    articulation carry institution-local identifiers, 972 sending ids with none
    shared between colleges and 633 receiving ids with none shared between
    universities, so "the same course" is not sayable and every proxy for it
    also encodes "these two institutions are different". Transfer areas are the
    part of this system that does have a shared vocabulary: `1A`, `3B`, `A2`,
    `C1` mean the same thing state-wide. That is what makes a course placed in
    one area by one receiving system and another area by another a reading
    about the declaration rather than about curriculum coverage.

    Which list types exist is read from the service rather than guessed, and
    the payloads are kept so the parser can be written against documents rather
    than against a description of them. Both of those are this stage repeating
    what it already paid for once.
    """
    print("handshake         verified, header token comes from the %s cookie"
          % handshake())
    OUT.mkdir(parents=True, exist_ok=True)

    raw = get(f"{BASE}/transferability/areaTypes")
    (OUT / "areaTypes.json").write_bytes(raw)
    doc = json.loads(raw.decode("utf-8"))
    print("areaTypes         %d bytes, %s"
          % (len(raw), type(doc).__name__))
    print(json.dumps(doc, indent=1, ensure_ascii=False)[:1800])
    print("wrote %s" % (OUT / "areaTypes.json"))

    types = list_types(doc)
    print("\nlist types found  %s"
          % (", ".join("%s=%s" % (n, a) for n, a in types) or "NONE"))
    if not types:
        print("\nSTOP. The list types could not be read out of that document, "
              "so the sweep has nothing to iterate over. Do not guess the "
              "tokens: a wrong one returns an error page that a sweep would "
              "record as a college with no transferable courses.")
        return 1

    schools = institutions()
    cc = [s for s in schools if s.get("isCommunityCollege")]
    sample = cc[0]
    print("\nsample college    %d %s" % (sample["id"], name_of(sample)))
    total = 0
    good: list[str] = []
    for kind, want in types:
        url = (f"{BASE}/transferability/courses?institutionId={sample['id']}"
               f"&academicYearId={year - YEAR_BASE}&listType={kind}")
        try:
            blob = get(url)
        except Exception as exc:                          # noqa: BLE001
            print("  %-14s FAILED %s" % (kind, str(exc)[:70]))
            continue
        ok, got = honoured(blob, want)
        if not ok:
            print("  %-14s %7d B  DECLINED, answered listType %s instead. Not "
                  "written." % (kind, len(blob), got))
            time.sleep(DELAY)
            continue
        total += len(blob)
        dest = OUT / ("_areas_%d_%s.json" % (sample["id"], kind))
        dest.write_bytes(blob)
        d = json.loads(blob.decode("utf-8"))
        print("  %-14s %7d B  listType %s, %d courses"
              % (kind, len(blob), got, len(d.get("courseInformationList") or [])))
        good.append(kind)
        time.sleep(DELAY)

    print("\naccepted          %s" % (", ".join(good) or "none"))
    calls = len(cc) * len(good)
    print("\n--- cost, before the sweep is paid for ---")
    print("colleges %d x accepted list types %d = %d calls, %.0f min at %.1fs"
          % (len(cc), len(good), calls, calls * DELAY / 60, DELAY))
    print("one college is %.2f MB across the accepted types, so the sweep is "
          "about %.2f GB" % (total / 1e6, total * len(cc) / 1e9))
    print("wrote %d sample payload(s) into %s" % (len(good), OUT))
    return 0


def list_types(doc) -> list[tuple[str, int]]:
    """Return (name, areaType) for each entry in the areaTypes document.

    Only the top level is read. An earlier version walked the whole document
    for any string under a plausible key and returned nine tokens, two of which
    were term codes lifted out of the `begin` and `end` blocks. Those two were
    then requested, and the service answered them, which is the point of the
    check in `honoured` below.
    """
    out = []
    for entry in doc if isinstance(doc, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            out.append((entry["name"], entry.get("areaType")))
    return out


def honoured(blob: bytes, want: int | None) -> tuple[bool, object]:
    """Did the service answer the list type that was asked for.

    **It does not refuse an unrecognised one.** Asking for `Cal-GETC`, and
    asking for the term code `F2016`, and asking for `CSUTC`, all returned the
    same 418,699 bytes reporting `listType` 0. So a wrong token yields a
    complete, well-formed, plausible document belonging to a different list,
    and a sweep that trusted its own filenames would record four copies of one
    list under four names. Every response is therefore checked against the
    `areaType` the vocabulary gave for the token, and a mismatch is not
    written.
    """
    try:
        got = json.loads(blob.decode("utf-8")).get("listType")
    except json.JSONDecodeError:
        return False, "not json"
    return (want is not None and got == want), got


def transferability(year: int, kinds: list[str]) -> int:
    """Pull each college's course list for each transfer-area list type."""
    print("handshake         verified, header token comes from the %s cookie"
          % handshake())
    vocab = json.loads(get(f"{BASE}/transferability/areaTypes").decode("utf-8"))
    wanted = dict(list_types(vocab))
    unknown = [k for k in kinds if k not in wanted]
    if unknown:
        raise SystemExit(
            "%s is not in the vocabulary the service publishes (%s). The "
            "service answers an unrecognised token with a different list "
            "rather than an error, so this stops instead of sweeping."
            % (", ".join(unknown), ", ".join(sorted(wanted))))
    schools = institutions()
    cc = [s for s in schools if s.get("isCommunityCollege")]
    root = OUT / ("transferability_%d" % year)
    root.mkdir(parents=True, exist_ok=True)
    done = new = skipped = 0
    for school in cc:
        for kind in kinds:
            dest = root / ("%d_%s.json" % (school["id"], kind))
            done += 1
            if dest.exists():
                skipped += 1
                continue
            url = (f"{BASE}/transferability/courses?institutionId={school['id']}"
                   f"&academicYearId={year - YEAR_BASE}&listType={kind}")
            try:
                blob = get(url)
                ok, got = honoured(blob, wanted.get(kind))
                if not ok:
                    print("  [%4d/%4d] %-30s %-12s DECLINED, listType %s"
                          % (done, len(cc) * len(kinds), name_of(school)[:30],
                             kind, got), flush=True)
                    time.sleep(DELAY)
                    continue
            except Exception as exc:                      # noqa: BLE001
                print("  [%4d/%4d] %-30s %-12s FAILED %s"
                      % (done, len(cc) * len(kinds), name_of(school)[:30], kind,
                         str(exc)[:50]), flush=True)
                time.sleep(DELAY)
                continue
            dest.write_bytes(blob)
            new += 1
            print("  [%4d/%4d] %-30s %-12s %d B"
                  % (done, len(cc) * len(kinds), name_of(school)[:30], kind,
                     len(blob)), flush=True)
            time.sleep(DELAY)
    print("\n%d slots, %d fetched now, %d already on disk" % (done, new, skipped))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnose", action="store_true",
                    help="find a request the API answers; writes nothing")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--areas", action="store_true",
                    help="enumerate the transfer-area vocabulary and sample it")
    ap.add_argument("--transferability", nargs="*", metavar="LISTTYPE",
                    help="sweep every college for these list types")
    ap.add_argument("--year", type=int, default=YEAR)
    ap.add_argument("--grid", type=int, default=3, help="--pilot grid side")
    args = ap.parse_args()
    if args.diagnose:
        return diagnose()
    if args.probe:
        return probe(args.year)
    if args.pilot:
        return pilot(args.year, args.grid)
    if args.pull:
        return sweep(args.year)
    if args.areas:
        return areas(args.year)
    if args.transferability is not None:
        if not args.transferability:
            return ap.error('name the list types, from --areas')
        return transferability(args.year, args.transferability)
    return ap.error("pass --areas or --probe first. Pulling on an unverified parse is the "
                    "mistake this ordering exists to prevent.")


if __name__ == "__main__":
    raise SystemExit(main())
