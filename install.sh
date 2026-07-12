#!/usr/bin/env bash
#
# Install the ai-prd-workflow prompts as native slash commands / workflows for:
#
#   --claude     Claude Code   -> .claude/commands/*.md
#   --cursor     Cursor        -> .cursor/commands/*.md
#   --gemini     Gemini CLI    -> .gemini/commands/*.toml
#   --windsurf   Windsurf      -> .windsurf/workflows/*.md
#   --opencode   OpenCode      -> .opencode/commands/*.md
#
# Usage:
#   ./install.sh [target-project-dir] [tool flags...]
#
# Examples:
#   ./install.sh ~/code/my-project                     # Claude Code + Cursor (default)
#   ./install.sh ~/code/my-project --claude            # Claude Code only
#   ./install.sh ~/code/my-project --gemini --opencode # any combination
#   ./install.sh ~/code/my-project --all               # every supported tool
#
# Also works without cloning the repo (prompts are fetched from GitHub):
#   curl -fsSL https://raw.githubusercontent.com/nurettincoban/ai-prd-workflow/main/install.sh | bash -s -- /path/to/project

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/nurettincoban/ai-prd-workflow/main"
SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
if [ -n "$SCRIPT_SOURCE" ] && [ -f "$SCRIPT_SOURCE" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
else
    SCRIPT_DIR=""
fi

ALL_TOOLS="claude cursor gemini windsurf opencode"

TARGET="."
TOOLS=""
for arg in "$@"; do
    case "$arg" in
        --claude)   TOOLS="$TOOLS claude" ;;
        --cursor)   TOOLS="$TOOLS cursor" ;;
        --gemini)   TOOLS="$TOOLS gemini" ;;
        --windsurf) TOOLS="$TOOLS windsurf" ;;
        --opencode) TOOLS="$TOOLS opencode" ;;
        --all)      TOOLS="$ALL_TOOLS" ;;
        --help|-h)
            echo "Install ai-prd-workflow slash commands into a project."
            echo ""
            echo "Usage: ./install.sh [target-project-dir] [tool flags...]"
            echo ""
            echo "  --claude     Claude Code (.claude/commands/)"
            echo "  --cursor     Cursor (.cursor/commands/)"
            echo "  --gemini     Gemini CLI (.gemini/commands/)"
            echo "  --windsurf   Windsurf (.windsurf/workflows/)"
            echo "  --opencode   OpenCode (.opencode/commands/)"
            echo "  --all        Every supported tool"
            echo ""
            echo "Default (no flags): --claude --cursor"
            echo ""
            echo "Claude Code users can also install this as a plugin instead:"
            echo "  /plugin marketplace add nurettincoban/ai-prd-workflow"
            echo "  /plugin install prd-workflow@ai-prd-workflow"
            exit 0
            ;;
        --*)
            echo "Error: unknown flag '$arg' (see --help)" >&2
            exit 1
            ;;
        *) TARGET="$arg" ;;
    esac
done
[ -n "$TOOLS" ] || TOOLS="claude cursor"

if [ ! -d "$TARGET" ]; then
    echo "Error: target directory '$TARGET' does not exist." >&2
    exit 1
fi

# command-name|source-prompt-file|description|argument-hint
COMMANDS='
create-prd|interactive-prd-creation-prompt.md|Create a PRD through guided step-by-step questioning|
verify-prd|prd-comprehensive-verification-prompt.md|Verify and improve PRD.md by finding gaps and quality issues|
extract-features|prd-to-features-prompt.md|Extract prioritized features from PRD.md into FEATURES.md|
generate-rules|prd-to-rules-prompt.md|Generate development rules and standards into RULES.md|
generate-rfcs|prd-to-rfcs-prompt.md|Break the PRD into sequential implementation RFCs|
implement-rfc|implementation-prompt-template.md|Implement a specific RFC (plan first, then code)|[rfc-id]
review-rfc|code-review-prompt.md|Review an RFC implementation against its spec and project standards|[rfc-id]
test-strategy|testing-strategy-prompt.md|Generate a test plan from features and RFCs|
manage-changes|prd-change-management-prompt.md|Analyze and integrate PRD changes mid-development|
workflow-status|workflow-status-prompt.md|Report which workflow artifacts exist and recommend the next step|
'

get_prompt() {
    local file="$1"
    if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/$file" ]; then
        cat "$SCRIPT_DIR/$file"
    else
        curl -fsSL "$REPO_RAW/$file"
    fi
}

# Argument preamble variants. Tools with explicit argument substitution get the
# substituted value; tools without it reference "the ID after the command".
# shellcheck disable=SC2016  # $ARGUMENTS and {{args}} are literal placeholders for the target tool
ARG_LINE_SUBST='Target RFC ID: "$ARGUMENTS" — substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.'
ARG_LINE_GEMINI='Target RFC ID: "{{args}}" — substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.'
ARG_LINE_PLAIN='Target RFC: the ID provided after this command in my message — substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.'

write_claude() {
    local name="$1" src="$2" desc="$3" arghint="$4"
    local out="$TARGET/.claude/commands/$name.md"
    local content
    content="$(get_prompt "$src")" || { echo "Error: could not fetch $src" >&2; return 1; }
    {
        echo "---"
        echo "description: $desc"
        if [ -n "$arghint" ]; then
            echo "argument-hint: $arghint"
        fi
        echo "---"
        echo ""
        if [ -n "$arghint" ]; then
            echo "$ARG_LINE_SUBST"
            echo ""
        fi
        echo "$content"
    } > "$out"
    echo "  /$name -> $out"
}

write_cursor() {
    local name="$1" src="$2" desc="$3" arghint="$4"
    local out="$TARGET/.cursor/commands/$name.md"
    local content
    content="$(get_prompt "$src")" || { echo "Error: could not fetch $src" >&2; return 1; }
    {
        if [ -n "$arghint" ]; then
            echo "$ARG_LINE_PLAIN"
            echo ""
        fi
        echo "$content"
    } > "$out"
    echo "  /$name -> $out"
}

write_gemini() {
    local name="$1" src="$2" desc="$3" arghint="$4"
    local out="$TARGET/.gemini/commands/$name.toml"
    local content
    content="$(get_prompt "$src")" || { echo "Error: could not fetch $src" >&2; return 1; }
    {
        echo "description = \"$desc\""
        echo "prompt = '''"
        if [ -n "$arghint" ]; then
            echo "$ARG_LINE_GEMINI"
            echo ""
        fi
        echo "$content"
        echo "'''"
    } > "$out"
    echo "  /$name -> $out"
}

write_windsurf() {
    local name="$1" src="$2" desc="$3" arghint="$4"
    local out="$TARGET/.windsurf/workflows/$name.md"
    local content
    content="$(get_prompt "$src")" || { echo "Error: could not fetch $src" >&2; return 1; }
    {
        echo "---"
        echo "description: $desc"
        echo "---"
        echo ""
        if [ -n "$arghint" ]; then
            echo "$ARG_LINE_PLAIN"
            echo ""
        fi
        echo "$content"
    } > "$out"
    echo "  /$name -> $out"
}

write_opencode() {
    local name="$1" src="$2" desc="$3" arghint="$4"
    local out="$TARGET/.opencode/commands/$name.md"
    local content
    content="$(get_prompt "$src")" || { echo "Error: could not fetch $src" >&2; return 1; }
    {
        echo "---"
        echo "description: $desc"
        echo "---"
        echo ""
        if [ -n "$arghint" ]; then
            echo "$ARG_LINE_SUBST"
            echo ""
        fi
        echo "$content"
    } > "$out"
    echo "  /$name -> $out"
}

install_tool() {
    local tool="$1" dir label
    case "$tool" in
        claude)   dir=".claude/commands";    label="Claude Code" ;;
        cursor)   dir=".cursor/commands";    label="Cursor" ;;
        gemini)   dir=".gemini/commands";    label="Gemini CLI" ;;
        windsurf) dir=".windsurf/workflows"; label="Windsurf" ;;
        opencode) dir=".opencode/commands";  label="OpenCode" ;;
    esac
    mkdir -p "$TARGET/$dir"
    echo "Installing $label commands:"
    echo "$COMMANDS" | while IFS='|' read -r name src desc arghint; do
        if [ -n "$name" ]; then
            "write_$tool" "$name" "$src" "$desc" "$arghint"
        fi
    done
}

# Iterate over ALL_TOOLS so repeated flags don't install twice
for tool in $ALL_TOOLS; do
    case " $TOOLS " in
        *" $tool "*) install_tool "$tool" ;;
    esac
done

echo ""
echo "Done. Open your project in your AI coding tool and type / to see the commands."
echo "Start with /create-prd for a new project, or /workflow-status for an existing one."
