#!/usr/bin/env python3
"""Summarise results.jsonl: per method/scenario median/min/max and phases."""

import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

B = Path(__file__).resolve().parent
LINE = re.compile(r"^\[\s*([0-9.]+)\] (.*)$")

MX_MARKERS = [
    ("mxenv", None),
    ("releaser + buildout2pip", "Install plone.releaser"),
    ("git sources", "Checkout project sources"),
    ("mxfiles", "Create project files"),
    ("packages", "Install python packages"),
    ("test, cookiecutter, instance", "Install zope-testrunner"),
]


def lines_of(log):
    out = []
    for raw in open(B / log, errors="replace"):
        m = LINE.match(raw)
        if m:
            out.append((float(m.group(1)), m.group(2)))
    return out


def phases(res):
    lines = lines_of(res["log"])
    total = res["total"]
    ph = {}
    if res["method"].startswith("bo"):
        start = total - res["steps"]["buildout"]
        if "bootstrap" in res["steps"]:
            ph["bootstrap"] = res["steps"]["bootstrap"]
        parts_at = next(
            (t for t, l in lines
             if t >= start and re.match(r"(Installing|Updating) [\w.-]+\.$", l)),
            total)
        ph["setup (ext, git, develop, recipes)"] = parts_at - start
        ph["parts"] = total - parts_at
    else:
        cuts = []
        for name, marker in MX_MARKERS:
            if marker is None:
                cuts.append((name, 0.0))
                continue
            t = next((t for t, l in lines if l.startswith(marker)), None)
            if t is not None:
                cuts.append((name, t))
        for (name, t), nxt in zip(cuts, cuts[1:] + [(None, total)]):
            ph[name] = nxt[1] - t
    return ph


def main():
    path = B / (sys.argv[1] if len(sys.argv) > 1 else "results.jsonl")
    rows = [json.loads(l) for l in open(path) if l.strip()]
    groups = defaultdict(list)
    for r in rows:
        if r["label"] == "prime":  # only fills the shared eggs-directory
            continue
        groups[(r["scenario"], r["method"])].append(r)
    summary = []
    for scen in ("cold", "warm", "shared", "noop"):
        for meth in ("bo-pip", "bo-uv", "mx"):
            rs = groups.get((scen, meth), [])
            if not rs:
                continue
            ok = [r for r in rs if r["ok"]]
            tot = [r["total"] for r in ok]
            phs = defaultdict(list)
            for r in ok:
                for k, v in phases(r).items():
                    phs[k].append(v)
            row = dict(
                scenario=scen, method=meth, n=len(ok), failed=len(rs) - len(ok),
                median=round(statistics.median(tot), 1) if tot else None,
                min=min(tot) if tot else None, max=max(tot) if tot else None,
                runs=tot,
                phases={k: round(statistics.median(v), 1) for k, v in phs.items()},
                ndists=ok[-1]["ndists"] if ok else None,
                install_mb=round(ok[-1]["install_bytes"] / 2**20) if ok else None,
                cache_mb=round(ok[-1]["cache_bytes"] / 2**20) if ok else None,
            )
            summary.append(row)
            print(f"{scen:5} {meth:7} n={row['n']} fail={row['failed']} "
                  f"median={row['median']}s runs={tot} dists={row['ndists']} "
                  f"install={row['install_mb']}MB cache={row['cache_mb']}MB")
            print(f"      phases: {row['phases']}")
    json.dump(summary, open(B / "summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
