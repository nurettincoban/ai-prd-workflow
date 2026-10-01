#!/usr/bin/env bash
# Seeds the empty run workspace with the v2.0 url-shortener artifacts.
# Runs only with `claude plugin eval --scaffold`.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/../../examples/url-shortener/before"
[ -f "$src/PRD.md" ] || { echo "fixture not found: $src/PRD.md" >&2; exit 1; }
# Copies a fixture file without carriage returns, so a Windows checkout cannot break line matches.
copy() { mkdir -p "$(dirname "$1")"; tr -d '\r' < "$src/$1" > "$1"; }
for f in PRD.md FEATURES.md; do copy "$f"; done
for f in "$src"/RFCs/*.md; do copy "RFCs/${f##*/}"; done
git init -q
git -c user.name=eval -c user.email=eval@example.invalid add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -qm "fixture"
# The user's edit: two new requirements in the earliest category, left uncommitted
awk '{ print } /^- Delete a short URL$/ { print "- Edit the destination of an existing short URL"; print "- Shorten up to 100 URLs in one request" }' PRD.md > PRD.md.new
mv PRD.md.new PRD.md
grep -q "Shorten up to 100 URLs" PRD.md || { echo "fixture changed: anchor line not found" >&2; exit 1; }
