# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
- Five broken hand-offs between commands, the same class of bug 2.2.0 fixed for the review report:
  - `/generate-rules` now gives every rule a permanent, append-only ID (`SEC-3`) — `/manage-changes` and the self-checks cited rule IDs that nothing created
  - `/test-strategy` now saves `TEST-STRATEGY.md` with a section per RFC, and `/implement-rfc` and `/review-rfc` read it — the plan was moved before implementation in 2.2.0, but the implementer never saw it
  - `PRD-REVIEW.md` is now read by `/extract-features`, `/generate-rules`, `/generate-rfcs` and `/manage-changes` — it said "downstream commands should read this file" and none did
  - The PRD gains a **Decisions** section (written by `/create-prd` and `/verify-prd`), which `/manage-changes` checks changes against — it previously checked against "resolved decisions" no PRD contained
  - `/implement-rfc` records deviations in the RFC under `## Implementation Notes`, and `/review-rfc` reads them — the reviewer runs in a fresh session by design, so a deviation explained only in chat looked like a bug
- `/implement-rfc` stops when a declared predecessor is not implemented yet, reads any earlier review of the RFC, and finds the RFC at its real path (`RFCs/RFC-[ID]-*.md`) instead of `RFC-[ID].md`; the never-filled `[Title]` placeholders are gone
- `/workflow-status` no longer reports parallel RFCs as drift (2.2.0 replaced strict ordering with declared predecessors) and checks for `TEST-STRATEGY.md`

- README no longer claims the workflow predates every AI planning mode — Aider, Roo Code and Cline shipped planning modes before March 2025. It now says what is true: it predates plan mode in Claude Code and Cursor, and both Kiro and Spec Kit

### Added
- Artifact contracts table in `CONTRIBUTING.md`, enforced in CI by `scripts/check-prompts.py`: it fails when a command reads something nothing writes, writes something nothing reads, or does not mention an artifact its row declares

## [2.3.0] - 2026-10-01

### Added
- Claude Code plugin — the repo is now its own plugin marketplace (`.claude-plugin/`); install with `/plugin marketplace add nurettincoban/ai-prd-workflow` then `/plugin install prd-workflow@ai-prd-workflow`
- Native slash-command support for three more tools via `install.sh`: Gemini CLI (`--gemini` → `.gemini/commands/*.toml`), Windsurf (`--windsurf` → `.windsurf/workflows/`), and OpenCode (`--opencode` → `.opencode/commands/`); flags combine, `--all` installs everything
- CI (GitHub Actions): shellcheck, a drift check that fails when the committed command folders differ from the source prompts, install smoke tests for every tool (file counts, TOML validity, Windsurf 12k size limit, flag isolation), and plugin manifest validation
- `RFCS.md` master index in the url-shortener example, including the coverage gaps it exposes (F7, a Must Have, has no RFC)
- Issue templates, pull request template, and `SECURITY.md`

### Changed
- README: plugin quick start, expanded tool support matrix, CI badge
- Shell scripts cleaned up to pass shellcheck (dead code removed, `cat |` pipelines replaced with redirects)
- `install.sh` rejects unknown flags instead of treating them as the target directory
- Only the Claude Code and Cursor command folders are committed; the Gemini CLI, Windsurf, and OpenCode formats are generated on demand

## [2.2.0] - 2026-07-20

Fixes from a full dogfooding run — all ten commands used end to end to build a real, publishable library from a real PRD. Three structural problems surfaced: nothing in the workflow ever executed anything, decisions were discarded while artifacts were kept, and every prompt assumed a CRUD web application.

### Added
- Verification step in `/implement-rfc` — run the build, typecheck and tests, paste the actual output, and verify one end-to-end path against the built artifact rather than the source
- `STEP 0: RUN IT` in `/review-rfc` and a baseline step in `/test-strategy` — both now execute before assessing, and must say so explicitly when they cannot
- Shared "classify the product type" preamble in six commands — apply only the checks that fit and state which were skipped, so a library no longer gets database, auth and accessibility sections
- Grounding in existing code: `STEP 0: GROUND THE PRD IN REALITY` in `/verify-prd`, an existing-implementation question in `/create-prd`, and reference-implementation derivation in `/generate-rules`
- `CONFLICT CHECK` as the first step of `/manage-changes` impact analysis — cites violated rule IDs and reversed decisions before anything else
- Decision records written to disk: `PRD-REVIEW.md`, `reviews/REVIEW-RFC-[ID].md`, `changes/CHANGE-REQUEST-[NNN].md`
- Fresh-session requirement in `/review-rfc`, and a cold-read check in `/generate-rfcs` — hand each RFC to a new session and ask what it would have to guess
- `SELF-CHECK BEFORE FINISHING` in the five generating commands — recount tables from actual content, verify every cross-reference resolves to what the text claims, confirm no two tables disagree
- Artifact precedence rule (`PRD > FEATURES > RULES > RFCs > generated plans`) in the four downstream consumers
- Per-RFC implemented/reviewed tracking in `/workflow-status`
- README: restart-after-install note, the multi-lens evidence table, and the ID-stability property

### Changed
- `/generate-rfcs` no longer mandates strict sequential implementation — each RFC must be implementable once its **declared predecessors** are complete, so independent branches can be parallelized while the solo path is unchanged
- `/test-strategy` moved ahead of `/implement-rfc` in the pipeline, so the plan exists before the tests it plans are written
- `/generate-rules` must verify dependency versions against the actual registry instead of stating them from memory
- `/test-strategy` no longer hard-codes a 100% coverage target, and takes priorities from the existing MoSCoW ratings in FEATURES.md
- `/verify-prd` treats an existing PRD as a normal entry point, and warns before overwriting `PRD.md` when the project is not under version control
- `/manage-changes` documentation updates cover every affected artifact, not just the PRD — all in one commit, or none
- `/workflow-status` stage table covers all ten commands (was eight)

### Fixed
- `/generate-rfcs` step 5 referenced `implementation-prompt-template.md`, which `install.sh` never installs into a project — the step was unexecutable as written and duplicated `/implement-rfc`
- `/workflow-status` expected a "Review report" artifact that no command in the suite ever produced, so stage 7 could never be reported Done
- RFC acceptance criteria could silently omit files named elsewhere in the same RFC, so those files never got built while the RFC was reported complete

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
