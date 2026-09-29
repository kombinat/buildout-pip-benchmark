# Benchmark: buildout (pip) vs. buildout (`installer = uv`) vs. mxdev `make install`

Plone 6.2 core development setup ([buildout.coredev](https://github.com/plone/buildout.coredev) branch `6.2`),
comparing the new `installer = uv` mode of zc.buildout 5.3.0a1 (released 2026-09-27) with the classic pip mode
and with the mxdev/mxmake based `make install`.

## TL;DR

| Scenario | buildout (pip) | buildout (uv) | mxdev `make install` |
|---|---:|---:|---:|
| **Cold**: empty download caches, fresh project | 318 s | **75 s** | **52 s** |
| **Warm**: download caches filled, fresh project | 303 s | **46 s** | **29 s** |
| **Shared eggs**: filled shared `eggs-directory`, fresh project | 24 s | 23 s | n/a |
| **No-op rerun**: nothing changed | 10.4 s | 10.1 s | 0.3 s ¹ |

Median wall-clock time. ¹ `make install` only checks sentinel files, see [No-op reruns](#no-op-reruns).

- `installer = uv` makes a fresh buildout **4.2× faster cold** and **6.6× faster warm** than pip mode.
- mxdev `make install` is still **1.5× (cold) to 1.6× (warm) faster** than buildout with uv.
- With a filled shared eggs directory, the installer does not matter: both buildout modes take about 23 s.
- Out of the box, `installer = uv` **fails** on buildout.coredev 6.2 because it is stricter about picked versions
  than pip mode. See [Compatibility finding](#compatibility-finding-installer--uv-and-picked-versions).

## Environment

| | |
|---|---|
| Machine | Apple M2, 8 cores, 8 GB RAM, macOS 26 |
| Disk | Project, caches and eggs on an external USB disk (HFS+), which is also the normal working disk |
| Python | CPython 3.13.9 (uv-managed), same interpreter for all methods |
| buildout.coredev | `6.2` @ `c0b03f092` (identical to `origin/6.2`), exported with `git archive`, no `local.cfg` |
| zc.buildout | 5.3.0a1 for both buildout modes |
| uv | 0.12.19, both for buildout (pulled into the venv as a zc.buildout dependency) and for mxmake (global uv) |
| mxdev / mxmake | as installed by the repository's `Makefile` (`PYTHON_PACKAGE_INSTALLER=uv`) |
| Date | 2026-09-28/29 |

Because the disk is HFS+, uv cannot use APFS clones (reflinks) when installing from its cache.
On an APFS system disk the uv based numbers are probably lower.

## Method

Each run starts from a fresh copy of the exported repository. The 6 `auto-checkout` packages from `checkouts.cfg`
(`mockup`, `Plone`, `plone.app.locales`, `plone.app.upgrade`, `Products.CMFPlone`, `plone.restapi`) are cloned
once from GitHub on the branches from `sources.cfg` and copied into `src/` before every run, so the initial clone
is **not** measured. The git fetch/update of these checkouts that both tools do on every run **is** measured:
mr.developer runs with `always-checkout = force`, mxdev with `mxdev -f`.

Every method gets its own isolated caches (`PIP_CACHE_DIR`, `UV_CACHE_DIR`, cookiecutter dir). Runs were
strictly sequential, with the methods interleaved to spread network variance.

### Commands

**buildout (pip)** and **buildout (uv)**

```bash
python3.13 -m venv .venv
.venv/bin/pip install pip==26.2.1 setuptools==81.0.0 wheel==0.48.0 \
    horse-with-no-namespace==20260202.0 zc.buildout==5.3.0a1 uv==0.12.19
.venv/bin/buildout [buildout:installer=uv] \
    versions:zc.buildout=5.3.0a1 versions:uv=0.12.19 \
    versions:httpcore=1.0.9 versions:grpcio=1.81.0 \
    versions:grpcio-tools=1.81.0 versions:protobuf=6.33.6
```

The `versions:` overrides are the only change to the 6.2 configuration. `versions.cfg` pins zc.buildout 5.2.0,
and the other four pins are explained below. Both buildout modes get exactly the same overrides.
In the "shared eggs" scenario, `buildout:eggs-directory=<persistent dir>` is added.

**mxdev**

```bash
make install PRIMARY_PYTHON=/path/to/python3.13
```

This uses the unchanged `Makefile`, `mx.ini`, `mxsources.ini` and `mxcheckouts.ini` from 6.2.

### Scenarios

| Scenario | Download caches | Project dir | Runs |
|---|---|---|---:|
| Cold | deleted before the run | fresh | 2 |
| Warm | kept from earlier runs | fresh (new venv / new `eggs/`) | 3 |
| Shared eggs (buildout only) | kept | fresh, but `eggs-directory` points to a persistent, already filled directory, like a typical `~/.buildout/default.cfg` | 3 (after 1 priming run) |
| No-op rerun | kept | same dir, directly after each warm run | 3 |

## Results

### Wall-clock time, all runs

| Scenario | buildout (pip) | buildout (uv) | mxdev |
|---|---|---|---|
| Cold | 325.9, 309.6 | 72.4, 77.6 | 52.2, 50.9 |
| Warm | 313.4, 303.4, 299.2 | 46.0, 49.2, 43.8 | 28.5, 30.2, 26.4 |
| Shared eggs | 23.9, 23.7, 23.6 | 22.5, 22.9, 22.3 | n/a |
| No-op rerun | 10.6, 10.2, 10.4 | 10.2, 10.1, 9.8 | 0.21, 0.27, 0.31 |

Run-to-run variation stays within about ±8 %.

### Phase breakdown, median in seconds

**buildout**

| Phase | pip cold | uv cold | pip warm | uv warm | pip shared | uv shared |
|---|---:|---:|---:|---:|---:|---:|
| Bootstrap (venv + pip install zc.buildout) | 8.3 | 8.3 | 5.5 | 5.7 | 5.5 | 5.5 |
| Setup: extensions, mr.developer git update, develop eggs, recipes | 81.6 | 24.7 | 79.3 | 17.5 | 13.7 | 12.1 |
| Installing parts | 227.9 | 42.0 | 218.5 | 23.0 | 4.7 | 4.7 |
| **Total** | **317.7** | **75.0** | **303.4** | **46.0** | **23.7** | **22.5** |

**mxdev `make install`**

| Phase | cold | warm |
|---|---:|---:|
| mxenv (uv venv, mxdev, mxmake) | 3.6 | 1.8 |
| plone.releaser + `manage buildout2pip` / `versions2constraints` | 3.0 | 2.1 |
| git sources (`mxdev -f`) | 7.3 | 6.3 |
| mxfiles (`mxdev -n`) | 0.6 | 0.3 |
| packages (`uv pip install -r requirements-mxdev.txt`) | 31.9 | 14.0 |
| zope-testrunner, cookiecutter, zope instance | 5.2 | 3.8 |
| **Total** | **51.5** | **28.5** |

### Size

| | buildout (pip) | buildout (uv) | mxdev |
|---|---:|---:|---:|
| Distributions installed | 358 | 358 | 349 |
| Installed size (eggs + develop-eggs + venv, or venv) | 491 MB | 419 MB | 372 MB |
| Download cache after a run | 24 MB ² | 425 MB | 424 MB |

² In pip mode, buildout downloads distributions itself and hands local files to pip, so the pip cache stays almost
empty. Without `download-cache` or a shared `eggs-directory`, pip mode has nothing it can reuse, which is why
"warm" is barely faster than "cold" there.

The distribution sets are not identical: buildout also installs the `releaser`, `z3c_checkversions`,
`dependencies`, `zodbupdate`, `robot` etc. parts. Both cover Plone, the test dependencies and the dev tools.

### First Zope startup after install

A full `app` startup with all ZCML loaded, via `bin/instance run` (buildout) or `zconsole run` (mxdev).
The instance is started three times in a row.

| | 1st start | 2nd start | 3rd start |
|---|---:|---:|---:|
| buildout (pip) | 30.0 s | 4.8 s | 4.8 s |
| buildout (uv) | 25.3 s | 4.3 s | 4.1 s |
| mxdev | 25.0 s | 4.1 s | 3.8 s |

pip compiles bytecode at install time (4259 `.pyc` files for 4951 `.py` files), uv does not (143 `.pyc` files
for 8216 `.py` files), and neither does mxdev with uv. In an isolated test (buildout uv, all `__pycache__`
removed, database already created), the missing bytecode costs **about 5.5 s once** on the first start
(10.0 s vs. 4.5 s). The rest of the long first start most likely comes from creating the database and a cold
disk cache, which affects all three methods alike (not measured separately).

## Interpretation

1. **uv changes buildout a lot.** Resolution and installation go from ~310 s to ~75 s (cold) and ~46 s (warm).
   The per-requirement pip subprocess fan-out is the main cost in pip mode.
2. **mxdev is still faster than buildout with uv.** The gap comes from:
   - buildout's setup phase (extensions, mr.developer, develop eggs, recipes): 17–25 s vs. ~10 s for git and venv in mxdev;
   - buildout resolving and installing per part in several batches, while mxdev does one `uv pip install`;
   - buildout's pip-based bootstrap (~8 s cold) vs. `uv venv` in mxmake (~3.6 s).
3. **A shared eggs directory hides the installer.** When all eggs are already there, both buildout modes take about 23 s.
   Most of that is bootstrap and git updates.

### No-op reruns

These numbers are not comparable. `make install` only checks sentinel files (0.3 s) and does not touch git or
packages. buildout always updates the git checkouts (`always-checkout = force` in `checkouts.cfg`), re-evaluates
all parts and regenerates scripts (~10 s), and here the installer makes no difference.

## Compatibility finding: `installer = uv` and picked versions

With the unchanged 6.2 configuration (`allow-picked-versions = false`), **pip mode succeeds and uv mode fails**:

```text
While:
  Installing.
  Loading extensions.
  Getting distribution for 'mr.developer==3.0.0'.
Error: Picked: httpcore = 1.0.9

The `httpcore` egg does not have a version pin and `allow-picked-versions = false`.
```

After pinning `httpcore`, it fails again in the `test` part:

```text
While:
  Installing test.
  Getting distribution for 'plone.app.robotframework[test]==3.0.0'.
Error: Picked: grpcio = 1.81.0
```

Checking every installed distribution against `versions.cfg`, `versions-extra.cfg` and the Zope 6.2 version files
found exactly four unpinned distributions:

| Distribution | Why it is unpinned | pip mode | uv mode |
|---|---|---|---|
| `httpcore` | Dependency of the `plone.versioncheck` extension (via `httpx`) | accepted | "Picked" error |
| `grpcio` | Deliberately unpinned in 6.2, exact `==` pin in `robotframework-browser` metadata (see `[versionannotations]`) | accepted | "Picked" error |
| `grpcio-tools` | same | accepted | "Picked" error |
| `protobuf` | same | accepted | "Picked" error |

So there are two behaviour differences between the modes:

- pip mode does not enforce `allow-picked-versions` for the dependencies of buildout **extensions**, uv mode does;
- pip mode does not treat a version fixed by an **exact `==` pin in a dependency's metadata** as "picked", uv mode does.

The benchmark works around this by pinning the four distributions to the versions pip mode picks, in both modes.

## Reproducing

Step-by-step instructions: see [README.md](README.md#running-the-benchmarks).

Requirements: git, make, uv ≥ 0.12.11 on `PATH` (for mxmake), and CPython 3.13. Set `BENCH_PYTHON` to the
interpreter path, otherwise `python3.13` from `PATH` is used.

```bash
./setup.sh 6.2      # export buildout.coredev and clone the checkouts
./matrix.sh         # cold, warm and noop series
./matrix2.sh        # shared eggs series (waits for matrix.sh)
python3 analyze.py  # summary
python3 startup.py  # first Zope startup
```

| File | Purpose |
|---|---|
| `setup.sh [REF]` | exports buildout.coredev at `REF` (default `6.2`) into `export/` and clones the auto-checkout packages into `srcref/` |
| `bench.py METHOD SCENARIO [LABEL]` | one run; `METHOD` is `bo-pip`, `bo-uv` or `mx`; `SCENARIO` is `cold`, `warm`, `shared` or `noop` |
| `matrix.sh` | cold ×2, then warm + noop ×3, methods interleaved |
| `matrix2.sh` | shared eggs series for both buildout modes |
| `analyze.py` | medians and phase breakdown from `results.jsonl`; writes `summary.json` |
| `startup.py` | first and second Zope startup |
| `results.jsonl`, `summary.txt`, `startup.json`, `logs/` | raw data and timestamped logs of every run |

In the logs, local paths are replaced by placeholders: `<bench>` is the benchmark directory and
`<python3.13>` is the interpreter passed as `BENCH_PYTHON`.
