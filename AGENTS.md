# Working on ai-prd-workflow

This repository is a set of prompts. The prompt files at the repo root are the product; everything else exists to ship them and to check them. Read CONTRIBUTING.md for the full rules; these are the ones an AI agent most often gets wrong.

- **Edit the root prompts, never `skills/`.** `skills/` is generated from the root prompts by `./install.sh --build`. After changing a prompt, rebuild and commit `skills/` in the same commit.
- **Shared sections live in `shared/`.** Some sections appear word for word in several prompts. Edit the file in `shared/` and run `python3 scripts/check-prompts.py --fix`; editing one copy fails CI.
- **Contracts move with the prompts.** If a prompt starts or stops reading or writing an artifact (PRD.md, FEATURES.md, RFCS.md, ...), update the contracts table in CONTRIBUTING.md in the same commit.
- **The example is real output.** `examples/url-shortener/after/` was produced by running the commands. Do not hand-edit it to match a prompt change; rerun the commands, or leave it and say it predates the change.
- **README changes reach the translations.** `README.zh-CN.md` and `README.tr.md` follow `README.md`. Update them in the same change, keeping commands, code and file names in English, or tell the user they are now behind.
- **Versions move together.** `VERSION` in `install.sh`, `version` in `.claude-plugin/plugin.json`, and the CHANGELOG entry.

Before committing, run:

```bash
python3 scripts/check-prompts.py
python3 -m unittest discover scripts
./install.sh --build && bash scripts/test-install.sh
```

When writing prompt text: keep it tool-agnostic and concrete, and say why a rule exists when the reason is not obvious — the existing prompts do this, and the reasons are what stop a later edit from "simplifying" the rule away.
