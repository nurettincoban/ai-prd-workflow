# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.2.0] - 2026-07-12

### Added
- Claude Code plugin — the repo is now its own plugin marketplace (`.claude-plugin/`); install with `/plugin marketplace add nurettincoban/ai-prd-workflow` then `/plugin install prd-workflow@ai-prd-workflow`
- Native slash-command support for three more tools via `install.sh`: Gemini CLI (`--gemini` → `.gemini/commands/*.toml`), Windsurf (`--windsurf` → `.windsurf/workflows/`), and OpenCode (`--opencode` → `.opencode/commands/`); flags combine, `--all` installs everything
- Committed generated command folders for all five supported tools, so cloning the repo gives working commands in each
- CI (GitHub Actions): shellcheck, generated-commands drift check, install smoke tests (file counts, TOML validity, Windsurf 12k size limit, flag isolation), plugin manifest validation
- `RFCS.md` master index in the url-shortener example — the example now matches everything the RFCs prompt promises to produce
- Issue templates, pull request template, and `SECURITY.md`

### Changed
- `prd-to-rfcs` prompt: per-RFC implementation-prompt files are now explicitly a copy-paste-workflow step, skipped when slash commands are installed (`/implement-rfc` already applies the template)
- README: plugin quick start, expanded tool support matrix, CI badge
- Shell scripts cleaned up to pass shellcheck (dead code removed, `cat |` pipelines replaced with redirects)

## [2.1.0] - 2026-07-06

### Added
- `install.sh` — installs all prompts as native slash commands for Claude Code (`.claude/commands/`) and Cursor (`.cursor/commands/`); works via `curl | bash` without cloning
- Committed `.claude/commands/` and `.cursor/commands/` so cloning the repo gives working slash commands immediately
- Workflow Status prompt (`/workflow-status`) — reports which artifacts exist, detects drift, and recommends the next step
- Agent configuration guidance in the Rules prompt (wire RULES.md into CLAUDE.md, AGENTS.md, or `.cursor/rules/`)
- `.gitignore`

### Changed
- README repositioned around spec-driven development, with slash-command Quick Start, Mermaid workflow diagram, and updated model compatibility (Claude 4/5, GPT-5, Gemini 2.5+)
- Prompts reference concrete filenames (PRD.md, FEATURES.md, RULES.md) instead of "attached" documents
- CONTRIBUTING documents the prompt-files-as-source-of-truth rule and command regeneration

## [2.0.0] - 2026-03-21

### Added
- Code Review prompt for reviewing implementations against RFCs
- Testing Strategy prompt for generating comprehensive test plans
- Examples folder with complete URL shortener sample project
- CONTRIBUTING.md with prompt submission guidelines
- CHANGELOG.md
- MIT LICENSE file
- `--list` and `--help` flags for copy-prompt.sh
- Compatibility section in README
- Quick Start section in README

### Changed
- All prompts trimmed ~30-40% for modern LLMs (less verbose, more effective)
- Removed Cursor-specific `@file` references from implementation template
- Standardized MoSCoW terminology across all prompts
- Overhauled README with updated workflow diagram, examples section, and tool-agnostic language
- Rebranded from "cursor-ai-prd-workflow" to "ai-prd-workflow"
- Updated workflow to include Code Review and Testing steps

### Fixed
- README referenced LICENSE file that didn't exist

## [1.0.0] - 2025-03-01

### Added
- Interactive PRD Creation prompt
- PRD Comprehensive Verification prompt
- PRD to Features Extraction prompt
- PRD to Rules prompt
- PRD to RFCs prompt
- Implementation Prompt Template
- PRD Change Management prompt
- copy-prompt.sh clipboard helper script
- README with workflow documentation
