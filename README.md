# buildout (pip) vs. buildout (installer = uv) vs. mxdev `make install`

buildout.coredev 6.2 @ c0b03f092 (git archive, no local.cfg), 2026-09-28/29.
Apple M2, 8 GB, macOS 26, project on external USB disk (HFS+), Python 3.13.9,
zc.buildout 5.3.0a1, uv 0.12.19 (same binary version for buildout and mxmake).
Same 6 checkouts (checkouts.cfg) pre-copied into src/ for every method; git
fetch/update of those checkouts is part of the measured time.

Median wall time in seconds (runs in brackets):

| scenario | buildout pip | buildout uv | mxdev make install |
|---|---|---|---|
| cold: empty download caches, fresh project | 318 (326, 310) | 75 (72, 78) | 52 (52, 51) |
| warm: download caches filled, fresh project | 303 (313, 303, 299) | 46 (46, 49, 44) | 29 (29, 30, 26) |
| shared: filled shared eggs-directory, fresh project | 24 (24, 24, 24) | 23 (23, 23, 22) | n/a |
| noop: rerun, nothing changed | 10.4 | 10.1 | 0.3 (sentinels only) |

Distributions: buildout 358 (both modes), mxdev 349.
Full Zope startup after install (1st / 2nd): pip 30.0 / 4.8, uv 25.3 / 4.3,
mxdev 25.0 / 4.1. Missing bytecode alone (uv mode, __pycache__ removed): +5.5 s once.

Pins added on the buildout command line for both modes (unpinned in 6.2 and
tolerated by pip mode, rejected by installer=uv with allow-picked-versions=false):
httpcore=1.0.9, grpcio=1.81.0, grpcio-tools=1.81.0, protobuf=6.33.6.

Files: bench.py (one run), matrix.sh / matrix2.sh (series), analyze.py
(summary, phases), startup.py, results.jsonl, summary.txt, logs/.

Full write-up: RESULTS.md
