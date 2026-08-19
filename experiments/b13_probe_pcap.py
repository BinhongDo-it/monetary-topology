# -*- coding: utf-8 -*-
"""B13 probe: what is in a CME Globex MDP 3.0 PCAP, without decoding any field
whose offset has not been checked against the data.

**This is a probe, not the station.** It answers structural questions and
declines everything else:

  survey     one pass: every multicast group, and the template histogram per group
  groups     multicast groups only
  templates  template histogram for one group
  peek       one raw message per template, hex and ascii

`survey` exists because a pass over a trading-day capture takes tens of minutes,
and running it twice to learn two things it could have learned once is the whole
cost again.

**Pass `--file`, do not pipe.** `--file` spawns `zstd -dc` itself through a real
OS pipe. Piping from a shell works on Unix and is a trap in PowerShell: its
pipeline is an object pipeline, so it decodes the bytes as text, buffers, and
re-encodes. If the reader exits, PowerShell does not deliver SIGPIPE, so `zstd`
keeps decompressing and PowerShell keeps buffering. **That is how a crash in the
first millisecond of this script ate 32 GB of RAM on 2026-08-19** (the mode
argument was declared as a positional whose values began with `--`, which
argparse reads as options, so the script died before reading a byte).

Both faults are fixed here: the modes are bare words, and `--file` removes the
shell from the path.

  python experiments/b13_probe_pcap.py survey --file data/raw/b13/x.pcap.zst --out out.txt

`--limit` and `--seconds` stop early and **say so in the output**, because a
truncated scan that does not announce it is indistinguishable from a complete
one.
"""
import argparse
import collections
import os
import struct
import subprocess
import sys
import time

TEMPLATE_NAMES = {
    12: "AdminHeartbeat",
    30: "SecurityStatus",
    32: "MDIncrementalRefreshBook (pre-2017 MBP)",
    42: "MDIncrementalRefreshTradeSummary",
    43: "MDIncrementalRefreshOrderBook (MBO)",
    44: "MDIncrementalRefreshVolume",
    45: "SnapshotFullRefresh",
    46: "MDIncrementalRefreshBook (MBP)  <- implied lives here",
    47: "MDIncrementalRefreshOrderBook (MBO)  <- carries no implied",
    48: "MDIncrementalRefreshTradeSummary",
    49: "MDIncrementalRefreshDailyStatistics",
    50: "MDIncrementalRefreshLimitsBanding",
    51: "MDIncrementalRefreshSessionStatistics",
    52: "MDIncrementalRefreshVolume",
    53: "SnapshotFullRefresh",
    # **54 and 56 are named from the data, not from a schema.** On channel 382
    # every one of the 20,622 template-54 symbols is an outright and 24,751 of
    # the 25,897 template-56 symbols contain a hyphen, which is CME's spread
    # symbology. Template 55 does not appear at all. The obvious reading of the
    # numbers, that 56 is the option definition, is wrong here and would have
    # sent a search for calendar spreads to a template that is never sent.
    54: "MDInstrumentDefinitionFuture (outrights, measured)",
    55: "MDInstrumentDefinitionSpread (never seen on ch382)",
    56: "MDInstrumentDefinition, SPREADS on ch382 (measured, not the schema name)",
    57: "MDIncrementalRefreshBook (MBP)",
    58: "SnapshotRefreshTopOrders (MBO)",
    59: "SecurityStatusWorkup",
    60: "SnapshotFullRefreshOrderBook (MBO)",
}

PCAP_LE = (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1")
PCAP_BE = (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d")


def open_stream(path, want_total=False):
    """Return (binary stream, child process or None, decompressed size or None).

    Spawns `zstd -dc` rather than asking the caller to pipe, so the shell never
    touches the bytes. See the module docstring for what happened when it did.
    """
    if path is None:
        return sys.stdin.buffer, None, None
    if not path.endswith(".zst"):
        fh = open(path, "rb")
        return fh, None, os.path.getsize(path)
    try:
        proc = subprocess.Popen(["zstd", "-dc", path],
                                stdout=subprocess.PIPE, bufsize=1 << 22)
    except FileNotFoundError:
        raise SystemExit(
            "zstd not found on PATH. Install it (winget install Facebook.Zstandard, "
            "or apt install zstd) or decompress first and pass the .pcap.")
    total = None
    # `zstd -l` has to walk the frame index, which on a multi-GB file sitting on
    # a network-backed mount took **longer than the scan itself**. It buys a
    # percentage in the progress line and nothing else, so it is off by default.
    if not want_total:
        return proc.stdout, proc, None
    try:
        out = subprocess.run(["zstd", "-l", path], capture_output=True,
                             text=True, timeout=60).stdout
        for tok in out.replace("MiB", " MiB").replace("GiB", " GiB").split("\n"):
            parts = tok.split()
            if "GiB" in parts:
                total = float(parts[parts.index("GiB") - 1]) * (1 << 30)
            elif "MiB" in parts:
                total = float(parts[parts.index("MiB") - 1]) * (1 << 20)
    except Exception:
        total = None
    return proc.stdout, proc, total


def packets(stream, limit, deadline, every, total_bytes):
    """Yield (dst_ip:port, udp_payload) for every UDP/IPv4 packet.

    Pure stdlib on purpose: the machines this has to run on have no scapy, no
    dpkt and no zstandard module, and a probe that cannot run where the data is
    is not a probe. Memory is O(1); nothing here accumulates.
    """
    head = stream.read(24)
    if len(head) < 24:
        raise SystemExit("input ended inside the pcap global header")
    magic = head[:4]
    if magic in PCAP_LE:
        end = "<"
    elif magic in PCAP_BE:
        end = ">"
    else:
        raise SystemExit("unknown pcap magic %s (pcapng starts 0a0d0d0a and is "
                         "not handled here)" % magic.hex())
    nanos = magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")
    link = struct.unpack(end + "I", head[20:24])[0]
    if link != 1:
        raise SystemExit("linktype %d is not Ethernet; this parser assumes it" % link)
    print("pcap: %s-endian, %s timestamps, Ethernet, snaplen %d"
          % ("little" if end == "<" else "big",
             "nanosecond" if nanos else "microsecond",
             struct.unpack(end + "I", head[16:20])[0]), file=sys.stderr, flush=True)

    rec = struct.Struct(end + "IIII")
    read = stream.read
    n = 0
    nbytes = 24
    first = last = None
    t0 = time.time()
    stopped = None
    while n < limit:
        h = read(16)
        if len(h) < 16:
            break
        secs, _frac, incl, _orig = rec.unpack(h)
        body = read(incl)
        if len(body) < incl:
            stopped = "input ended mid-record after %d packets" % n
            break
        n += 1
        nbytes += 16 + incl
        if first is None:
            first = secs
        last = secs
        if n % every == 0:
            el = time.time() - t0
            rate = n / el if el else 0
            msg = "  %d packets, %.1f GB, %.0f pkt/s, %.0f s elapsed" % (
                n, nbytes / (1 << 30), rate, el)
            if total_bytes:
                frac = nbytes / total_bytes
                if frac > 0:
                    msg += ", %.1f%% done, ~%.0f s left" % (
                        100 * frac, el * (1 - frac) / frac)
            print(msg, file=sys.stderr, flush=True)
            if time.time() > deadline:
                stopped = "hit the --seconds limit after %d packets" % n
                break
        off = 14
        if len(body) < 14:
            continue
        etype = struct.unpack(">H", body[12:14])[0]
        while etype in (0x8100, 0x88A8) and len(body) >= off + 4:
            etype = struct.unpack(">H", body[off + 2:off + 4])[0]
            off += 4
        if etype != 0x0800:
            continue
        ip = body[off:]
        if len(ip) < 20 or (ip[0] >> 4) != 4 or ip[9] != 17:
            continue
        udp = ip[(ip[0] & 0xF) * 4:]
        if len(udp) < 8:
            continue
        yield ("%d.%d.%d.%d:%d" % (ip[16], ip[17], ip[18], ip[19],
                                   struct.unpack(">H", udp[2:4])[0]), udp[8:])
    if n >= limit:
        stopped = "hit the --limit of %d packets" % limit
    packets.summary = (n, nbytes, first, last, time.time() - t0, stopped)


def sbe_messages(payload):
    """Yield (template_id, raw) from one MDP 3.0 packet.

    Packet = MsgSeqNum uint32 + SendingTime uint64, then repeated
    Message = MsgSize uint16 + SBE header (BlockLength, TemplateID, SchemaID,
    Version), little-endian throughout.
    """
    q = 12
    while q + 10 <= len(payload):
        size = struct.unpack("<H", payload[q:q + 2])[0]
        if size < 8 or q + size > len(payload):
            return
        yield struct.unpack("<H", payload[q + 4:q + 6])[0], payload[q:q + size]
        q += size


def entry_types(raw):
    """Yield (MDEntryType char, SecurityID) for one template 46 message.

    Every offset below is read off the bytes, not assumed. SBE header 10 bytes,
    then a root block of BlockLength bytes (TransactTime uint64,
    MatchEventIndicator uint8, padding), then repeating groups each introduced
    by blockLength uint16 + numInGroup uint8.

    The first group is NoMDEntries, entry length 32 in schema 1 version 9:
    MDEntryPx int64 @0, MDEntrySize int32 @8, SecurityID int32 @12,
    RptSeq uint32 @16, NumberOfOrders int32 @20, MDPriceLevel uint8 @24,
    MDUpdateAction uint8 @25, **MDEntryType char @26**, padding to the
    blockLength the message itself declares.

    **Tag 269 is that char.** `0` and `1` are the directly quoted bid and offer,
    `E` and `F` are the implied bid and offer the matching engine derived from
    the outright legs. Telling those two apart is the whole station (design file
    section 1), and both arrive inside the same message.
    """
    block = struct.unpack("<H", raw[2:4])[0]
    o = 10 + block
    if o + 3 > len(raw):
        return
    ent, num = struct.unpack("<HB", raw[o:o + 3])
    o += 3
    if ent < 27:
        return
    for _ in range(num):
        if o + ent > len(raw):
            return
        yield chr(raw[o + 26]), struct.unpack("<i", raw[o + 12:o + 16])[0]
        o += ent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("survey", "groups", "templates", "peek",
                                     "entrytypes"))
    ap.add_argument("group", nargs="?", help="ip:port, needed by templates and peek")
    ap.add_argument("--file", help=".pcap or .pcap.zst; omit to read stdin")
    ap.add_argument("--out", help="write the report here as well as to stdout")
    ap.add_argument("--limit", type=int, default=10 ** 12)
    ap.add_argument("--seconds", type=float, default=1e9)
    ap.add_argument("--every", type=int, default=2_000_000,
                    help="progress line every N packets")
    ap.add_argument("--eta", action="store_true",
                    help="run `zstd -l` first so progress can show a percentage. "
                         "Slow on large files over a network mount; off by default")
    args = ap.parse_args()
    if args.mode in ("templates", "peek", "entrytypes") and not args.group:
        ap.error("%s needs a group, e.g. 224.0.31.130:14382" % args.mode)

    stream, proc, total = open_stream(args.file, args.eta)
    if total:
        print("decompressed size about %.1f GB" % (total / (1 << 30)),
              file=sys.stderr, flush=True)
    src = packets(stream, args.limit, time.time() + args.seconds, args.every, total)
    lines = []
    emit = lines.append

    try:
        if args.mode in ("survey", "groups"):
            count = collections.Counter()
            payload = collections.Counter()
            per = collections.defaultdict(collections.Counter)
            for key, data in src:
                count[key] += 1
                payload[key] += len(data)
                if args.mode == "survey":
                    tmpl = per[key]
                    for tid, _raw in sbe_messages(data):
                        tmpl[tid] += 1
            emit("%-24s %14s %16s" % ("dst ip:port", "packets", "udp payload B"))
            for key, num in count.most_common():
                emit("%-24s %14d %16d" % (key, num, payload[key]))
            emit("")
            emit("%d multicast groups" % len(count))
            if args.mode == "survey":
                for key, _num in count.most_common():
                    emit("")
                    emit("=== %s" % key)
                    for tid, num in per[key].most_common():
                        emit("  %-6d %14d  %s"
                             % (tid, num, TEMPLATE_NAMES.get(tid, "(unnamed here)")))
        elif args.mode == "entrytypes":
            wanted = set(args.group.split(","))
            kinds = collections.Counter()
            ids_implied = set()
            ids_real = set()
            msgs = 0
            for key, data in src:
                if key not in wanted:
                    continue
                for tid, raw in sbe_messages(data):
                    if tid != 46:
                        continue
                    msgs += 1
                    for ch, sid in entry_types(raw):
                        kinds[ch] += 1
                        if ch in "EF":
                            ids_implied.add(sid)
                        elif ch in "01":
                            ids_real.add(sid)
            emit("%d template-46 messages on %s, %d book entries"
                 % (msgs, args.group, sum(kinds.values())))
            emit("")
            meaning = {"0": "bid, directly quoted", "1": "offer, directly quoted",
                       "2": "trade", "4": "opening price", "6": "settlement",
                       "7": "session high", "8": "session low",
                       "B": "trade volume", "C": "open interest",
                       "E": "IMPLIED BID", "F": "IMPLIED OFFER",
                       "W": "book reset"}
            emit("%-6s %14s  %s" % ("269", "entries", "meaning"))
            for ch, num in kinds.most_common():
                emit("%-6s %14d  %s" % (repr(ch)[1:-1], num, meaning.get(ch, "?")))
            emit("")
            emit("distinct SecurityID with implied entries (E/F): %d" % len(ids_implied))
            emit("distinct SecurityID with direct entries (0/1):  %d" % len(ids_real))
            emit("ids carrying both:                              %d"
                 % len(ids_implied & ids_real))
            emit("")
            emit("implied-carrying SecurityIDs, first 60 sorted:")
            emit("  " + " ".join(str(i) for i in sorted(ids_implied)[:60]))
        elif args.mode == "templates":
            wanted = set(args.group.split(","))
            tmpl = collections.Counter()
            schema = collections.Counter()
            hit = 0
            for key, data in src:
                if key not in wanted:
                    continue
                hit += 1
                for tid, raw in sbe_messages(data):
                    tmpl[tid] += 1
                    schema[struct.unpack("<H", raw[6:8])[0]] += 1
            emit("%d packets on %s, %d SBE messages, schema ids %s"
                 % (hit, args.group, sum(tmpl.values()), dict(schema)))
            emit("")
            emit("%-6s %14s  %s" % ("tmpl", "count", "name"))
            for tid, num in tmpl.most_common():
                emit("%-6d %14d  %s" % (tid, num, TEMPLATE_NAMES.get(tid, "(unnamed here)")))
        else:
            wanted = set(args.group.split(","))
            seen = {}
            for key, data in src:
                if key not in wanted:
                    continue
                for tid, raw in sbe_messages(data):
                    seen.setdefault(tid, raw)
            for tid in sorted(seen):
                raw = seen[tid]
                emit("=== template %d  MsgSize=%d BlockLength=%d Schema=%d Version=%d  %s"
                     % (tid, struct.unpack("<H", raw[0:2])[0],
                        struct.unpack("<H", raw[2:4])[0],
                        struct.unpack("<H", raw[6:8])[0],
                        struct.unpack("<H", raw[8:10])[0],
                        TEMPLATE_NAMES.get(tid, "")))
                for i in range(0, min(len(raw), 288), 32):
                    row = raw[i:i + 32]
                    emit("  %04d  %-64s  %s"
                         % (i, row.hex(),
                            "".join(chr(c) if 32 <= c < 127 else "." for c in row)))
                emit("")
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()

    n, nbytes, first, last, el, stopped = getattr(
        packets, "summary", (0, 0, None, None, 0, "never started"))
    head = ["read %d packets, %.2f GB, in %.0f s (%.0f pkt/s)"
            % (n, nbytes / (1 << 30), el, n / el if el else 0),
            "capture spans %s..%s (%d s)" % (first, last, (last - first) if first else 0),
            ("COMPLETE, reached end of input" if stopped is None
             else "TRUNCATED: " + stopped),
            ""]
    text = "\n".join(head + lines) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("wrote %s" % args.out, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
