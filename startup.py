#!/usr/bin/env python3
"""Time a full Zope/Plone startup (all ZCML loaded) right after install
(bytecode as the installer left it) and a second time with bytecode written.

Run after the benchmark series, when nothing else is running.
"""

import json
import subprocess
import time
from pathlib import Path

B = Path(__file__).resolve().parent
SCRIPT = B / "startup_script.py"
SCRIPT.write_text('print("STARTUP OK", sorted(app.objectIds()))\n')

CMDS = {
    "bo-pip": ["bin/instance", "run", str(SCRIPT)],
    "bo-uv": ["bin/instance", "run", str(SCRIPT)],
    "mx": [".venv/bin/zconsole", "run", "instance/etc/zope.conf", str(SCRIPT)],
}


def main():
    out = {}
    for method, cmd in CMDS.items():
        proj = B / "runs" / method
        times = []
        for i in range(3):
            t0 = time.monotonic()
            p = subprocess.run(cmd, cwd=proj, capture_output=True, text=True)
            dt = time.monotonic() - t0
            ok = "STARTUP OK" in p.stdout
            if not ok:
                print(method, "failed:", (p.stdout + p.stderr)[-2000:])
            times.append(round(dt, 2))
        out[method] = times
        print(method, times, flush=True)
    json.dump(out, open(B / "startup.json", "w"), indent=1)


if __name__ == "__main__":
    main()
