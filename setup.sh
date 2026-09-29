#!/bin/bash
# Prepare the benchmark directory: export buildout.coredev and clone the
# auto-checkout packages once (copied into src/ before every run).
# Usage: ./setup.sh [BRANCH_OR_COMMIT]   (default: 6.2)
set -euo pipefail
cd "$(dirname "$0")"
REF=${1:-6.2}
mkdir -p export srcref caches runs logs
git clone -q --depth 1 --branch "$REF" https://github.com/plone/buildout.coredev.git coredev.tmp 2>/dev/null \
  || { git clone -q https://github.com/plone/buildout.coredev.git coredev.tmp; git -C coredev.tmp checkout -q "$REF"; }
git -C coredev.tmp log -1 --format='buildout.coredev %H' > export.ref
git -C coredev.tmp archive HEAD | tar -x -C export
rm -rf coredev.tmp
cat export.ref
# Branches from sources.cfg for the packages in checkouts.cfg (6.2 as of 2026-09-28).
cd srcref
git clone -q --branch 5.6.x  https://github.com/plone/mockup.git mockup &
git clone -q --branch 6.2.x  https://github.com/plone/Plone.git Plone &
git clone -q --branch master https://github.com/collective/plone.app.locales.git plone.app.locales &
git clone -q --branch master https://github.com/plone/plone.app.upgrade.git plone.app.upgrade &
git clone -q --branch main   https://github.com/plone/plone.restapi.git plone.restapi &
git clone -q --branch 6.2.x  https://github.com/plone/Products.CMFPlone.git Products.CMFPlone &
wait
echo "done; now run ./matrix.sh (and ./matrix2.sh), then ./analyze.py"
