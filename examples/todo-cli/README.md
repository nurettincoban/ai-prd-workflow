# Example: td, a tiny to-do list, from idea to reviewed code

This folder is one complete run of the workflow on a very small product: a command-line to-do list called `td`. It goes from a ten-line idea to working, tested, reviewed code. The url-shortener example stops before implementation; this one doesn't.

Every command ran on **Claude Sonnet 5.5** (`claude-sonnet-5-5`), cold reads included. Each step was its own agent with a fresh context and no notes, and it saw only the skill's instructions and the project files. Nobody answered questions during the run. Wherever a command would have asked you something, it decided, marked the decision **(assumption)** and listed it, so you can see what an interactive run would have put in front of you.

The run has two parts:

- **Part 1**, on 2026-11-15, used the 3.1.0 skills: `/create-prd` through `/review-rfc` and `/workflow-status`.
- **Part 2**, on 2026-11-15 and 16, used the 3.2.0 skills. It re-reviewed the code, sent three RFCs back, took the open lock question through `/manage-changes`, and built and reviewed the lock. Then an outside critic's bug report went through `/manage-changes` too, and the RFCs it touched went back for fixes and review.

The files from part 1 that part 2 did not touch (the PRD's structure, the 56 rules, the first five RFCs' design) are 3.1.0 output. 3.2.0 would write fewer rules for a product this size, but regenerating them would have changed everything built on them.

Nothing here is hand-edited, including this folder's `CLAUDE.md` and `AGENTS.md`, which `/generate-rules` wrote. There are two exceptions:

- this README;
- two lines in [RFCS.md](RFCS.md), written by the person running the example: the note that RFC-006 passed its third cold read, and the roadmap line saying it could start;
- [changes/BUG-REPORT-001.md](changes/BUG-REPORT-001.md), the bug report, which the person running the example wrote from the critic's findings. Like [IDEA.md](IDEA.md), it is input, not output.

## Try it

```bash
cd examples/todo-cli
export TD_FILE=/tmp/td-demo.json
./td add buy milk
./td add call the bank
./td done 1
./td list
python3 -m unittest discover tests      # 91 tests, about 20 seconds
```

## The run, step by step

| Step | What it wrote |
|---|---|
| The idea | [IDEA.md](IDEA.md): ten lines in the user's words, and the only input |
| `/create-prd` | [PRD.md](PRD.md), at the time: 9 functional and 9 non-functional requirements, 8 decisions, 12 open questions marked (assumption). Later commands added to it |
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
| `/manage-changes` on a bug report | [changes/CHANGE-REQUEST-002.md](changes/CHANGE-REQUEST-002.md): two bugs filed against RFC-001 and RFC-002, four changes left for the user |
| fix rounds and re-reviews | RFC-001 Reviewed in round 5; RFC-002 fixed, reviewed, sent back, fixed again, and now waiting on the user |
| `/workflow-status` | [WORKFLOW-STATUS.md](WORKFLOW-STATUS.md): where the project stands |

The result is [td](td) (504 lines), [tests/](tests/) (91 tests), five reviewed RFCs and one waiting for a decision.

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

## What the reviews missed, and what happened to it

After part 1, an outside critic (Fable 5.2, given the code and nothing else) found bugs that none of the reviews had reported. A second critic, after the lock was built, could not make `td` lose a task, but found the rest still there and a few more. Among them:

- `td add call mom -h` prints the help, saves nothing and exits 0, so the task you typed is gone.
- A save resets a `chmod 600` data file to 644.
- `td add x >&-` (stdout closed) saves the task, then exits 1, so a script that retries adds it twice. That breaks the project's own rule SAFE-6, which three review rounds said held.
- Deleting the `flush()` before the `fsync` left all 85 tests green, so the "power cut leaves an empty file" fix was not protected.
- Ctrl-C in the first few milliseconds printed a Python traceback in about half the tries.

The person running the example wrote these up as [a bug report](changes/BUG-REPORT-001.md) and ran `/manage-changes` on it. It sorted them as the prompt says:

- **Two were bugs**, where the RFC was right and the code or its tests were wrong: the fsync test and the early Ctrl-C. They became blocking follow-ups, and RFC-001 and RFC-002 went back to Changes requested.
- **Four were changes** to what `td` should do, because the RFCs pin today's behavior: `-h` after the text, the file mode, exit 1 after a save, and naming the data file in `--help`. Nobody could accept them, so they wait in [CHANGE-REQUEST-002.md](changes/CHANGE-REQUEST-002.md), and no code was written for them.

What happened next:

- **RFC-001** got a test that checks the file's size at the moment of `fsync`, and passed review round 5.
- **RFC-002's first fix claimed the Ctrl-C traceback was gone in 60 of 60 tries.** The reviewer reran it, got 29 of 60, and sent it back. The claim came from a shell loop that cannot deliver Ctrl-C to a background job at all. The second fix measured with a real driver: 72 tracebacks in 252 timed tries before, 48 after, all of them inside Python's own start-up, before `td` runs a line.
- The reviewer also made "exit 1 after a save" blocking for RFC-002, because it breaks SAFE-6. Fixing it needs the user's answer on Change 3, so **RFC-002 is In progress, waiting for that decision.**

Not everything the workflow can see, it checks. RFC-003 has the same SAFE-6 problem and is still marked Reviewed. Open conflict 12 names it, but this run's RFCS.md predates the conflict format that `trace-check.py` reads, so the check passes.

## Where it stands

From [WORKFLOW-STATUS.md](WORKFLOW-STATUS.md):

- **Five of six RFCs are Reviewed.** RFC-002 is In progress: its last fix has not been reviewed, and it waits on the user's answer to Change 3.
- **Waiting on the user:**
  - the four changes in CHANGE-REQUEST-002;
  - the lock (CR-001), which the person running the example accepted and the user has not;
  - Open conflict 11 (Ctrl-C during Python start-up);
  - the names, formats and exit codes nobody confirmed (Open conflict 2).
- **The release is not done.** The tests pass on Python 3.10 to 3.13 on Linux, but nobody ran them on macOS. That is item 1 of the release checklist in [RFCS.md](RFCS.md).
- **Also open:** 20 non-blocking follow-ups in RFCS.md (13 others were closed in fix rounds), and TEST-STRATEGY.md is behind RFC-006.

Is this too much process for a to-do list? Decide for yourself. 56 rules and 91 tests for 504 lines of code is a lot. Most of it comes from one sentence in the idea, "it must never lose my tasks", which the workflow took at its word. An interactive run would have asked you about it at `/verify-prd`, and you could have trimmed it there.

## What this run changed in the workflow

- **Cold readers now get the RFCs an RFC depends on.** In part 1, the first round of readers got only PRD.md, FEATURES.md, RULES.md and one RFC. Most of what they reported was about interfaces a predecessor already defined. In the second round, each reader also got the predecessor RFCs, and its report was much shorter.
- **Several 3.2.0 changes come from part 1:**
  - cold reads capped at five guesses;
  - assumptions that may not contradict a goal;
  - reviews that block on such a conflict;
  - criteria that describe behavior instead of scanning the source;
  - a release checklist for checks that need another machine;
  - a bug in a Reviewed RFC filed as a blocking follow-up, which the fix round closes.

The run's commit history is not part of this repository. The commits are one per command, in the order of the table above.
