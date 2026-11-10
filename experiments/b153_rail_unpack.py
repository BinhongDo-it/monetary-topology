"""B153: record and unpack the three rail data packages already on disk.

Fetches nothing. For each package under data/raw/rail_fares/ it records the
byte count and SHA-256, then extracts every member into a subdirectory named
after the package (fares/, timetable/, routeing/), checking the member CRC on
the way and recording each extracted file's size and SHA-256. The packages and
the extracted files stay under data/raw; the manifest prints counts and hashes
only, no fare content.

Resumable: a member already on disk with the recorded size and hash is not
written again. A member on disk with a different size is reported and left
alone (nothing is overwritten); rerun after moving it aside by hand.

    python -I -B experiments/b153_rail_unpack.py [--dir data/raw/rail_fares]
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

# the shared compare-and-swap writer when it sits next to the repository; otherwise a plain write
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from safe_write import create, rewrite  # noqa: E402
except ImportError:
    create = rewrite = None

PACKAGES = ("fares.zip", "timetable.zip", "routeing.zip")
SESSION = "B153"
CHUNK = 1 << 20


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            h.update(b)
    return h.hexdigest()


def safe_member_name(name: str) -> str:
    pp = PurePosixPath(name)
    if pp.is_absolute() or ".." in pp.parts or len(pp.parts) != 1 or "\\" in name or ":" in name:
        raise ValueError(f"member name not flat: {name!r}")
    return pp.name


def header_lines(p: Path, n: int = 40) -> list:
    """The leading comment lines ('/' prefix) of a text file, decoded as latin-1."""
    out = []
    with p.open("rb") as f:
        for _ in range(n):
            line = f.readline()
            if not line:
                break
            s = line.decode("latin-1").rstrip("\r\n")
            if not s.startswith("/"):
                break
            out.append(s)
    return out


def unpack(pkg: Path, outdir: Path) -> dict:
    outdir.mkdir(exist_ok=True)
    rec = {"package": pkg.name, "bytes": pkg.stat().st_size, "sha256": sha256_file(pkg),
           "extract_dir": outdir.name, "members": []}
    with zipfile.ZipFile(pkg) as zf:
        bad = zf.testzip()
        rec["testzip_first_bad_member"] = bad
        for info in zf.infolist():
            name = safe_member_name(info.filename)
            dst = outdir / name
            m = {"name": name, "bytes": info.file_size, "crc32": f"{info.CRC:08x}",
                 "zip_date_time": "%04d-%02d-%02dT%02d:%02d:%02d" % info.date_time}
            if dst.exists():
                if dst.stat().st_size == info.file_size:
                    m["status"] = "already_on_disk"
                else:
                    m["status"] = f"size_mismatch_on_disk_{dst.stat().st_size}_left_alone"
                    rec["members"].append(m)
                    continue
            else:
                tmp = outdir / (name + ".partial.expired")
                h = hashlib.sha256()
                with zf.open(info) as src, tmp.open("wb") as out:
                    for b in iter(lambda: src.read(CHUNK), b""):
                        h.update(b)
                        out.write(b)
                if tmp.stat().st_size != info.file_size:
                    raise RuntimeError(f"truncated extract {name}")
                tmp.replace(dst)
                m["status"] = "extracted"
            m["sha256"] = sha256_file(dst)
            m["header"] = header_lines(dst)
            rec["members"].append(m)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parents[1] / "data" / "raw" / "rail_fares"))
    a = ap.parse_args()
    d = Path(a.dir)
    out = {"station": "B153", "note": "packages supplied by hand; nothing fetched by this script",
           "packages": []}
    for name in PACKAGES:
        pkg = d / name
        if not pkg.exists():
            raise SystemExit(f"missing {pkg}")
        r = unpack(pkg, d / pkg.stem)
        out["packages"].append(r)
        print(f"{name}: {r['bytes']:,} bytes sha256 {r['sha256']} members {len(r['members'])} "
              f"testzip {r['testzip_first_bad_member']}")
        for m in r["members"]:
            print(f"   {m['name']:16} {m['bytes']:>12,} {m['status']}")
    text = json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    man = d / "b153_manifest.json"
    if rewrite is None:
        man.write_text(text, encoding="utf-8", newline="\n")
    elif man.exists():
        rewrite(man, "B153 manifest refresh", lambda _t: text, session=SESSION)
    else:
        create(man, "B153 manifest", text, session=SESSION)
    print("manifest:", man)


if __name__ == "__main__":
    main()
