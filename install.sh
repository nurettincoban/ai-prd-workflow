#!/usr/bin/env bash
#
# Install the ai-prd-workflow commands into a project as Agent Skills.
#
#   --claude   Claude Code                                  -> .claude/skills/<name>/SKILL.md
#   --agents   Codex, GitHub Copilot, Cursor, Gemini CLI,   -> .agents/skills/<name>/SKILL.md
#              OpenCode, Devin
#   --all      both (the default)
#
# Usage:
#   ./install.sh [target-project-dir] [--claude] [--agents] [--force] [--ref <tag>] [--remove-legacy]
#   ./install.sh --build     maintainers: regenerate skills/ in this repo from the prompt sources
#
# Without cloning the repo (pin a release by replacing main with a tag and adding --ref <tag>):
#   curl -fsSL https://raw.githubusercontent.com/nurettincoban/ai-prd-workflow/main/install.sh | bash -s -- /path/to/project
#
# Files you have edited are never overwritten silently: every generated SKILL.md carries a
# checksum, a file whose checksum no longer matches is kept, and --force replaces it after
# saving a backup.

set -euo pipefail

VERSION="3.0.0"
REPO_URL="https://github.com/nurettincoban/ai-prd-workflow"
# Overridable so the curl path can be tested without the network (file:// works).
RAW_BASE="${AI_PRD_WORKFLOW_RAW:-https://raw.githubusercontent.com/nurettincoban/ai-prd-workflow}"

SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
if [ -n "$SCRIPT_SOURCE" ] && [ -f "$SCRIPT_SOURCE" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
else
    SCRIPT_DIR=""
fi

# name|source prompt|description|argument hint|options
COMMANDS='
create-prd|interactive-prd-creation-prompt.md|Interview the user about a product idea and write PRD.md. Use at the start of a new project, before features, rules or RFCs exist.||
document-existing|document-existing-prompt.md|Document an existing codebase as PRD.md, FEATURES.md and RULES.md, so new work is planned against the code as it is. Use instead of create-prd when the code already exists.||
verify-prd|prd-comprehensive-verification-prompt.md|Review PRD.md for gaps, contradictions and unverifiable claims, write an improved PRD.md and record the findings in PRD-REVIEW.md.||
extract-features|prd-to-features-prompt.md|Turn PRD.md into FEATURES.md: permanent feature IDs, MoSCoW priorities, acceptance criteria and the PRD requirement each feature comes from.||
generate-rules|prd-to-rules-prompt.md|Write RULES.md, the project standards the AI must follow, with registry-verified dependency versions and permanent rule IDs.||
generate-rfcs|prd-to-rfcs-prompt.md|Break the PRD into sequenced implementation RFCs under RFCs/ with an RFCS.md index, then cold-read each RFC for gaps.||
test-strategy|testing-strategy-prompt.md|Write TEST-STRATEGY.md, a test plan per RFC, before the tests are written.||
implement-rfc|implementation-prompt-template.md|Implement one RFC: check its predecessors, present a plan for approval, write the code, then demonstrate every acceptance criterion.|<rfc-id>|
review-rfc|code-review-prompt.md|Review an implemented RFC in a fresh context against its acceptance criteria, RULES.md and the test plan, and save the review to reviews/.|<rfc-id>|fork
manage-changes|prd-change-management-prompt.md|Assess a requirement change mid-project against the rules and past decisions, then update every affected artifact together.||
workflow-status|workflow-status-prompt.md|Report which workflow artifacts exist, which RFCs are implemented and reviewed, what has drifted, and the next step.||
'

# shellcheck disable=SC2016  # $ARGUMENTS is a literal placeholder for the AI tool to substitute
ARG_PREAMBLE='Target RFC ID: "$ARGUMENTS" -- if that still reads as a literal placeholder, use the RFC ID from my message instead. Substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.'

die() { echo "Error: $*" >&2; exit 1; }

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum | cut -d' ' -f1
    else shasum -a 256 | cut -d' ' -f1
    fi
}

# Checksum of a generated SKILL.md: every byte except the checksum line itself, CRs ignored.
checksum_of() { tr -d '\r' < "$1" | grep -v '^  checksum: ' | sha256; }
recorded_checksum() { tr -d '\r' < "$1" | sed -n 's/^  checksum: "sha256:\([0-9a-f]*\)"$/\1/p'; }

yaml_quote() { printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"; }

usage() {
    cat <<EOF
Install the ai-prd-workflow commands into a project as Agent Skills (v$VERSION).

Usage: ./install.sh [target-project-dir] [options]

  --claude          Claude Code: .claude/skills/
  --agents          Codex, GitHub Copilot, Cursor, Gemini CLI, OpenCode, Devin: .agents/skills/
  --all             Both (default)
  --force           Replace skills you have edited (a backup is saved first)
  --ref <tag>       Install a specific release, e.g. --ref v$VERSION (skills ship from v3.0.0)
  --remove-legacy   Move command files left by v2.x installs into a backup folder
  --build           Maintainers: regenerate skills/ in this repository from the prompt sources

Claude Code users can install the plugin instead:
  /plugin marketplace add nurettincoban/ai-prd-workflow
  /plugin install prd-workflow@ai-prd-workflow
EOF
}

TARGET="."
TOOLS=""
FORCE=0
REF=""
REMOVE_LEGACY=0
BUILD=0
while [ $# -gt 0 ]; do
    case "$1" in
        --claude) TOOLS="$TOOLS claude" ;;
        --agents) TOOLS="$TOOLS agents" ;;
        --all) TOOLS="claude agents" ;;
        --cursor|--gemini|--opencode|--windsurf)
            echo "Note: $1 now installs Agent Skills into .agents/skills/, which that tool reads." >&2
            TOOLS="$TOOLS agents" ;;
        --force) FORCE=1 ;;
        --ref)
            [ $# -ge 2 ] || die "--ref needs a tag, e.g. --ref v$VERSION"
            REF="$2"; shift ;;
        --remove-legacy) REMOVE_LEGACY=1 ;;
        --build) BUILD=1 ;;
        --help|-h) usage; exit 0 ;;
        --*) die "unknown option '$1' (see --help)" ;;
        *) TARGET="$1" ;;
    esac
    shift
done
[ -n "$TOOLS" ] || TOOLS="claude agents"

# ------------------------------------------------------------------ build
# Generates skills/<name>/SKILL.md from the prompt sources. Only maintainers run this;
# installs copy the generated files, so every channel ships byte-identical skills.
render_skill() {
    local name="$1" src="$2" desc="$3" arghint="$4" options="$5"
    echo "---"
    echo "name: $name"
    echo "description: $(yaml_quote "$desc")"
    if [ -n "$arghint" ]; then echo "argument-hint: $(yaml_quote "$arghint")"; fi
    if [ "$options" = "fork" ]; then
        echo "context: fork"
        echo "agent: general-purpose"
    fi
    echo "metadata:"
    echo "  source: \"$REPO_URL\""
    echo "  version: \"$VERSION\""
    echo "---"
    echo ""
    if [ -n "$arghint" ]; then
        echo "$ARG_PREAMBLE"
        echo ""
    fi
    tr -d '\r' < "$SCRIPT_DIR/$src"
}

build_skills() {
    [ -n "$SCRIPT_DIR" ] || die "--build only works from a clone of the repository"
    local out="$SCRIPT_DIR/skills" tmp sum name src desc arghint options
    rm -rf "$out"
    mkdir -p "$out"
    while IFS='|' read -r name src desc arghint options; do
        [ -n "$name" ] || continue
        mkdir -p "$out/$name"
        tmp="$out/$name/SKILL.md.tmp"
        render_skill "$name" "$src" "$desc" "$arghint" "$options" > "$tmp"
        sum="$(sha256 < "$tmp")"
        # The checksum goes right after the version line; checksum_of() skips that one line.
        awk -v line="  checksum: \"sha256:$sum\"" '{ print } /^  version: "/ && !done { print line; done = 1 }' "$tmp" > "$out/$name/SKILL.md"
        rm "$tmp"
        if grep -q 'trace-check.py' "$out/$name/SKILL.md"; then
            mkdir -p "$out/$name/scripts"
            tr -d '\r' < "$SCRIPT_DIR/scripts/trace-check.py" > "$out/$name/scripts/trace-check.py"
        fi
        echo "  skills/$name/"
    done <<< "$COMMANDS"
}

if [ "$BUILD" = 1 ]; then
    echo "Building skills/ (v$VERSION):"
    build_skills
    exit 0
fi

# ---------------------------------------------------------------- install
[ -d "$TARGET" ] || die "target directory '$TARGET' does not exist."

# fetch <path in the repo>: the file from this copy, from a git ref of this clone, or downloaded
fetch() {
    local path="$1"
    if [ -n "$SCRIPT_DIR" ] && [ -z "$REF" ]; then
        cat "$SCRIPT_DIR/$path" 2>/dev/null
    elif [ -n "$SCRIPT_DIR" ] && git -C "$SCRIPT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
        git -C "$SCRIPT_DIR" show "$REF:$path" 2>/dev/null
    else
        curl -fsSL "$RAW_BASE/${REF:-main}/$path"
    fi
}

# Stage every skill once, so each tool folder gets identical files.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
while IFS='|' read -r name _; do
    [ -n "$name" ] || continue
    mkdir -p "$STAGE/$name"
    fetch "skills/$name/SKILL.md" > "$STAGE/$name/SKILL.md" \
        || die "could not fetch skills/$name/SKILL.md${REF:+ at $REF} (skills ship from v3.0.0)"
    if grep -q 'trace-check.py' "$STAGE/$name/SKILL.md"; then
        mkdir -p "$STAGE/$name/scripts"
        fetch "skills/$name/scripts/trace-check.py" > "$STAGE/$name/scripts/trace-check.py" \
            || die "could not fetch skills/$name/scripts/trace-check.py"
    fi
done <<< "$COMMANDS"

ADDED=0; UPDATED=0; CURRENT=0; KEPT=0

install_skill() {
    local name="$1" dest="$2" out="$2/SKILL.md" recorded actual
    if [ -f "$out" ]; then
        if [ "$(tr -d '\r' < "$out")" = "$(tr -d '\r' < "$STAGE/$name/SKILL.md")" ]; then
            CURRENT=$((CURRENT + 1))
            return 0
        fi
        recorded="$(recorded_checksum "$out")"
        actual="$(checksum_of "$out")"
        if [ -z "$recorded" ] || [ "$recorded" != "$actual" ]; then
            if [ "$FORCE" != 1 ]; then
                echo "  kept     $out  (edited locally -- rerun with --force to replace it)"
                KEPT=$((KEPT + 1))
                return 0
            fi
            cp "$out" "$out.backup-$(date +%Y%m%d%H%M%S)"
            echo "  replaced $out  (backup saved beside it)"
        else
            echo "  updated  $out"
        fi
        UPDATED=$((UPDATED + 1))
    else
        echo "  added    $out"
        ADDED=$((ADDED + 1))
    fi
    mkdir -p "$dest"
    cp "$STAGE/$name/SKILL.md" "$out"
    if [ -d "$STAGE/$name/scripts" ]; then
        mkdir -p "$dest/scripts"
        cp "$STAGE/$name/scripts/"* "$dest/scripts/"
    fi
}

# v2.x installed plain command files under these names; skills with the same names replace them.
LEGACY_MARKER='You are (an experienced Product Manager|an expert|a senior software developer|guiding a project through)'
handle_legacy() {
    local dir="$TARGET/$1" found="" name file
    [ -d "$dir" ] || return 0
    for name in create-prd verify-prd extract-features generate-rules generate-rfcs implement-rfc review-rfc test-strategy manage-changes workflow-status; do
        file="$dir/$name.md"
        if [ -f "$file" ] && grep -Eq "$LEGACY_MARKER" "$file"; then
            if [ "$REMOVE_LEGACY" = 1 ]; then
                mkdir -p "$dir/.ai-prd-workflow-v2-backup"
                mv "$file" "$dir/.ai-prd-workflow-v2-backup/"
            fi
            found="$found $name"
        fi
    done
    [ -n "$found" ] || return 0
    if [ "$REMOVE_LEGACY" = 1 ]; then
        echo "Moved v2 command files from $1/ to $1/.ai-prd-workflow-v2-backup/:$found"
    else
        echo "Note: $1/ still has v2 command files with the same names:$found"
        echo "      Rerun with --remove-legacy to move them into a backup folder."
    fi
}

for tool in claude agents; do
    case " $TOOLS " in *" $tool "*) ;; *) continue ;; esac
    case "$tool" in
        claude) dir=".claude/skills"; label="Claude Code" ;;
        agents) dir=".agents/skills"; label="Codex, Copilot, Cursor, Gemini CLI, OpenCode, Devin" ;;
    esac
    echo "$label -> $dir/"
    while IFS='|' read -r name _; do
        [ -n "$name" ] || continue
        install_skill "$name" "$TARGET/$dir/$name"
    done <<< "$COMMANDS"
    if [ "$CURRENT" -gt 0 ]; then echo "  $CURRENT already up to date"; fi
    CURRENT=0
done
handle_legacy ".claude/commands"
handle_legacy ".cursor/commands"

echo ""
echo "Done (ai-prd-workflow v$VERSION): $ADDED added, $UPDATED updated, $KEPT kept."
echo "Restart your AI tool so it picks up new skills, then type / to see them."
echo "Start with /create-prd for a new project, /document-existing for an existing codebase,"
echo "or /workflow-status to see where a project stands."
