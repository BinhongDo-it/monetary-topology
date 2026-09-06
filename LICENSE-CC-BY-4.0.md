# Documentation and results license

Copyright (c) 2026 Binhong Dong

The files listed below are licensed under the Creative Commons Attribution 4.0
International License (CC BY 4.0). They are not covered by the MIT License in
`LICENSE`, which covers the code.

Covered by CC BY 4.0:

    docs/
    results/
    figures/
    speedrun/
    RESULTS.md
    README.md
    data/SOURCES.md
    data/*.json
    data/*.csv
    data/**/*_manifest.json

Covered by MIT (see `LICENSE`):

    src/
    experiments/
    scripts/
    tests/
    data/*.py

Anything else in this repository that is this project's own work falls under one
of the two above according to what it is: source files under MIT, prose and
records under CC BY 4.0. The lists are meant to be exhaustive of what is here;
if something is not on them, that is an omission rather than a third category.
The two `.gitkeep` files under `data/` are empty and hold directories open; they
carry nothing to license.

**Nothing that came from anyone else is licensed by this file.** Retrieved
source data is not in this repository: `data/raw/` and the per-stage `raw/`
directories are excluded from git, and each source keeps its own terms, recorded
in `data/SOURCES.md`. Two third-party repositories cloned under `data/raw/` are
excluded on the same footing and keep whatever terms their upstreams set.

**What is on the lists under `data/` is not retrieved data.** It is the
retrieval scripts, the per-file provenance manifests, the choices this project
pinned by hand and recorded with what was measured to settle them, and two
tables this project collected and arranged itself. The account of each sits in
`data/SOURCES.md`.

## The license

To view a copy of this license, visit

    https://creativecommons.org/licenses/by/4.0/

and for the full legal code,

    https://creativecommons.org/licenses/by/4.0/legalcode

In short: you may share and adapt this material for any purpose, including
commercially, provided you give appropriate credit, link to the license, and
indicate whether changes were made. Credit may not be given in a way that
suggests endorsement.

## Attribution

Attribution must name the copyright holder and the work and link to the
license. `CITATION.cff` carries the canonical citation metadata. A short form:

    Binhong Dong, "monetary-topology", 2026.
    https://github.com/BinhongDo-it/monetary-topology
    Licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)

One further request, of scholarly practice rather than of this license: cite a
reading by its stage and criterion identifier and carry the scope limits
recorded beside it, because identifiers are stable and section numbers move.
