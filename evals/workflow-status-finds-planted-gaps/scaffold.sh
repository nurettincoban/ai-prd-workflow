#!/usr/bin/env bash
# Seeds the empty run workspace with the v2.0 url-shortener artifacts.
# Runs only with `claude plugin eval --scaffold`.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/../../examples/url-shortener/before"
[ -f "$src/PRD.md" ] || { echo "fixture not found: $src/PRD.md" >&2; exit 1; }
# Copies a fixture file without carriage returns, so a Windows checkout cannot break line matches.
copy() { mkdir -p "$(dirname "$1")"; tr -d '\r' < "$src/$1" > "$1"; }
for f in PRD.md FEATURES.md RULES.md; do copy "$f"; done
for f in "$src"/RFCs/*.md; do copy "RFCs/${f##*/}"; done
git init -q
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -qm "fixture"
