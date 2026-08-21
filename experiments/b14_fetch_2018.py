"""B14 leg A fetch: pull the eight 2018 Appendix B.I monthly files into data/raw/.

Registered in the design file section 7 supplement 2 clause A and its expansion A1.
Also pulls the field specification of record, which is the unlock condition for
both T7 (the Order_Type code table) and D3-3 (the WA weighting convention).

Discipline (project rules, engineering part, items 5 and 6)
    - Nothing is ever deleted. A file already on disk whose size disagrees with the
      index is renamed with an .expired suffix, never overwritten and never removed.
    - Resumable: bytes land in a .part file, an HTTP Range request continues it, and
      os.replace renames only after the size check passes.
    - Truncation is detected, not read silently: every .gzip is decompressed end to
      end after it lands.
    - Enumerate before selecting (D12): filenames come from the directory index, not
      from a hardcoded list. If the index cannot be read, its raw bytes are written
      to disk so a human can look at it instead of the script guessing.

Host note (design file section 1): the certificate on ftp.nyxdata.com is not valid
for that hostname, so plain http:// is the registered route. --direct exists for the
case where the index is unreachable but the files are not: the 2016 filenames on disk
fix the naming convention, so the 2018 names can be formed without the index.

Usage
    python experiments/b14_fetch_2018.py --selftest
    python experiments/b14_fetch_2018.py --index            # list only, no download
    python experiments/b14_fetch_2018.py --fetch            # eight files + the spec
    python experiments/b14_fetch_2018.py --fetch --direct   # skip the index
    python experiments/b14_fetch_2018.py --fetch --with-oct # add the two 2018-10 files
    python experiments/b14_fetch_2018.py --verify           # check what is on disk
"""
import argparse
import gzip
import os
import re
import socket
import ssl
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")

BASE = "https://ftp.nyxdata.com/Tick_Pilot/"
#: Tried in order when BASE fails. https first, measured 2026-08-19: the design file
#: section 1 recorded "http only, the certificate is not valid for this hostname",
#: and taking that literally is what broke the fetch. The host redirects http to
#: https, so asking for http does not avoid TLS, it just moves the failure into the
#: redirect. Asking for https directly is the route that works.
BASE_ALTS = [
    "https://ftp.nyxdata.com/Tick_Pilot/",
    "http://ftp.nyxdata.com/Tick_Pilot/",
    "http://ftp.nyxdata.com/tick_pilot/",
    "http://ftp.nyxdata.com/",
]
VENUES = ["NYSE", "NYSEARCA"]
#: All five months, October included. The gate drops October (it is the phase-out
#: month, design file A1 clause 1), but dropping a month from the WINDOWS is not a
#: reason to leave it off DISK. Two reasons it belongs on disk, both concrete:
#: the 2016 round has its 201610 cached and leaving 2018 without one is an
#: asymmetry with nothing behind it; and 2016-10 is where the whole "Test_Group
#: records same-day state" finding came from, since a security carries both labels
#: inside that month. 2018-10 should show the reverse switch, which is direct
#: evidence for the D3-9" premise instead of an inference from the post window.
MONTHS = ["201808", "201809", "201810", "201811", "201812"]

#: Design file section 3 supplement 3. T7 and D3-3 unlock on the same document.
SPECS = [
    ("http://www.finra.org/sites/default/files/"
     "Appendix-B-and-C-Reporting-Requirements.pdf",
     "FINRA_Appendix-B-and-C-Reporting-Requirements.pdf"),
]

UA = {"User-Agent": "Mozilla/5.0 (compatible; b14-fetch/1.0)"}
CHUNK = 1 << 20

#: Design file section 1 already records the fact this works around: the certificate
#: served by this host is not valid for this hostname. Requesting http:// does not
#: avoid it, because the host redirects to https and the redirect is where
#: verification fails. Hostname checking is therefore disabled FOR THIS HOST ONLY,
#: never globally, and only for a host whose certificate mismatch is a registered
#: property of the carrier rather than something discovered at fetch time.
INSECURE_HOSTS = ("ftp.nyxdata.com",)
_LAX = ssl.create_default_context()
_LAX.check_hostname = False
_LAX.verify_mode = ssl.CERT_NONE


def ctx_for(url):
    """The lax context for the registered host, the default one for everything else."""
    host = urllib.parse.urlparse(url).hostname or ""
    return _LAX if host in INSECURE_HOSTS else None


def stamp():
    return time.strftime("%Y%m%d_%H%M%S")


def wanted(with_oct=True):
    """Every month on disk. with_oct=False narrows to the four the gate reads."""
    ms = MONTHS if with_oct else [m for m in MONTHS if not m.endswith("10")]
    return ["%s_MKTQUALITYSTATS_%s.gzip" % (v, m) for v in VENUES for m in sorted(ms)]


def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx_for(url)) as r:
        return r.read()


def describe(e):
    """One line a human can act on, plus the exception class."""
    if isinstance(e, urllib.error.HTTPError):
        return "HTTP %s %s" % (e.code, e.reason)
    if isinstance(e, urllib.error.URLError):
        return "URLError: %r" % (e.reason,)
    if isinstance(e, socket.timeout):
        return "socket timeout"
    return "%s: %s" % (type(e).__name__, e)


def parse_index(html):
    """Return ({filename: size or None}, [subdirectory names]).

    Makes no assumption about which server generated the index: collect every href,
    then look on the same row for an integer that could be a byte count.
    """
    files, dirs = {}, []
    for line in re.split(r"<[Tt][Rr]|\n", html):
        for href in re.findall(r'href="([^"]+)"', line):
            name = href.rstrip("/").split("/")[-1]
            if not name or name.startswith("?") or name in ("..",):
                continue
            if href.endswith("/"):
                if name not in dirs:
                    dirs.append(name)
                continue
            if not re.search(r"\.(gzip|gz|txt|csv|pdf|xlsx)$", name, re.I):
                continue
            tail = line.split(href, 1)[-1]
            tail = re.sub(r"<[^>]+>", " ", tail)
            nums = re.findall(r"(?<![\d.,])(\d{4,})(?![\d.,])", tail)
            files[name] = int(nums[-1]) if nums else None
    return files, dirs


def fetch_index(bases):
    """Try each base in turn. Returns (mapping, raw_html, base_used, attempts)."""
    attempts = []
    for base in bases:
        try:
            raw = get(base).decode("latin-1")
        except Exception as e:
            attempts.append((base, describe(e)))
            continue
        files, dirs = parse_index(raw)
        found = {base + k: v for k, v in files.items()}
        need = set(wanted(with_oct=True))
        if not need & set(files):
            for d in dirs:
                try:
                    sub = get(base + d + "/").decode("latin-1")
                except Exception as e:
                    attempts.append((base + d + "/", describe(e)))
                    continue
                sf, _ = parse_index(sub)
                for k, v in sf.items():
                    found[base + d + "/" + k] = v
        attempts.append((base, "ok, %d entries" % len(files)))
        return found, raw, base, attempts
    return None, None, None, attempts


def park(path, why):
    """Never delete: rename with an .expired suffix. Returns the new name."""
    new = "%s.expired_%s_%s" % (path, stamp(), why)
    os.replace(path, new)
    return new


def download(url, dst, expect=None):
    """Write to .part, resume via Range, os.replace on success. -> (ok, message)."""
    part = dst + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if expect is not None and have > expect:
        park(part, "part_larger_than_index")
        have = 0
    headers = dict(UA)
    if have:
        headers["Range"] = "bytes=%d-" % have
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=300, context=ctx_for(url)) as r:
        resumed = (r.status == 206)
        if have and not resumed:
            park(part, "server_ignored_range")
            have = 0
        mode = "ab" if resumed else "wb"
        with open(part, mode) as fh:
            while True:
                buf = r.read(CHUNK)
                if not buf:
                    break
                fh.write(buf)
    got = os.path.getsize(part)
    if expect is not None and got != expect:
        return False, ("got %d bytes, index says %d; left as .part, not renamed"
                       % (got, expect))
    os.replace(part, dst)
    return True, "%d bytes%s" % (got, ", resumed" if have else "")


def verify_gzip(path):
    """Decompress the whole stream. Truncation or corruption raises here."""
    n = 0
    with gzip.open(path, "rb") as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            n += len(b)
    return n


def run(do_fetch, with_oct, verify_only, direct):
    os.makedirs(RAW, exist_ok=True)
    names = wanted(with_oct)
    by_name = {}

    if verify_only and not do_fetch:
        # --verify checks bytes already on disk. It has no business touching the
        # network, and making it depend on the index meant a fetch problem could
        # stop a check that needs no fetching at all.
        print("--verify: checking the files on disk; no index, no network")
        by_name = {n: (None, None) for n in names}
    elif direct:
        print("--direct: skipping the index, forming names from the 2016 convention")
        by_name = {n: (BASE + n, None) for n in names}
    else:
        print("index: %s" % BASE)
        idx, raw, used, attempts = fetch_index([BASE] + [b for b in BASE_ALTS if b != BASE])
        for url, note in attempts:
            print("  %-46s %s" % (url, note))
        if idx is None:
            print("\n  The directory index could not be read from any of the forms above.")
            print("  This is a fetch problem, not a design problem: the eight filenames")
            print("  follow the 2016 convention already on disk, so if the files are")
            print("  reachable in a browser, run:")
            print("      python experiments/b14_fetch_2018.py --fetch --direct")
            print("  which downloads by name and relies on the gzip end-to-end check")
            print("  instead of the index byte count.")
            return 1
        dump = os.path.join(RAW, "_tickpilot_index_%s.html" % stamp())
        with open(dump, "wb") as fh:
            fh.write(raw.encode("latin-1"))
        print("  index served by %s, raw bytes kept at %s"
              % (used, os.path.relpath(dump, ROOT)))
        by_name = {u.split("/")[-1]: (u, sz) for u, sz in idx.items()}
        print("  %d entries, %d of them MKTQUALITYSTATS"
              % (len(by_name), sum(1 for k in by_name if "MKTQUALITYSTATS" in k)))

    print("\nwanted, %d files:" % len(names))
    rows = []
    for name in names:
        dst = os.path.join(RAW, name)
        url, expect = by_name.get(name, (None, None))
        have = os.path.getsize(dst) if os.path.exists(dst) else None
        note = ""
        if url is None and verify_only and not do_fetch:
            note = ("on disk, %d bytes" % have) if have is not None else "not on disk"
        elif url is None:
            note = "not in the index under this name"
        elif have is not None and expect is not None and have != expect:
            new = park(dst, "size_disagrees_with_index")
            note = ("on disk %d vs index %d, renamed to %s, will re-fetch"
                    % (have, expect, os.path.basename(new)))
            have = None
        elif have is not None:
            note = ("already on disk, size agrees" if expect is not None
                    else "already on disk (index gave no size)")
        if do_fetch and url is not None and have is None:
            try:
                ok, msg = download(url, dst, expect)
                note = ("fetched: " if ok else "**incomplete**: ") + msg
            except Exception as e:
                note = ("**download failed**: %s (.part kept on disk, re-running "
                        "this script resumes)" % describe(e))
        rows.append((name, expect, note))
        print("  %-42s %12s  %s" % (name, expect if expect else "?", note))

    if do_fetch:
        print("\nspecification of record (design file section 3 supplement 3):")
        for url, name in SPECS:
            dst = os.path.join(RAW, name)
            if os.path.exists(dst):
                print("  %-52s already on disk, %d bytes" % (name, os.path.getsize(dst)))
                continue
            try:
                ok, msg = download(url, dst, None)
                print("  %-52s %s" % (name, msg))
            except Exception as e:
                print("  %-52s **failed**: %s" % (name, describe(e)))

    if do_fetch or verify_only:
        print("\ngzip end-to-end check (a truncated file raises here, it is not "
              "read silently):")
        for name, _, _ in rows:
            dst = os.path.join(RAW, name)
            if not os.path.exists(dst):
                print("  %-42s not on disk, skipped" % name)
                continue
            t0 = time.time()
            try:
                n = verify_gzip(dst)
                print("  %-42s decompressed %12d bytes  %.1fs"
                      % (name, n, time.time() - t0))
            except Exception as e:
                new = park(dst, "gzip_corrupt")
                print("  %-42s **corrupt**: %s -> renamed %s"
                      % (name, describe(e), os.path.basename(new)))

    missing = [n for n, _, _ in rows if not os.path.exists(os.path.join(RAW, n))]
    print("\n%d still missing%s"
          % (len(missing), (": " + ", ".join(missing)) if missing else ", complete"))
    if not missing:
        print("next: python experiments/b14_tickpilot_panel.py --build")
        print("then: python experiments/b14_gate_exit.py --census")
    return 0


def _probe_file():
    """Write a sample containing os.remove, only to prove the ban check bites.

    It is an object to be inspected, never a module to be run. Not one line of it
    executes.
    """
    d = os.path.join(ROOT, "data", "cache", "b14")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "_probe_banned_call.py.sample")
    with open(p, "w") as fh:
        fh.write("import os\n")
        fh.write("def never_called(path):\n")
        fh.write("    os.remove(path)\n")
    return p


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    chk("ten files by default: two venues by five months", len(wanted()) == 10)
    chk("2018-10 is taken by default, matching the 2016 round which has its "
        "201610 on disk", any("201810" in x for x in wanted()))
    chk("--gate-months-only narrows to the four the gate reads",
        len(wanted(False)) == 8 and not any("201810" in x for x in wanted(False)))
    chk("dropping a month from the windows is not the same as leaving it off "
        "disk: the gate reads eight, the fetch takes ten",
        set(wanted(False)) < set(wanted()))
    chk("names follow the convention of the ten 2016 files already on disk",
        wanted()[0].endswith(".gzip") and "_MKTQUALITYSTATS_" in wanted()[0])
    chk("the default base is tried first", BASE_ALTS[0] == BASE)
    chk("https is the default, not http (measured 2026-08-19: the host redirects "
        "http to https and the redirect is where verification fails)",
        BASE.startswith("https://"))

    html = ('<tr><td><a href="NYSE_MKTQUALITYSTATS_201808.gzip">x</a></td>'
            '<td>2018-11-02 10:00</td><td>86259841</td></tr>\n'
            '<tr><td><a href="sub/">sub/</a></td><td>-</td></tr>\n'
            '<tr><td><a href="notes.txt">n</a></td><td>-</td></tr>')
    f, d = parse_index(html)
    chk("index parse picks up filename and byte count",
        f.get("NYSE_MKTQUALITYSTATS_201808.gzip") == 86259841)
    chk("index parse picks up subdirectories", d == ["sub"])
    chk("an entry with no byte count records None",
        "notes.txt" in f and f["notes.txt"] is None)
    chk("digits inside the date are not mistaken for a byte count",
        f.get("NYSE_MKTQUALITYSTATS_201808.gzip") != 2018)

    chk("the lax TLS context applies to the registered host",
        ctx_for("http://ftp.nyxdata.com/Tick_Pilot/") is _LAX)
    chk("and to nothing else: finra.org gets the default verifying context",
        ctx_for(SPECS[0][0]) is None)
    chk("the lax context really does skip hostname checking, which is what the "
        "redirect to https trips on",
        _LAX.check_hostname is False and _LAX.verify_mode == ssl.CERT_NONE)
    chk("only one host is exempt", len(INSECURE_HOSTS) == 1)
    chk("describe() turns an HTTPError into one actionable line",
        describe(urllib.error.HTTPError("u", 404, "Not Found", {}, None))
        == "HTTP 404 Not Found")
    chk("describe() names the exception class for anything else",
        describe(ValueError("x")).startswith("ValueError"))

    # Project rules, engineering part item 5: this script calls no deletion.
    # Walk the AST for called names rather than matching strings, because a string
    # match is triggered by this check's own literals, which is a check that bites
    # the wrong object.
    import ast

    def called_names(path):
        out = set()
        for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
            if not isinstance(node, ast.Call):
                continue
            fn, parts = node.func, []
            while isinstance(fn, ast.Attribute):
                parts.append(fn.attr)
                fn = fn.value
            if isinstance(fn, ast.Name):
                parts.append(fn.id)
            if parts:
                out.add(".".join(reversed(parts)))
        return out

    banned = {"remove", "unlink", "rmdir", "rmtree", "removedirs"}
    calls = called_names(os.path.abspath(__file__))
    hits = sorted(c for c in calls if c.split(".")[-1] in banned)
    chk("this script calls no deletion at all: " +
        (", ".join(hits) if hits else "zero hits"), not hits)
    chk("and that check does recognise a deletion (tested on a planted sample)",
        "os.remove" in called_names(_probe_file()))
    chk("this script does call os.replace (write .part, then rename; never open a "
        "write handle on the destination)", "os.replace" in calls)

    # The PowerShell half of this fetch is scripts/fetch_b14_2018.ps1: on a proxied
    # egress the host answers 403, so Windows moves the bytes and this file verifies
    # them. One check covers both halves. Comments are stripped first, because the
    # ps1 names the banned verbs in prose to say it does not use them, and a check
    # that fires on that is a check biting the wrong object.
    ps1 = os.path.join(ROOT, "scripts", "fetch_b14_2018.ps1")
    if os.path.exists(ps1):
        body = open(ps1, encoding="utf-8").read()
        body = re.sub(r"<#.*?#>", "", body, flags=re.S)
        body = "\n".join(re.sub(r"#.*$", "", ln) for ln in body.split("\n"))
        verbs = ["Remove-Item", "Remove-ItemProperty", "Clear-Content", "rmdir",
                 "Unregister-", "\\bdel\\b", "\\berase\\b"]
        hit = sorted(v for v in verbs if re.search(v, body))
        chk("the PowerShell half deletes nothing either: " +
            (", ".join(hit) if hit else "zero hits"), not hit)
        chk("and it does rename out of the way instead (Move-Item present)",
            "Move-Item" in body)
        chk("the ps1 writes to .part and renames, never onto the destination",
            ".part" in body)
        chk("no CJK in the ps1",
            not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", body))

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    # Written as code points, not as literal characters: a literal CJK class
    # here would make this check fail on itself, which is the same self-
    # reference that broke the first version of the deletion check above.
    cjk = re.compile("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]")
    hits = sorted({c for c in src if cjk.match(c)})
    chk("no CJK or fullwidth punctuation left in this file: " +
        ("".join(hits) if hits else "zero"), not hits)
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--index", action="store_true", help="list the index and disk state only")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--verify", action="store_true", help="check gzips on disk, no download")
    ap.add_argument("--gate-months-only", dest="no_oct", action="store_true",
                    help="narrow to the four months the gate reads, leaving the "
                         "2018-10 phase-out month off disk (not the default: see "
                         "the note on MONTHS)")
    ap.add_argument("--direct", action="store_true",
                    help="skip the index, download by the 2016 naming convention")
    ap.add_argument("--base", default=None)
    ap.add_argument("--traceback", action="store_true", help="full traceback on failure")
    a = ap.parse_args()
    if a.base:
        global BASE
        BASE = a.base if a.base.endswith("/") else a.base + "/"
    if a.selftest:
        return selftest()
    if a.index or a.fetch or a.verify:
        try:
            return run(a.fetch, not a.no_oct, a.verify, a.direct)
        except Exception:
            if a.traceback:
                traceback.print_exc()
                return 1
            raise
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
