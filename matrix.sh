#!/bin/bash
# Full benchmark matrix, strictly sequential, methods interleaved.
cd "$(dirname "$0")"
M="bo-pip bo-uv mx"
for r in 1 2; do for m in $M; do python3 bench.py $m cold "r$r" | tail -1; done; done
for r in 1 2 3; do for m in $M; do
  python3 bench.py $m warm "r$r" | tail -1
  python3 bench.py $m noop "r$r" | tail -1
done; done
echo MATRIX DONE
