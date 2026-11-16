# Example: td, a tiny to-do list, from idea to reviewed code

This folder is one complete run of the workflow on a very small product: a command-line to-do list called `td`. It goes from a ten-line idea to working, tested, reviewed code. The url-shortener example stops before implementation; this one doesn't.

Every command ran on **Claude Sonnet 5.5** (`claude-sonnet-5-5`), cold reads included. Each step was its own agent with a fresh context and no notes, and it saw only the skill's instructions and the project files. Nobody answered questions during the run. Wherever a command would have asked you something, it decided, marked the decision **(assumption)** and listed it, so you can see what an interactive run would have put in front of you.

The run has two parts:

- **Part 1**, on 2026-11-15, used the 3.1.0 skills: `/create-prd` through `/review-rfc` and `/workflow-status`.
- **Part 2**, on 2026-11-15 and 16, used the 3.2.0 skills. It re-reviewed the code, sent three RFCs back, took the open lock question through `/manage-changes`, and built and reviewed the lock.

The files from part 1 that part 2 did not touch (the PRD's structure, the 56 rules, the first five RFCs' design) are 3.1.0 output. 3.2.0 would write fewer rules for a product this size, but regenerating them would have changed everything built on them.

Nothing here is hand-edited, including this folder's `CLAUDE.md` and `AGENTS.md`, which `/generate-rules` wrote. There are two exceptions:

- this README;
- two lines in [RFCS.md](RFCS.md), written by the person running the example: the note that RFC-006 passed its third cold read, and the roadmap line saying it could start.

## Try it

```bash
cd examples/todo-cli
export TD_FILE=/tmp/td-demo.json
./td add buy milk
./td add call the bank
./td done 1
./td list
python3 -m unittest discover tests      # 85 tests, about 20 seconds
```

## The run, step by step

| Step | What it wrote |
|---|---|
| The idea | [IDEA.md](IDEA.md): ten lines in the user's words, and the only input |
| `/create-prd` | [PRD.md](PRD.md): 9 functional and 9 non-functional requirements, 8 decisions, 12 open questions marked (assumption) |
| `/verify-prd` | [PRD-REVIEW.md](PRD-REVIEW.md): 3 High, 7 Medium and 3 Low findings, and fixes to PRD.md |
| `/extract-features` | [FEATURES.md](FEATURES.md): 23 features |
| `/generate-rules` | [RULES.md](RULES.md): 56 checkable rules, and `CLAUDE.md` / `AGENTS.md` pointing at them |
| `/generate-rfcs` | 5 RFCs in [RFCs/](RFCs/) and the index [RFCS.md](RFCS.md), with 10 open conflicts listed |
| cold reads, 2 rounds | [cold-reads/](cold-reads/): one clean-context reader per RFC, then fixes, then a second round of readers on the fixed RFCs |
| `/test-strategy` | [TEST-STRATEGY.md](TEST-STRATEGY.md): one row per acceptance criterion |
| `/implement-rfc` ×5, `/review-rfc` ×4 | the first version of [td](td), its tests, and round 1 of the reviews in [reviews/](reviews/) |
| **part 2 (3.2.0)** | |
| `/review-rfc` round 2 on RFC-001 to RFC-003 | all three sent back with Changes requested |
| `/manage-changes` | [changes/CHANGE-REQUEST-001.md](changes/CHANGE-REQUEST-001.md): add a lock for concurrent runs, as RFC-006 |
| fix rounds and re-reviews | RFC-001 took two more fix rounds and was Reviewed in round 4; RFC-002 and RFC-003 were Reviewed in round 3 |
| RFC-006, 3 cold reads | 5 guesses, then 3, then none |
| `/implement-rfc`, `/review-rfc` | RFC-006 (the lock), and a rerun of RFC-005's release checks on Python 3.10 to 3.13 |
| `/workflow-status` | [WORKFLOW-STATUS.md](WORKFLOW-STATUS.md): where the project stands |

The result is [td](td) (478 lines), [tests/](tests/) (85 tests), and six reviewed RFCs.

## What the workflow caught

On a product this small, most of the value went into things nobody would think to write down.

**Part 1**

- **`/verify-prd`:** the idea says "it must never lose my tasks, even if it crashes halfway through saving". The first PRD broke that in two ways, and both were fixed in PRD.md before any code existed:
  - It saved by writing a temp file and renaming it over the old one, with no `fsync`, so a power cut could still leave an empty file.
  - It promised never to reuse ids, but stored nothing that remembered the highest id ever issued.
- **Cold reads:** two tests would have passed even with the feature broken.
  - The `td list | head -1` test produced less output than a pipe buffer holds, so the broken-pipe code never ran.
  - The `LANG=C` test passed regardless, because Python switches the C locale to UTF-8 by itself.

**Part 2**

- **Concurrent runs:** the 3.1.0 reviews passed code that two overlapping `td add` runs could make lose a task, against "never lose my tasks". The 3.2.0 `/review-rfc` blocks on an open conflict against a goal, so it sent RFC-001 to RFC-003 back. The lock in RFC-006 closes it.
- **Breaking the code on purpose:** the reviewers broke the code to see whether the tests noticed. Each miss became a blocking issue and a new test:
  - A JSON file nested 200,000 levels deep crashed `td` with a traceback instead of a clean error.
  - `td done ٣` (an Arabic-Indic 3) could have marked task 3: no test covered non-ASCII digits.
  - Loosening the check that `next_id` is positive left all 74 tests green.
- **RFC-006's first cold read:** one acceptance criterion scanned the source for forbidden imports, and it contradicted the design two paragraphs above it. That kind of criterion is now banned by the prompt.
- **RFC-006's second cold read:** the RFC could be read as retrying a permission error for 10 seconds before reporting it.

## What the workflow did not catch

After part 1, an outside critic (Fable 5.2, given the code and nothing else) found bugs that none of the six reviews reported. As of the end of part 2 these are still in [td](td):

- `td add call mom -h` prints the help, saves nothing and exits 0, so the task you typed is gone. The help text says to put `--` before text that starts with `-`, but `-h` at the end is easy to type by accident.
- Saving replaces the file with a new one created with the default permissions. A `chmod 600 ~/.td.json` is undone by the next `td add`.
- `td add x >&-` (stdout closed) saves the task and then reports `td: unexpected error: AttributeError` with exit 1, so a script would think the add failed.

The reviewers break the code against the RFC's criteria and the PRD's properties. None of these three is in either, and that is where a review driven by the spec stops seeing.

## Where it stands

From [WORKFLOW-STATUS.md](WORKFLOW-STATUS.md):

- **All six RFCs are Reviewed**, with no blocking issues in the last round of any review. `trace-check.py` reports 0 failures.
- **The release is not done.** The tests pass on Python 3.10, 3.11, 3.12 and 3.13 on Linux, but nobody ran them on macOS. That run is item 1 of the release checklist in [RFCS.md](RFCS.md), and it no longer keeps an RFC In progress forever.
- **The lock was decided on the user's behalf.** Part 1 left "concurrent runs against never lose my tasks" as an open question. The person running the example picked the safer answer, a lock, and CR-001 says in so many words that the user has not confirmed it. If you are the user, you could reverse it and reword the goal to "never lose tasks to a crash".
- **Names, formats and exit codes nobody confirmed** are still listed in Open conflict 2: `TD_FILE`, `~/.td.json`, the `1 [ ] text` line format, and exit codes 0/1/2.
- **16 follow-ups are open** in RFCS.md. They are non-blocking findings from the reviews; 10 others were closed in the fix rounds.

Is this too much process for a to-do list? Decide for yourself. 56 rules and 85 tests for 478 lines of code is a lot. Most of it comes from one sentence in the idea, "it must never lose my tasks", which the workflow took at its word. An interactive run would have asked you about it at `/verify-prd`, and you could have trimmed it there.

## What this run changed in the workflow

- **Cold readers now get the RFCs an RFC depends on.** In part 1, the first round of readers got only PRD.md, FEATURES.md, RULES.md and one RFC. Most of what they reported was about interfaces a predecessor already defined. In the second round, each reader also got the predecessor RFCs, and its report was much shorter.
- **Several 3.2.0 changes come from part 1:**
  - cold reads capped at five guesses;
  - assumptions that may not contradict a goal;
  - reviews that block on such a conflict;
  - criteria that describe behavior instead of scanning the source;
  - a release checklist for checks that need another machine.

The run's commit history is not part of this repository. The commits are one per command, in the order of the table above.
