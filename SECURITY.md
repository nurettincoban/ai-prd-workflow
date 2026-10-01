# Security Policy

This project is a collection of markdown prompts plus two shell scripts (`install.sh`, `copy-prompt.sh`). There is no server, no dependencies, and nothing that handles user data. The security surface is:

- **`install.sh` via `curl | bash`** — the script only writes skill folders into the target project's `.claude/skills/` and `.agents/skills/`, and with `--remove-legacy` moves old command files into a backup folder. It never overwrites a file you have edited unless you pass `--force`, which saves a backup first. If you prefer, clone the repo and read the script before running it, or copy the prompts manually.
- **`trace-check.py`** — bundled with some skills and run by your AI tool on your project. It only reads the project's markdown files and prints a report; it writes nothing and makes no network calls.
- **Prompt content** — prompts are instructions for your AI assistant. Review them (they're short) before installing, as you would any third-party agent instruction.

## Reporting a Vulnerability

If you find a security issue — e.g. something in `install.sh` that could write outside the target directory, or prompt content that could cause an agent to take unsafe actions — please report it privately via [GitHub Security Advisories](https://github.com/nurettincoban/ai-prd-workflow/security/advisories/new) rather than a public issue.

You can expect an initial response within a week.
