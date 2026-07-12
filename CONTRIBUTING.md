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
- **Length**: Aim for 40-70 lines. If your prompt exceeds 80 lines, look for redundancy to cut.
- **Terminology**: Use MoSCoW (Must/Should/Could/Won't have) for any prioritization language.
- **Tool-agnostic**: Do not use tool-specific syntax (e.g., Cursor's `@file` references). Reference files by name.

## Prompt Quality Guidelines

- **Trust modern LLMs**: Don't include instructions for markdown formatting, being clear, or being specific. Modern models do this by default.
- **Say it once**: If an instruction appears more than twice, consolidate it into one clear statement.
- **Be concrete**: "Review for security vulnerabilities" is better than "ensure the code is secure."
- **Focus on what's unique**: Only include instructions that the AI wouldn't do by default.

## Source of Truth & Generated Files

The prompt `.md` files at the repo root are the single source of truth. The `.claude/commands/`, `.cursor/commands/`, `.gemini/commands/`, `.windsurf/workflows/`, and `.opencode/commands/` folders are **generated** by `install.sh` — never edit them by hand. (`.claude-plugin/` manifests are hand-maintained; the plugin reuses `.claude/commands/`.)

After adding or editing a prompt:

1. If it's a new prompt, add it to the `COMMANDS` mapping in `install.sh` and to the `show_prompts` list in `copy-prompt.sh`
2. Run `./install.sh . --all` to regenerate the command folders
3. Commit the regenerated files together with your prompt change — CI fails if they drift from the source prompts

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
