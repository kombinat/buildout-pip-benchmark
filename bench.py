#!/usr/bin/env python3
"""Benchmark buildout (pip), buildout (uv) and mxdev/mxmake `make install`
on buildout.coredev 6.2.

Usage: bench.py METHOD SCENARIO [LABEL]
  METHOD   bo-pip | bo-uv | mx
  SCENARIO cold   empty download caches, fresh project dir
           warm   caches kept from earlier runs, fresh project dir
           noop   rerun in the existing project dir
           shared (buildout only) fresh project dir, persistent shared
                  eggs-directory as configured in ~/.buildout/default.cfg

Every output line is timestamped so phases can be derived afterwards.
One JSON line per run is appended to results.jsonl.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

B = Path(__file__).resolve().parent
# Interpreter for all methods (the published results used a uv-managed CPython 3.13.9).
PY = os.environ.get("BENCH_PYTHON") or shutil.which("python3.13")
BUILDOUT_VERSION = "5.3.0a1"
UV_VERSION = "0.12.19"
BOOTSTRAP = [
    "pip==26.2.1",
    "setuptools==81.0.0",
    "wheel==0.48.0",
    "horse-with-no-namespace==20260202.0",
    f"zc.buildout=={BUILDOUT_VERSION}",
    f"uv=={UV_VERSION}",
]
BUILDOUT_ARGS = [
    f"versions:zc.buildout={BUILDOUT_VERSION}",
    f"versions:uv={UV_VERSION}",
    # The only dists 6.2 (incl. Zope 6.2 pins) leaves unpinned. pip mode
    # accepts them (httpcore: extension dependency; grpcio*/protobuf: exact
    # == pins in robotframework-browser metadata), installer=uv fails on
    # allow-picked-versions. Pinned to what pip mode picks, for both modes.
    "versions:httpcore=1.0.9",
    "versions:grpcio=1.81.0",
    "versions:grpcio-tools=1.81.0",
    "versions:protobuf=6.33.6",
]


def env_for(method):
    cache = B / "caches" / method
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("UV_", "PIP_", "VIRTUAL_ENV", "PYTHON")):
            del env[k]
    env.update(
        PIP_CACHE_DIR=str(cache / "pip"),
        UV_CACHE_DIR=str(cache / "uv"),
        PIP_DISABLE_PIP_VERSION_CHECK="1",
        COOKIECUTTERS_DIR=str(cache / "cookiecutters"),
    )
    return env


def run(cmd, cwd, env, log, lines):
    t0 = time.monotonic()
    log.write(f"\n$ {' '.join(cmd)}\n")
    p = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    for line in p.stdout:
        t = time.monotonic()
        log.write(f"[{t - T0:8.2f}] {line}")
        lines.append((t - T0, line.rstrip()))
    p.wait()
    dt = time.monotonic() - t0
    log.write(f"# exit {p.returncode} after {dt:.2f}s\n")
    log.flush()
    return p.returncode, dt


def du(path):
    if not path.exists():
        return 0
    out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True).stdout
    return int(out.split()[0]) * 1024


def fresh_project(proj):
    if proj.exists():
        subprocess.run(["rm", "-rf", str(proj)], check=True)
    subprocess.run(["cp", "-R", str(B / "export"), str(proj)], check=True)
    (proj / "src").mkdir(exist_ok=True)
    for d in (B / "srcref").iterdir():
        subprocess.run(["cp", "-R", str(d), str(proj / "src" / d.name)], check=True)


def main():
    global T0
    method, scenario = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else ""
    proj = B / "runs" / method
    env = env_for(method)
    cache = B / "caches" / method

    if scenario == "cold" and cache.exists():
        shutil.rmtree(cache)
    cache.mkdir(parents=True, exist_ok=True)
    if scenario in ("cold", "warm", "shared"):
        fresh_project(proj)
    elif not proj.exists():
        sys.exit("noop needs an existing project dir")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    logpath = B / "logs" / f"{stamp}-{method}-{scenario}.log"
    lines = []
    steps = {}
    T0 = time.monotonic()
    rc = 0
    with open(logpath, "w") as log:
        if method.startswith("bo"):
            extra = ["buildout:installer=uv"] if method == "bo-uv" else []
            if scenario == "shared":
                extra.append(f"buildout:eggs-directory={cache / 'eggs'}")
            if scenario != "noop":
                rc, steps["bootstrap"] = run(
                    [PY, "-m", "venv", ".venv"], proj, env, log, lines)
                if rc == 0:
                    rc, dt = run([".venv/bin/pip", "install", *BOOTSTRAP],
                                 proj, env, log, lines)
                    steps["bootstrap"] += dt
                buildout = ".venv/bin/buildout"
            else:
                buildout = "bin/buildout"
            if rc == 0:
                rc, steps["buildout"] = run(
                    [buildout, *extra, *BUILDOUT_ARGS], proj, env, log, lines)
        else:
            rc, steps["make install"] = run(
                ["make", "install", f"PRIMARY_PYTHON={PY}"], proj, env, log, lines)
    total = time.monotonic() - T0

    # size / count of what got installed
    if method.startswith("bo"):
        eggs = cache / "eggs" if scenario == "shared" else proj / "eggs"
        ndists = len(list(eggs.glob("v5/*.egg"))) + len(list((proj / "develop-eggs").glob("*.egg-link")))
        size = du(eggs) + du(proj / "develop-eggs") + du(proj / ".venv")
        ok = (proj / "bin" / "instance").exists()
    else:
        freeze = subprocess.run(
            ["uv", "pip", "freeze", "--python", str(proj / ".venv/bin/python")],
            capture_output=True, text=True, env=env).stdout.splitlines()
        ndists = len([x for x in freeze if x.strip()])
        size = du(proj / ".venv")
        ok = (proj / "instance" / "etc" / "zope.conf").exists()

    res = dict(
        method=method, scenario=scenario, label=label, stamp=stamp,
        rc=rc, ok=ok and rc == 0, total=round(total, 2),
        steps={k: round(v, 2) for k, v in steps.items()},
        ndists=ndists, install_bytes=size, cache_bytes=du(cache),
        log=str(logpath.relative_to(B)),
    )
    with open(B / "results.jsonl", "a") as f:
        f.write(json.dumps(res) + "\n")
    print(json.dumps(res))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
