#!/bin/bash
# Shared eggs-directory series for buildout, after matrix.sh.
cd "$(dirname "$0")"
until grep -q "MATRIX DONE" matrix.out; do sleep 20; done
for m in bo-pip bo-uv; do python3 bench.py $m shared prime | tail -1; done
for r in 1 2 3; do for m in bo-pip bo-uv; do python3 bench.py $m shared "r$r" | tail -1; done; done
echo MATRIX2 DONE
