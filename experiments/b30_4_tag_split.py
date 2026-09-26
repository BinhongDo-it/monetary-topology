"""Step two of the B30-4 tag census: the split, applied to names alone.

**No price has been pulled on this carrier, and none is read here.** The whole
point of running this before step three is that a split drawn with the prices in
view is a split drawn to fit them, and nothing downstream could tell afterwards.

**The registered rule is binary** and is not changed here: a market tag names a
kind of thing a buyer would substitute within, and its size is set by how many
people make that kind rather than by the price level. Everything else is not a
market tag. **What this file adds is a sub-kind on the non-market side**, so that
an exclusion can be read and argued with rather than taken on trust, and a third
state for the ones the rule does not settle.

Sub-kinds on the non-market side, each failing the rule in its own way:

    jam        provenance. Size is set by how many entered an event
    engine     the tool it was built with. A buyer does not shop by engine
    hardware   the machine or headset targeted
    input      how it is controlled
    aesthetic  technique, palette, camera, era of look
    process    distribution, licence, source, teaching, meta-tooling
    policy     a declaration about the work rather than a description of it
    scope      length, structure, completeness, and the mechanics of play
    ip         derivative of one named work

**One sub-rule inside the third state**, written after the first classification ran
and before any price was pulled. The third state came back holding two different
things: forms of play (card game, nonogram, pinball, solitaire) and subjects the
work is about (cats, Christmas, Norse, mental health). The registered rule settles
the first kind and does not settle the second, so keeping them in one bucket was an
error in this file, not a property of the vocabulary. The discriminant is one line
and reads no count:

    does the tag name a form of play, or a subject the work is about?

A form of play is a market tag: a buyer shopping for a nonogram substitutes within
nonograms, and how many exist is set by how many people make them. A subject is
left in the third state, because whether a buyer substitutes within "cats" is not
something the rule answers. Nineteen names moved to the market side under this
sub-rule and two mechanics moved to ``scope``; the moves land at both ends of the
count range (card game at 24,400 and nonogram at 161), so the sub-rule is not a
move that fattens one end. **A purpose claim is neither a form nor a subject** and
stays in the third state: ``educational`` and ``experimental`` span every form.

Usage::

    python experiments/b30_4_tag_split.py            # classify and write
    python experiments/b30_4_tag_split.py --selftest # seed faults, assert they fire
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "results" / "b30_4_itch_tag_census.json"
OUT = ROOT / "results" / "b30_4_tag_split.json"

JAM = re.compile(r"(ludum dare|global game jam|ggj\d*|gbjam|lowrezjam|procjam|trijam"
                 r"|7dfps|7drl|1gam|game jam|roguelike challenge"
                 r"|game maker's toolkit jam)", re.I)

ENGINE = {
    "unity", "godot", "unreal engine", "gamemaker", "rpg maker", "rpg maker mz",
    "rpg maker mv", "ren'py", "twine", "bitsy", "pico-8", "construct 2", "löve",
    "stencyl", "sfml", "libgdx", "aseprite", "decker", "tyranobuilder",
    "puzzlescript", "hypercard", "corona sdk", "scratch", "tic-80",
    "fantasy-console",
}
HARDWARE = {
    "game boy", "game boy rom", "game boy advance",
    "nes (nintendo entertainment system)", "nes rom", "psx (playstation)", "commodore 64", "zx spectrum", "amiga",
    "amstrad cpc", "msx", "vic-20", "turbografx-16", "sega genesis", "mega drive",
    "dreamcast", "nintendo 64", "super nintendo", "playstation portable", "ms-dos",
    "dos", "playdate", "oculus quest", "oculus rift", "virtual reality (vr)",
    "augmented reality", "atari", "chip-8", "kinect", "leap motion", "doom wad",
}
INPUT_ = {
    "mouse only", "controller", "gamepad", "touch-friendly", "one-button",
    "voice-controlled", "typing", "tablet", "split screen", "local co-op",
}
AESTHETIC = {
    "2d", "3d", "pixel art", "low-poly", "hand-drawn", "voxel", "black and white",
    "two colors", "grayscale", "1-bit", "8-bit", "16-bit", "ascii", "neon",
    "pastel", "watercolor", "painting", "drawing", "isometric", "top-down",
    "first-person", "third person", "side scroller", "flat-shading", "vector",
    "lo-fi", "chiptune", "synthwave", "glitch", "psychedelic", "photorealistic",
    "cartoon", "manga", "colorful", "minimalist", "abstract", "retro", "parallax",
    "rotation", "stop-motion", "live-action", "fmv", "binaural", "screensaver",
    "wobbly", "perspective", "gothic", "noir", "surreal", "atmospheric", "dark",
    "cute", "creepy", "spooky", "spoopy", "scary", "cozy", "relaxing", "wholesome",
    "feel good", "funny", "comedy", "dark humor", "weird", "simple", "difficult",
    "fast-paced", "immersive", "creative", "mind-bending", "liminal space",
    "suspense", "thriller", "story rich", "narrative", "meaningful choices",
    "non-eucledian", "zero gravity", "shadows", "soundtoy", "visualization",
    "trashcore", "mashup",
}
PROCESS = {
    "open source", "sourcecode", "github", "moddable", "drm free", "kickstarter",
    "discord", "streaming", "job-system", "game design", "tutorial",
    "beginner friendly", "generator", "emulator", "modeling", "homebrew",
    "prototype", "instrument", "midi", "video", "internet", "voice acting",
}
POLICY = {
    "no ai", "ai generated", "artificial-intelligence", "non violent", "violent",
    "gore", "family friendly", "indie", "altgame", "horrible", "boring",
}
SCOPE = {
    "short", "endless", "episodic", "nonlinear", "multiple endings", "demake",
    "remake", "perma death", "high score", "score attack", "time attack",
    "real-time", "turn-based", "singleplayer", "multiplayer", "co-op", "pvp",
    "versus", "team-based", "deathmatch", "massively multiplayer", "classes",
    "upgrades", "secrets", "combos", "one-hit-kill", "lone-survivor", "traps",
    "hex based", "procedural generation", "physics", "gravity", "destruction",
    "explosions", "sandbox", "open world", "character customization", "loot",
    "crafting", "automation", "blocks", "jumping",
}
IP = {
    "five nights at freddy's", "undertale", "touhou",
    "minecraft", "doom", "gorilla tag", "pizza tower", "sprunki", "incredibox",
    "suika game", "wordle", "flappy bird", "backrooms", "siren head", "fangame",
    "tetris", "snake", "asteroids", "breakout", "minesweeper", "sharecart1000",
    "barfcade", "creepypasta", "cult classic",
}
#: The rule does not settle these, and the third state is kept rather than forced.
UNCLEAR = {
    "anime", "zine", "artgame", "memoir", "moe", "gender", "mental health",
    "coming of age", "magical realism", "slice of life", "period piece", "norway",
    "filipino", "celtic", "norse", "thanksgiving", "christmas", "halloween",
    "desktop pet", "food", "nature", "math", "astronomy", "ciphers",
    "educational", "experimental", "meme", "parody",
    "satire", "dreams", "time travel", "supernatural", "mythology", "folklore",
    "fairy tale", "alternate history", "urban", "mountains", "forest",
    "underwater", "sailing", "roadtrip", "railroad", "trains", "horses",
    "chicken", "frogs", "unicorns", "dinosaurs", "cats", "dogs", "animals",
    "slime", "tentacles", "skeletons", "ghosts", "vampire", "dragons", "wizards",
    "robots", "mechs", "aliens", "monsters", "superhero", "superpowers", "magic",
    "swords", "pirates", "ninja", "kung fu", "archery", "flying", "flight",
}

SUBKINDS = [("jam", None), ("engine", ENGINE), ("hardware", HARDWARE),
            ("input", INPUT_), ("aesthetic", AESTHETIC), ("process", PROCESS),
            ("policy", POLICY), ("scope", SCOPE), ("ip", IP)]


def classify(name):
    """Return (class, subkind). ``class`` is one of market, not_market, unclear."""
    s = html.unescape(name).strip().lower()
    if JAM.search(s):
        return "not_market", "jam"
    for label, members in SUBKINDS[1:]:
        if s in members:
            return "not_market", label
    if s in UNCLEAR:
        return "unclear", None
    return "market", None


def overlaps():
    """Any name in two sub-kind sets at once is a bug in the lists, not a judgement."""
    seen, dup = {}, []
    for label, members in SUBKINDS[1:]:
        for m in members:
            if m in seen:
                dup.append((m, seen[m], label))
            seen[m] = label
    for m in UNCLEAR:
        if m in seen:
            dup.append((m, seen[m], "unclear"))
    return dup


def census_names():
    """The games-scope tag names as the directory printed them, lowercased."""
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    return {r["name"].strip().lower() for r in census["tags"]
            if r["kind"] == "tag" and r["scope"] == "games"}


def dead_entries(names):
    """A list entry that matches nothing is not coverage, it is a flag that cannot fire.

    Three were found the first time this ran, and every one of them was a
    hand-typed name that had drifted from what the directory prints: an engine's
    name standing in for its jam, a truncated console name, and an escaped form
    left over from before the census stored names unescaped. All three were silent:
    the totals were right, the overlap guard was quiet, and the tag they were meant
    to catch fell through to the market side. This is 第 11 条 on the list itself,
    so it prints the entries rather than their count.
    """
    out = []
    for label, members in SUBKINDS[1:] + [("unclear", UNCLEAR)]:
        for m in sorted(members):
            if m not in names:
                out.append((label, m))
    return out


def selftest():
    bad = overlaps()
    print(f"overlap check on the lists as written: {len(bad)} duplicate(s)")
    for m, a, b in bad:
        print(f"  {m!r} is in both {a} and {b}")
    probes = [("Ludum Dare 42", "not_market", "jam"), ("Unity", "not_market", "engine"),
              ("Pixel Art", "not_market", "aesthetic"), ("Horror", "market", None),
              ("anime", "unclear", None)]
    for name, klass, sub in probes:
        got = classify(name)
        assert got == (klass, sub), f"{name}: expected {(klass, sub)}, got {got}"
    print(f"{len(probes)} probes pass")
    seeded = dict(ENGINE=set(ENGINE))
    ENGINE.add("horror")
    assert classify("Horror") == ("not_market", "engine"), "a seeded misfile did not fire"
    ENGINE.clear(); ENGINE.update(seeded["ENGINE"])
    assert classify("Horror") == ("market", None), "the seed was not backed out"
    print("seeded misfile fires and is backed out")

    names = census_names()
    dead = dead_entries(names)
    print(f"list entries matching nothing in the census: {len(dead)}")
    for label, m in dead:
        print(f"  {label}: {m!r} matches no tag the directory prints")
    ENGINE.add("an engine nobody has ever shipped")
    seeded = dead_entries(names)
    assert len(seeded) == len(dead) + 1, "a seeded dead entry did not get reported"
    ENGINE.discard("an engine nobody has ever shipped")
    assert len(dead_entries(names)) == len(dead), "the dead-entry seed was not backed out"
    print("seeded dead entry is reported and backed out")
    return 0 if not bad else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    dup = overlaps()
    if dup:
        print(f"STOP: {len(dup)} name(s) in two sub-kind lists at once; fix the lists first")
        for m, a, b in dup:
            print(f"  {m!r} in {a} and {b}")
        return 2

    dead = dead_entries(census_names())
    if dead:
        print(f"{len(dead)} list entry(ies) match nothing in the census; each is printed, "
              f"and none of them is coverage:")
        for label, m in dead:
            print(f"  {label}: {m!r}")

    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    rows = []
    for r in census["tags"]:
        if r["kind"] != "tag" or r["scope"] != "games":
            continue
        klass, sub = classify(r["name"])
        rows.append({"name": html.unescape(r["name"]), "slug": r["slug"],
                     "count": r["count"], "class": klass, "subkind": sub})
    rows.sort(key=lambda d: (d["class"], -d["count"], d["slug"]))

    by_class = Counter(r["class"] for r in rows)
    by_sub = Counter(r["subkind"] for r in rows if r["subkind"])
    thin = [r for r in rows if r["count"] < 1000]
    thin_class = Counter(r["class"] for r in thin)

    record = {
        "station": "B30-4",
        "what": "the split of the itch.io games-scope tag vocabulary, applied to names alone",
        "input": str(CENSUS.relative_to(ROOT)),
        "rule": ("market: names a kind a buyer substitutes within, and its size is set by "
                 "how many make that kind rather than by the price level. Everything else "
                 "is not a market tag, with a sub-kind recorded. unclear is the third state."),
        "prices_seen_when_classifying": False,
        "total": len(rows),
        "by_class": dict(sorted(by_class.items())),
        "by_subkind": dict(sorted(by_sub.items())),
        "thin_end_below_1000": {"n": len(thin), "by_class": dict(sorted(thin_class.items()))},
        "rows": rows,
        "diagnostic_only": True,
        "diagnostic_reason": ("A classification, not a reading. No price has been pulled on "
                              "this carrier and none entered this file."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")

    print(f"{len(rows)} games-scope tags: {dict(sorted(by_class.items()))}")
    print(f"non-market by sub-kind: {dict(sorted(by_sub.items()))}")
    print(f"below 1,000: n={len(thin)}, {dict(sorted(thin_class.items()))}")
    m = [r for r in rows if r["class"] == "market"]
    if m:
        lo = min(r["count"] for r in m)
        hi = max(r["count"] for r in m)
        print(f"market tags span {lo:,} to {hi:,}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
