# Contributing

Thanks for your interest in improving ai-prd-workflow! Here's how to contribute.

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b my-new-prompt`)
3. Make your changes
4. Submit a Pull Request with a clear description of what you changed and why

## Submitting New Prompts

New prompt files should follow these conventions:

- **Naming**: `<descriptive-name>-prompt.md` (e.g., `api-design-prompt.md`)
- **Structure**: Every prompt should include:
  - A clear role statement (who the AI should act as)
  - Input description (what documents/context the AI needs)
  - Numbered steps or sections for the task
  - An output format section (what the deliverable looks like)
- **Length**: Aim for 40-70 lines of command-specific instructions; the shared sections described below don't count. If yours exceeds 80, look for redundancy to cut.
- **Terminology**: Use MoSCoW (Must/Should/Could/Won't have) for any prioritization language.
- **Tool-agnostic**: Do not use tool-specific syntax (e.g., Cursor's `@file` references). Reference files by name.

## Prompt Quality Guidelines

- **Trust modern LLMs**: Don't include instructions for markdown formatting, being clear, or being specific. Modern models do this by default.
- **Say it once**: If an instruction appears more than twice, consolidate it into one clear statement.
- **Be concrete**: "Review for security vulnerabilities" is better than "ensure the code is secure."
- **Focus on what's unique**: Only include instructions that the AI wouldn't do by default.

## Source of Truth & Generated Files

The prompt `.md` files at the repo root are the single source of truth. The `.claude/commands/` and `.cursor/commands/` folders are **generated** by `install.sh` and committed — never edit them by hand. The Gemini CLI, Windsurf, and OpenCode formats are generated on demand by `install.sh` and not committed. (`.claude-plugin/` manifests are hand-maintained; the plugin reuses `.claude/commands/`.)

After adding or editing a prompt:

1. If it's a new prompt, add it to the `COMMANDS` mapping in `install.sh` and to the `show_prompts` list in `copy-prompt.sh`
2. Run `./install.sh .` to regenerate the committed command folders
3. Commit the regenerated files together with your prompt change — CI fails if they drift from the source prompts

## Shared Sections

A few sections appear word for word in several prompts, because every prompt must still work on its own when pasted into a chat. Their canonical text lives in `shared/`:

| File | Used by |
|---|---|
| `shared/classify-product-type.md` | prompts that write the PRD and classify the product |
| `shared/product-type.md` | prompts that read the classification from PRD.md |
| `shared/self-check.md` | prompts that generate an artifact |
| `shared/when-artifacts-conflict.md` | prompts that read several artifacts |

Edit the file in `shared/`, then run `python3 scripts/check-prompts.py --fix` to copy it into every prompt that has that section. CI fails when a copy differs. `--fix` refuses to overwrite a section that holds more than the shared text — content after a shared section needs its own `## ` heading.

## Artifact Contracts

The commands talk to each other only through files. Each row below says what a command reads and what it writes, and `scripts/check-prompts.py` (run in CI) fails when:

- a command reads an artifact no command writes,
- a command writes an artifact nothing reads — `/workflow-status` reads everything to report status, which does not count,
- a prompt never mentions an artifact its row declares, or
- this table and `install.sh` disagree about which commands exist.

Every one of those has shipped as a real bug: a review record no command produced, a test plan the implementer never opened, rule IDs cited everywhere and created nowhere. When you change what a prompt reads or writes, change its row in the same commit.

<!-- contracts:start -->
| Command | Prompt | Reads | Writes |
|---|---|---|---|
| `/create-prd` | interactive-prd-creation-prompt.md | code | PRD.md |
| `/verify-prd` | prd-comprehensive-verification-prompt.md | PRD.md, code | PRD.md, PRD-REVIEW.md |
| `/extract-features` | prd-to-features-prompt.md | PRD.md, PRD-REVIEW.md | FEATURES.md |
| `/generate-rules` | prd-to-rules-prompt.md | PRD.md, PRD-REVIEW.md, FEATURES.md, code | RULES.md |
| `/generate-rfcs` | prd-to-rfcs-prompt.md | PRD.md, PRD-REVIEW.md, FEATURES.md, RULES.md | RFCs/, RFCS.md |
| `/test-strategy` | testing-strategy-prompt.md | PRD.md, FEATURES.md, RULES.md, RFCs/, code | TEST-STRATEGY.md |
| `/implement-rfc` | implementation-prompt-template.md | PRD.md, FEATURES.md, RULES.md, RFCs/, RFCS.md, TEST-STRATEGY.md, reviews/ | code, RFCs/ |
| `/review-rfc` | code-review-prompt.md | PRD.md, FEATURES.md, RULES.md, RFCs/, TEST-STRATEGY.md, code | reviews/ |
| `/manage-changes` | prd-change-management-prompt.md | PRD.md, PRD-REVIEW.md, RULES.md, changes/, code | changes/, PRD.md, FEATURES.md, RULES.md, RFCs/, RFCS.md, TEST-STRATEGY.md |
| `/workflow-status` | workflow-status-prompt.md | PRD.md, PRD-REVIEW.md, FEATURES.md, RULES.md, RFCs/, RFCS.md, TEST-STRATEGY.md, reviews/, changes/, code | — |
<!-- contracts:end -->

## Modifying Existing Prompts

- Explain the rationale for your changes in the PR description
- If trimming content, note what was removed and why it's unnecessary
- Keep the overall structure consistent with other prompts in the repo

## Testing Prompts

Before submitting, test your prompt with at least 2 different LLMs (e.g., Claude and GPT-4):

1. Run the prompt with a realistic input
2. Verify the output covers all expected sections
3. Check that the output is actionable and well-structured
4. Include a brief summary of your test results in the PR description

## Questions?

Open an issue if you have questions or ideas you'd like to discuss before contributing.
