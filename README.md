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

Full write-up: [RESULTS.md](RESULTS.md)

## Running the benchmarks

### Requirements

- macOS or Linux with network access to GitHub and PyPI
- `git` and `make`
- **bash ≥ 4.4** as `bash` on `PATH`: the mxmake `Makefile` uses `-O inherit_errexit`.
  macOS ships bash 3.2, so install bash with Homebrew there.
- **uv ≥ 0.12.11** as `uv` on `PATH`. mxmake uses the global uv, and zc.buildout 5.3.0a1 requires at
  least this version. For comparable numbers, use the version pinned in `bench.py` (`UV_VERSION`, 0.12.19).
- **CPython 3.13** for the projects under test. Point `BENCH_PYTHON` to it, otherwise `python3.13` from `PATH` is used:

  ```bash
  export BENCH_PYTHON=$(uv python find 3.13)
  ```

- `python3` (3.9 or newer) to run the harness scripts themselves
- About **6 GB** of free disk space and **1.5 to 2 hours** for the full series.
  Every fresh run copies about 1 GB of git checkouts, so a slow disk adds a lot of wall time
  (this copy is not part of the measured time).

### 1. Prepare

```bash
git clone git@github.com:kombinat/buildout-pip-benchmark.git
cd buildout-pip-benchmark
./setup.sh 6.2
```

`setup.sh [REF]` exports buildout.coredev at `REF` (branch or commit, default `6.2`) into `export/` and writes the
exact commit to `export.ref`. It also clones the six `auto-checkout` packages once into `srcref/`, on the branches
from `sources.cfg`.

The repository contains the published results. To start a new series with empty results, move them away first:

```bash
mkdir -p published && git mv results.jsonl summary.* startup.json matrix*.out published/
```

### 2. Try a single run (optional)

```bash
python3 bench.py bo-uv cold test
```

`bench.py METHOD SCENARIO [LABEL]` runs one benchmark and appends one JSON line to `results.jsonl`.
The full output, with a timestamp on every line, goes to `logs/<stamp>-<method>-<scenario>.log`.

| `METHOD` | What runs |
|---|---|
| `bo-pip` | venv + `pip install zc.buildout==5.3.0a1`, then `buildout` in pip mode |
| `bo-uv` | same, then `buildout buildout:installer=uv` |
| `mx` | `make install` with the repository's mxmake `Makefile` |

| `SCENARIO` | Download caches | Project directory |
|---|---|---|
| `cold` | `caches/<method>/` is deleted first | fresh copy of `export/` plus `srcref/` in `runs/<method>/` |
| `warm` | kept | fresh copy |
| `shared` | kept; buildout only, uses a persistent `caches/<method>/eggs` as `eggs-directory` | fresh copy |
| `noop` | kept | existing `runs/<method>/`, nothing deleted |

Every method has its own `PIP_CACHE_DIR`, `UV_CACHE_DIR` and cookiecutter directory below `caches/<method>/`,
so your global pip and uv caches are not used.

Exit code 0 means the run succeeded: `bin/instance` exists (buildout) or `instance/etc/zope.conf` exists (mxdev).

### 3. Run the series

Run the series on an otherwise idle machine and never run two benchmarks at the same time.
`matrix2.sh` waits until `matrix.out` contains `MATRIX DONE`, so start both with their output redirected
exactly like this:

```bash
nohup ./matrix.sh  > matrix.out  2>&1 &
nohup ./matrix2.sh > matrix2.out 2>&1 &
tail -f matrix.out matrix2.out
```

- `matrix.sh`: 2 cold rounds, then 3 warm rounds each followed by a noop rerun. Methods are interleaved to spread network variance.
- `matrix2.sh`: shared eggs series for both buildout modes. One `prime` run per mode fills the eggs directory
  and is excluded from the analysis, then 3 counted rounds follow.

### 4. Analyse

```bash
python3 analyze.py                # reads results.jsonl
python3 analyze.py other.jsonl    # or any other results file
```

This prints median, min/max, all runs and a phase breakdown per scenario and method, derived from the log
timestamps. It also writes `summary.json`. Keep the text output with `python3 analyze.py > summary.txt`.

### 5. First Zope startup (optional)

```bash
python3 startup.py
```

Starts the instance left in `runs/<method>/` three times (full startup with all ZCML, via `bin/instance run`
or `zconsole run`) and writes the times to `startup.json`. Run it directly after the series, before anything
imports the installed packages. The first start then reflects the bytecode state the installer left behind.

### Adapting to other versions

- zc.buildout and uv versions: `BUILDOUT_VERSION` and `UV_VERSION` in `bench.py`.
- The bootstrap pins (pip, setuptools, wheel, horse-with-no-namespace) in `BOOTSTRAP` and the extra
  `versions:` pins in `BUILDOUT_ARGS` in `bench.py` match buildout.coredev 6.2 as of 2026-09-28.
  With another `REF`, check them against `requirements.txt` and `versions.cfg`. With `installer = uv`,
  `allow-picked-versions = false` also rejects dependencies that pip mode tolerates (see RESULTS.md).
- The checkout list and branches in `setup.sh` follow `checkouts.cfg` and `sources.cfg` of 6.2.

### Cleaning up

```bash
rm -rf runs caches          # installed projects and caches (several GB)
rm -rf export srcref        # recreated by setup.sh
```

In the committed logs, local paths are replaced by placeholders: `<bench>` is the benchmark directory and
`<python3.13>` is the interpreter passed as `BENCH_PYTHON`. New logs contain the real paths.
