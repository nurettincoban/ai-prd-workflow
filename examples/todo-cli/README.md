# Example: td, a tiny to-do list, from idea to reviewed code

This folder is one complete run of the workflow on a very small product: a command-line to-do list called `td`. It goes from a ten-line idea to working, tested, reviewed code. The url-shortener example stops before implementation; this one doesn't.

Every command ran on **Claude Sonnet 5.5** (`claude-sonnet-5-5`) on 2026-11-15, using the skills built from this repository at 3.1.0. The cold reads ran on Sonnet too. Each step was its own agent with a fresh context and no notes, and it saw only the skill's instructions and the project files. Nobody answered questions during the run. Wherever a command would have asked you something, it decided, marked the decision **(assumption)** and listed it, so you can see what an interactive run would have put in front of you.

Nothing here is hand-edited, including this folder's `CLAUDE.md` and `AGENTS.md`, which `/generate-rules` wrote. The one exception is this README.

## Try it

```bash
cd examples/todo-cli
export TD_FILE=/tmp/td-demo.json
./td add buy milk
./td add call the bank
./td done 1
./td list
python3 -m unittest discover tests      # 66 tests
```

## The run, step by step

| Step | What it wrote |
|---|---|
| The idea | [IDEA.md](IDEA.md): ten lines in the user's words, and the only input |
| `/create-prd` | [PRD.md](PRD.md): 9 functional and 9 non-functional requirements, 8 decisions, 12 open questions marked (assumption) |
| `/verify-prd` | [PRD-REVIEW.md](PRD-REVIEW.md): 3 High, 7 Medium and 3 Low findings, and fixes to PRD.md |
| `/extract-features` | [FEATURES.md](FEATURES.md): 23 features (14 Must, 2 Should, 7 Won't) |
| `/generate-rules` | [RULES.md](RULES.md): 55 checkable rules, and `CLAUDE.md` / `AGENTS.md` pointing at them |
| `/generate-rfcs` | 5 RFCs in [RFCs/](RFCs/) and the index [RFCS.md](RFCS.md), with 10 open conflicts listed |
| cold reads, 2 rounds | [cold-reads/](cold-reads/): one clean-context reader per RFC, then fixes, then a second round of readers on the fixed RFCs |
| `/test-strategy` | [TEST-STRATEGY.md](TEST-STRATEGY.md): 58 planned tests, one row per acceptance criterion |
| `/implement-rfc` ×5, `/review-rfc` ×4 | [td](td) (386 lines), [tests/](tests/) (66 tests), and the reviews in [reviews/](reviews/) |
| `/workflow-status` | [WORKFLOW-STATUS.md](WORKFLOW-STATUS.md): where the project stands |

The whole run took about 35 minutes of agent time.

## What the workflow caught

On a product this small, most of the value went into things nobody would think to write down:

- **`/verify-prd`:** the idea says "it must never lose my tasks, even if it crashes halfway through saving". The first PRD saved by writing a temp file and renaming it over the old one, with no `fsync`, so a power cut could still leave an empty file. It also promised never to reuse ids but stored nothing that remembered the highest id ever issued. Both were fixed in PRD.md before any code existed.
- **`/verify-prd` again:** "never lose my tasks" is also broken by two `td add` runs at the same moment, which the PRD's own assumptions accepted. That one needs a decision from you, so it was not quietly fixed. It is Open conflict 1 in [RFCS.md](RFCS.md), and it is still open (see below).
- **Cold reads, round 1:** 135 items across the 5 RFCs. Two tests would have passed even with the feature broken:
  - The test for `td list | head -1` used about 20 KB of output. That is less than a 64 KB pipe buffer, so the broken-pipe code would never have run.
  - The test for printing under `LANG=C` would have passed regardless, because Python 3.7+ switches the C locale to UTF-8 by itself.
- **Cold reads, round 2:** 44 items, many fewer. The speed test for `td done` and `td rm` reran each command three times on the same file. After the first run the task is already done or already gone, so runs 2 and 3 timed the cheap path that writes nothing.
- **`/review-rfc`:** the reviewers broke the code on purpose to see whether the tests noticed. Most breaks were caught. A few were not, and those are listed as non-blocking issues:
  - `\d` instead of `[0-9]` would let `td done ٣` mark task 3.
  - A line that keeps a broken pipe quiet can be deleted with the suite still green.

## Where it stands, and what an interactive run would ask you

[WORKFLOW-STATUS.md](WORKFLOW-STATUS.md) lists what remains:

- **RFC-001 to RFC-004 are Reviewed.** RFC-005, the release checks, is In progress: the suite passed on Python 3.10, 3.11, 3.12 and 3.13 on Linux, but nobody ran it on macOS, and the RFC requires that. The status says so rather than calling it done.
- **Concurrent runs against "never lose my tasks" is undecided.** Either add a lock, or reword the goal to "never lose tasks to a crash". This is the first question an interactive `/verify-prd` would have asked you. The run had nobody to ask, so it built no lock and recorded the question.
- **Names, formats and exit codes nobody confirmed** are listed in RFCS.md Open conflict 2 and in each RFC: `TD_FILE`, `~/.td.json`, the `1 [ ] text` line format, and exit codes 0/1/2. `/implement-rfc` showed them with each plan, but nobody was there to answer.

Is this too much process for a to-do list? Decide for yourself. 55 rules and 66 tests for 386 lines of code is a lot. Most of it comes from one sentence in the idea, "it must never lose my tasks", which the workflow took at its word. In an interactive run you would trim it at the first question.

## What this run changed in the workflow

The first round of cold readers got only PRD.md, FEATURES.md, RULES.md and one RFC, as the instructions said at the time. Most of what they reported was about interfaces that a predecessor RFC already defined, and the real gaps were buried under that. `/generate-rfcs` now gives each cold reader the RFCs it depends on, too. The second round ran that way and its reports are much shorter.

The run's commit history is not part of this repository. The commits, in order: the idea, the five generating commands, two rounds of cold reads each followed by a fix commit, `/test-strategy`, then `/implement-rfc` and `/review-rfc` for each RFC, a second RFC-005 commit for the Python 3.10 run, and `/workflow-status`.
