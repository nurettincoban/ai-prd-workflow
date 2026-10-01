#!/usr/bin/env bash
# End-to-end tests for install.sh. Run from the repo root after ./install.sh --build:
#   bash scripts/test-install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="$(sed -n "/^COMMANDS='$/,/^'$/p" "$ROOT/install.sh" | grep -c '|')"
PASS=0

ok() { PASS=$((PASS + 1)); echo "ok   $*"; }
fail() { echo "FAIL $*" >&2; exit 1; }
fresh() { mktemp -d; }
count_skills() { find "$1" -mindepth 2 -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' '; }

# --- every generated skill is internally consistent ---------------------------
for f in "$ROOT"/skills/*/SKILL.md; do
    name="$(basename "$(dirname "$f")")"
    head -1 "$f" | grep -qx -- '---' || fail "$f: no frontmatter"
    grep -qx "name: $name" "$f" || fail "$f: name does not match its folder"
    desc="$(sed -n 's/^description: "\(.*\)"$/\1/p' "$f")"
    if [ -z "$desc" ] || [ "${#desc}" -gt 1024 ]; then fail "$f: description missing or longer than 1024 characters"; fi
    keys="$(awk 'NR==1{next} /^---$/{exit} /^[a-z-]+:/{sub(/:.*/,""); print}' "$f" | tr '\n' ' ')"
    for key in $keys; do
        case "$key" in name|description|license|compatibility|metadata|allowed-tools|argument-hint|context|agent) ;;
            *) fail "$f: unexpected frontmatter key '$key'" ;; esac
    done
    recorded="$(sed -n 's/^  checksum: "sha256:\([0-9a-f]*\)"$/\1/p' "$f")"
    actual="$(grep -v '^  checksum: ' "$f" | sha256sum | cut -d' ' -f1)"
    [ "$recorded" = "$actual" ] || fail "$f: checksum does not match its content"
done
[ "$(count_skills "$ROOT/skills")" -eq "$EXPECTED" ] || fail "skills/ has $(count_skills "$ROOT/skills") skills, install.sh lists $EXPECTED"
ok "$EXPECTED skills: frontmatter valid, names match folders, checksums verify"

# --- default install: both tool folders, with bundled scripts -----------------
t="$(fresh)"
"$ROOT/install.sh" "$t" > /dev/null
[ "$(count_skills "$t/.claude/skills")" -eq "$EXPECTED" ] || fail "default install: .claude/skills incomplete"
[ "$(count_skills "$t/.agents/skills")" -eq "$EXPECTED" ] || fail "default install: .agents/skills incomplete"
[ -f "$t/.agents/skills/workflow-status/scripts/trace-check.py" ] || fail "trace-check.py not bundled"
diff -r "$ROOT/skills" "$t/.claude/skills" > /dev/null || fail "installed skills differ from skills/"
ok "default install writes .claude/skills and .agents/skills, identical to skills/"

# --- idempotent -----------------------------------------------------------------
out="$("$ROOT/install.sh" "$t")"
echo "$out" | grep -q "0 added, 0 updated, 0 kept" || fail "second run changed something: $out"
ok "second run is a no-op"

# --- a file the user edited is kept, --force replaces it with a backup -----------
echo "my own note" >> "$t/.claude/skills/create-prd/SKILL.md"
out="$("$ROOT/install.sh" "$t" --claude)"
echo "$out" | grep -q "kept .*create-prd/SKILL.md" || fail "edited skill was not kept: $out"
grep -q "my own note" "$t/.claude/skills/create-prd/SKILL.md" || fail "edited skill was overwritten"
out="$("$ROOT/install.sh" "$t" --claude --force)"
echo "$out" | grep -q "replaced .*create-prd/SKILL.md" || fail "--force did not replace: $out"
backups=("$t"/.claude/skills/create-prd/SKILL.md.backup-*)
[ -e "${backups[0]}" ] || fail "--force saved no backup"
ok "edited skill kept without --force; replaced with a backup with --force"

# --- an unedited file from an older release is updated ---------------------------
f="$t/.agents/skills/verify-prd/SKILL.md"
sed -i.bak 's/^  version: "[^"]*"$/  version: "2.9.0"/' "$f" && rm -f "$f.bak"
sum="$(grep -v '^  checksum: ' "$f" | sha256sum | cut -d' ' -f1)"
sed -i.bak "s/^  checksum: \"sha256:[0-9a-f]*\"$/  checksum: \"sha256:$sum\"/" "$f" && rm -f "$f.bak"
out="$("$ROOT/install.sh" "$t" --agents)"
echo "$out" | grep -q "updated .*verify-prd/SKILL.md" || fail "older unedited skill not updated: $out"
cmp -s "$f" "$ROOT/skills/verify-prd/SKILL.md" || fail "updated skill differs from skills/"
ok "unedited skill from an older release is updated in place"

# --- v2.x command files: reported, and moved only with --remove-legacy -------------
t="$(fresh)"
mkdir -p "$t/.claude/commands" "$t/.cursor/commands"
printf -- '---\ndescription: x\n---\n\nYou are an experienced Product Manager with expertise...\n' > "$t/.claude/commands/create-prd.md"
printf 'You are an expert code reviewer...\n' > "$t/.cursor/commands/review-rfc.md"
printf 'My own command\n' > "$t/.claude/commands/deploy.md"
out="$("$ROOT/install.sh" "$t")"
echo "$out" | grep -q "still has v2 command files" || fail "legacy files not reported: $out"
[ -f "$t/.claude/commands/create-prd.md" ] || fail "legacy file moved without --remove-legacy"
"$ROOT/install.sh" "$t" --remove-legacy > /dev/null
[ ! -f "$t/.claude/commands/create-prd.md" ] || fail "--remove-legacy left .claude/commands/create-prd.md in place"
[ -f "$t/.claude/commands/.ai-prd-workflow-v2-backup/create-prd.md" ] || fail "--remove-legacy did not back up .claude/commands"
[ -f "$t/.cursor/commands/.ai-prd-workflow-v2-backup/review-rfc.md" ] || fail "--remove-legacy did not back up .cursor/commands"
[ -f "$t/.claude/commands/deploy.md" ] || fail "--remove-legacy touched a command that is not ours"
ok "v2 command files reported; --remove-legacy backs up ours and leaves others alone"

# --- the curl | bash path, served from file:// instead of GitHub --------------------
served="$(fresh)"
mkdir -p "$served/main"
cp -r "$ROOT/skills" "$served/main/"
t="$(fresh)"
url="file://$served"
if command -v cygpath > /dev/null 2>&1; then url="file:///$(cygpath -m "$served")"; fi
(cd "$t" && AI_PRD_WORKFLOW_RAW="$url" bash -s -- "$t" < "$ROOT/install.sh" > /dev/null)
if [ "$(count_skills "$t/.claude/skills")" -ne "$EXPECTED" ] || [ "$(count_skills "$t/.agents/skills")" -ne "$EXPECTED" ]; then fail "curl-path install incomplete"; fi
diff -r "$ROOT/skills" "$t/.agents/skills" > /dev/null || fail "curl-path skills differ from skills/"
ok "curl | bash path installs the same files"

# --- flags --------------------------------------------------------------------------
t="$(fresh)"
"$ROOT/install.sh" "$t" --claude > /dev/null
if [ ! -d "$t/.claude/skills" ] || [ -d "$t/.agents" ]; then fail "--claude installed more than Claude Code"; fi
t="$(fresh)"
"$ROOT/install.sh" "$t" --cursor > /dev/null 2>&1
if [ ! -d "$t/.agents/skills" ] || [ -d "$t/.claude" ]; then fail "--cursor did not map to .agents/skills"; fi
if "$ROOT/install.sh" "$t" --clade > /dev/null 2>&1; then fail "unknown flag accepted"; fi
if "$ROOT/install.sh" "$t/does-not-exist" > /dev/null 2>&1; then fail "missing target accepted"; fi
ok "--claude, --cursor alias, unknown flags and missing targets behave"

echo "test-install: all $PASS groups passed"
