# Security Policy

This project is a collection of markdown prompts plus two shell scripts (`install.sh`, `copy-prompt.sh`). There is no server, no dependencies, and nothing that handles user data. The security surface is:

- **`install.sh` via `curl | bash`** — the script only writes markdown files into the target project's `.claude/commands/` and `.cursor/commands/` folders. If you prefer, clone the repo and read the script before running it, or copy the prompts manually.
- **Prompt content** — prompts are instructions for your AI assistant. Review them (they're short) before installing, as you would any third-party agent instruction.

## Reporting a Vulnerability

If you find a security issue — e.g. something in `install.sh` that could write outside the target directory, or prompt content that could cause an agent to take unsafe actions — please report it privately via [GitHub Security Advisories](https://github.com/nurettincoban/ai-prd-workflow/security/advisories/new) rather than a public issue.

You can expect an initial response within a week.
