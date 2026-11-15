# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [3.1.0] - 2026-11-15

This release came out of a review gauntlet: critics attacked the prompts, the README and the install path, and a second model (Fable 5.2) did the cold reads. Every finding below was reported by a critic and checked before it was fixed.

### Fixed
- `/verify-prd` no longer invents answers. It asks about every High-impact gap only the user can close (budget, team, which of two contradictory requirements is meant) before rewriting, and records anything unanswered in Open Questions marked **(assumption)**, never in Decisions. A guess written into PRD.md as a decision was defended by every later command
- `/generate-rfcs` can run again on a project that already has RFCs. It extends the plan instead of renumbering from 001, never rewrites an RFC past Not started, and keeps every Status. A regenerated RFC-001 silently attached an old review to new work
- `/manage-changes` stops after the assessment and applies only the changes you accept. It now adds each decision (accepted or rejected) to the PRD's Decisions, sets changed RFCs that were Implemented or Reviewed back to Changes requested, and runs the self-check and `trace-check.py`
- A fix round after Changes requested no longer looks reviewed. Predecessors must be Implemented or Reviewed; `/workflow-status` counts a review only if its last round has no blocking issues
- `/review-rfc` knows which code to review: `/implement-rfc` records the files changed and the commit or branch in the RFC's Implementation Notes
- On existing codebases, `/review-rfc` marks the RFC's features Implemented in FEATURES.md, so the next `/generate-rfcs` does not plan them again. `/document-existing` now routes through `/extract-features` after `/verify-prd`
- `/test-strategy` writes one section per RFC, one row per acceptance criterion, instead of six generic test-type checklists that nobody read at implementation time
- `/generate-rules` writes only rules a reviewer can check against a line of code, adds accessibility rules only for products with a UI, and no longer copies priorities and phasing out of FEATURES.md
- `/create-prd` records unanswered questions as labelled assumptions instead of filling Timeline and Success Metrics with guesses
- The prompts now state the exact ID forms the checker reads (`- **FR-1**: text`, `F1`, `RFC-001`)
- `trace-check.py` counts requirements defined in tables, lists and headings together (FRs in a table and NFRs as bullets gave false failures), exits 2 on a path that is not a directory instead of passing, and supports `--help`
- `install.sh` says when a `--ref` tag is missing from the clone, rejects a second target directory and a target that is a file
- `copy-prompt.sh` prints the prompt when piped or with `--print`, so it works over SSH and in containers
- `.gitignore` covers `__pycache__/` left by the unit tests
- Doubt no longer gets lost between files. A new shared section, **When a question has no answer**, tells every generating command what to do when nobody can answer: decide, mark it **(assumption)**, list it under `## Open Questions`, and never weaken a requirement from a higher artifact by assumption. Conflicts between artifacts go into one `## Open conflicts` list in RFCS.md. `/implement-rfc` puts both in front of you with the plan, and `/workflow-status` counts what is still unconfirmed. In the example run, about 100 assumptions and 22 flagged conflicts sat in files no command had to read before code was written
- `/generate-rfcs` gives each cold reader the RFCs the RFC depends on, directly or through another RFC. In the todo-cli run, readers without them spent most of their reports on interfaces a predecessor already defined
- `/generate-rfcs` fixes only cold-read findings that change behavior or a shared interface, cold-reads the fixed RFCs again before calling them passed, splits RFCs above about 15 criteria, and drops criteria that restate the rules
- `/generate-rules` writes structure and architecture rules only where the PRD or existing code fixes them, so rules stop pre-empting the RFCs that do the design
- `/manage-changes` saves the change request as pending before asking, and marks changed RFCs **Spec changed** instead of Changes requested, which the checker reserves for reviews
- `/verify-prd` cites a finding for every change to scope or a requirement; `/test-strategy` cites criteria by number instead of restating them; `/review-rfc` marks a feature split across RFCs Implemented only when all of them are reviewed
- The self-check says what `trace-check.py` does not check, instead of implying it checks everything

### Added
- `examples/url-shortener/after/`: the example's promised "after" half, produced by running `/verify-prd`, `/extract-features`, `/generate-rules`, `/generate-rfcs` and `/test-strategy` on the v2.0 PRD with these prompts, plus the cold-read reports that fixed the RFCs. The README and the example said it existed; it did not
- `examples/todo-cli/`: a second, much smaller example run from a ten-line idea to reviewed code (`/create-prd` through `/review-rfc` and `/workflow-status`), every step on Claude Sonnet 5.5, with two rounds of cold reads
- The README opens with a real run: one line of the input spec followed through the review, the fixed PRD and the RFC

### Changed
- README: a plain one-line pitch, a single Claude Code quick start with the other tools folded away, the evidence you can check first and the field report from an unpublished library labelled as such
- Plugin and marketplace descriptions match the README, with keywords for discovery

## [3.0.0] - 2026-10-01

The commands now ship as **Agent Skills** — one `SKILL.md` format for Claude Code, Codex, GitHub Copilot, Cursor, Gemini CLI, OpenCode and Devin — and the hand-offs between them are checked by machine instead of by the model's self-review.

**Upgrading from 2.x:** rerun `install.sh` with `--remove-legacy`, which installs the skills and moves the old command files into a backup folder. Command names are unchanged. If you edited an installed command, copy your changes into the new `SKILL.md`; `install.sh` will keep your edited skills from then on.


### Fixed
- Five broken hand-offs between commands, the same class of bug 2.2.0 fixed for the review report:
  - `/generate-rules` now gives every rule a permanent, append-only ID (`SEC-3`) — `/manage-changes` and the self-checks cited rule IDs that nothing created
  - `/test-strategy` now saves `TEST-STRATEGY.md` with a section per RFC, and `/implement-rfc` and `/review-rfc` read it — the plan was moved before implementation in 2.2.0, but the implementer never saw it
  - `PRD-REVIEW.md` is now read by `/extract-features`, `/generate-rules`, `/generate-rfcs` and `/manage-changes` — it said "downstream commands should read this file" and none did
  - The PRD gains a **Decisions** section (written by `/create-prd` and `/verify-prd`), which `/manage-changes` checks changes against — it previously checked against "resolved decisions" no PRD contained
  - `/implement-rfc` records deviations in the RFC under `## Implementation Notes`, and `/review-rfc` reads them — the reviewer runs in a fresh session by design, so a deviation explained only in chat looked like a bug
- `/implement-rfc` stops when a declared predecessor is not implemented yet, reads any earlier review of the RFC, and finds the RFC at its real path (`RFCs/RFC-[ID]-*.md`) instead of `RFC-[ID].md`; the never-filled `[Title]` placeholders are gone
- `/workflow-status` no longer reports parallel RFCs as drift (2.2.0 replaced strict ordering with declared predecessors) and checks for `TEST-STRATEGY.md`

- README: the "each step is a different lens" evidence came from a run nobody could inspect; it now links to evidence anyone can reproduce — the before/after example and the eval suite
- README no longer claims the workflow predates every AI planning mode — Aider, Roo Code and Cline shipped planning modes before March 2025. It now says what is true: it predates plan mode in Claude Code and Cursor, and both Kiro and Spec Kit

### Added
- A demo at the top of the README: a condensed replay of the real `/workflow-status` run on the v2.0 example, and a "try it on the example first" quick start — install the skills into `examples/url-shortener/before` and see what the workflow finds. That run's report moved out of `before/` so the folder can be audited fresh
- README translations: Simplified Chinese, Turkish, Japanese, Korean and Spanish (`README.<lang>.md`)
- `evals/`, a [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) suite that runs every case with and without the plugin, so the score difference is what the workflow adds over a plain agent. Three cases are seeded from the v2.0 example: `/verify-prd` on ten problems found by hand in its PRD, `/workflow-status` on cross-document gaps, and `/extract-features` keeping feature IDs stable when requirements are inserted. Graders are regexes checked against real command output, and against the fixture itself so that quoting a problem does not count as finding it. CI checks the fixtures and graders without model calls
- The url-shortener example is now a before/after: the v2.0 artifacts unchanged in `before/`, the problems found in them by hand, and what fresh-context runs of `/workflow-status` (12 of 13) and `/verify-prd` (10 of 10) found without seeing that list
- Agent Skills: `skills/<name>/SKILL.md`, generated from the prompt sources by `./install.sh --build` and shipped unchanged by every channel — the Claude Code plugin, `install.sh`, and anything that reads Agent Skills
- `install.sh` installs into `.claude/skills/` and `.agents/skills/`, and no longer overwrites silently: every skill carries a version and a checksum, a skill you edited is kept, `--force` replaces it after saving a backup, `--ref vX.Y.Z` pins a release, and `--remove-legacy` moves v2 command files aside
- `scripts/test-install.sh`, run in CI: fresh install, idempotent re-run, kept edits, `--force` backups, upgrades from an older release, v2 migration, and the `curl | bash` path end to end
- `check-prompts.py` also fails when `install.sh`, `plugin.json` and this CHANGELOG disagree about the version
- `/document-existing` — an entry point for codebases that already exist. It reads the code and its tests, asks what the code cannot say (users, intent, what is planned), and writes `PRD.md`, `FEATURES.md` (existing capabilities marked `Implemented`, with their code location) and `RULES.md` (the conventions the code actually follows). `/generate-rfcs` then plans only the new work. The README previously told existing-codebase users the workflow was not for them
- `scripts/trace-check.py` — a deterministic traceability check (Python 3.8+, standard library only). It fails when a cited ID does not exist, a PRD requirement has no feature, a Must Have feature has no RFC, an RFC depends on a later one, `RFCS.md` disagrees with `RFCs/`, or an RFC is marked reviewed without a review record. The self-checks and `/workflow-status` run it when it is available, because recounting tables and following references is exactly what an LLM self-check is worst at
- Machine-readable formats the checker relies on: permanent requirement IDs in the PRD (`FR-1`, `NFR-1`), a fixed column layout for `FEATURES.md` with a Source column, four header lines at the top of every RFC (`**Features**`, `**Depends on**`, `**Rules**`, `**Complexity**`), and a Status column in `RFCS.md`
- Artifact contracts table in `CONTRIBUTING.md`, enforced in CI by `scripts/check-prompts.py`: it fails when a command reads something nothing writes, writes something nothing reads, or does not mention an artifact its row declares

### Changed
- README rewritten to say each thing once: a three-path quick start, one command table (what each command does, what it writes, and its prompt) instead of three overlapping lists, the plan-mode comparison and the evidence condensed, and install details moved below the quick start. 240 → 183 lines. Adds an acknowledgment of Anthropic's support
- One skills format replaces the five per-tool command formats. Cursor moved custom commands to skills; Gemini CLI (0.34+), OpenCode and Devin run skills as slash commands; and Devin Desktop removed Windsurf workflows in September 2026, so 2.3.0's `.windsurf/workflows/` target no longer worked. `--cursor`, `--gemini`, `--opencode` and `--windsurf` still work, as aliases for `--agents`
- `/review-rfc` runs in a forked context with no conversation history (`context: fork`) in Claude Code and Copilot, so a fresh-eyes review no longer depends on the user opening a new session
- `trace-check.py` is bundled with the skills that run it
- The product type is classified once, in `/create-prd` or `/verify-prd`, and recorded in a **Product Type** section of the PRD. The four downstream commands read it instead of re-classifying — six separate classifications could disagree from one step to the next
- The classification checklist covers all seven product types (web app, mobile app, library/SDK, CLI, service/API, data pipeline, game). Only library/SDK had concrete checks before; the other six were told to "work out their own equivalents"
- Sections shared word for word across prompts live in `shared/`, and `scripts/check-prompts.py` fails CI when a copy drifts (`--fix` re-syncs them). `/generate-rfcs` also folds its overlapping sections 7 and 8 into 3 and 4: 101 → 93 lines despite new format rules
- RFC status is kept, not re-derived. `RFCS.md` carries a Status column that `/implement-rfc` (In progress → Implemented) and `/review-rfc` (Reviewed / Changes requested) update; `/workflow-status` starts from it and spot-checks it against the code instead of re-reading every RFC's criteria
- `/review-rfc` appends a new round to `reviews/REVIEW-RFC-[ID].md` instead of overwriting the previous review
- "Fresh eyes" is enforced instead of requested. `/review-rfc` opened with "run this in a fresh session", which the model only reads after it has been invoked in the current one; it now stops when the conversation contains the implementation it is about to review. `/generate-rfcs` runs the cold-read check itself with clean-context subagents where the tool supports them, and records which RFCs passed
- `copy-prompt.sh` on Windows (Git Bash, Cygwin, WSL) sends the clipboard UTF-16 with a byte-order mark — `clip.exe` garbled the prompts' em dashes and arrows — and supports Wayland (`wl-copy`)
- `.gitattributes` pins LF line endings, which the raw `curl | bash` path and the skills' checksums rely on
- `AGENTS.md` (imported by `CLAUDE.md`) tells AI agents working on this repo what they most often get wrong: edit the root prompts and `shared/`, never the generated `skills/`

### Removed
- The committed `.claude/commands/` and `.cursor/commands/` folders, replaced by `skills/`. Cloning the repo no longer installs the commands into the clone itself; install the plugin or run `install.sh`

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
