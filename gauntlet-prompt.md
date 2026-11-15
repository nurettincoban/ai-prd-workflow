You are running a quality gate in an RFC-driven workflow. An artifact moves to the next stage only after it survives a critic whose job is to break it. You orchestrate the gate; you are not the critic, and you must not soften what the critic finds.

The gate to run is one of:

| Gate | Run it after | Under attack | The critic's question |
|---|---|---|---|
| `prd` | `/verify-prd` | PRD.md, PRD-REVIEW.md | "What in this PRD would make a competent team build the wrong thing, or be unable to build it at all?" |
| `plan` | `/generate-rfcs` and `/test-strategy` | FEATURES.md, RULES.md, RFCs/, RFCS.md, TEST-STRATEGY.md, against PRD.md | "Where will following this plan in order fail: a gap, a wrong order, a criterion nobody can test?" |
| `rfc <id>` | `/review-rfc <id>` | the code for RFC-[ID], its RFC and `reviews/REVIEW-RFC-[ID].md` | "What did the implementation get wrong that the review passed?" |

If no gate was named, pick the earliest one whose inputs exist and that has no PASS in GAUNTLET.md, and say which you picked.

## 1. MECHANICAL GATE

If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it (`python3 <path>/trace-check.py .`). Any FAIL is a Blocker: the critic's time is wasted on a document whose IDs do not even resolve. For `rfc <id>`, also run the project's build and test commands and paste the output.

## 2. THE CRITIC

The critic must not be the author. The model that wrote or fixed these files in this conversation has read past their gaps already, and a second read by the same reasoning finds the same nothing. In order of preference:

1. In Claude Code, start the `gauntlet-critic` agent (`prd-workflow:gauntlet-critic` with the plugin). It runs on Fable 5.2 (`claude-fable-5-2`), a different model from the one that usually writes the artifacts, so it does not share the author's blind spots.
2. Otherwise, start a subagent with a clean context, on a different model from the author's if you can choose one.
3. If you cannot start one, stop and tell the user to run `/gauntlet <gate>` in a new session, ideally on a different model. Do not play the critic yourself.

Give the critic only file paths, the gate's question, and this brief, never your own summary of the files:

> You did not write these files and owe them nothing. Read them and find the ways they fail. For each finding give: severity (**Blocker**: building on this as written produces wrong or unbuildable work; **Major**: likely rework; **Minor**: worth fixing), the file and section, a quote, and the concrete failure it causes. A finding without a quote and a consequence is an opinion; leave it out. Do not suggest stylistic edits, and do not praise. If you find no Blocker, say so plainly -- an invented Blocker is as harmful as a missed one. End with a score from 0 to 10 for how safely the next stage can build on these files, and one sentence on the weakest point.

If a critic you started fails to run -- the model is unavailable, for example -- fall back to the next option and record which one ran.

## 3. VERDICT AND FIXES

- **PASS**: no Blocker from either the mechanical gate or the critic.
- **BLOCKED**: at least one Blocker. Show every Blocker and Major to the user verbatim. Fix them through the command that owns the file (`/verify-prd`, `/generate-rfcs`, `/implement-rfc`, `/manage-changes`), or directly if the user approves, then run the gate again with a fresh critic.

You may dispute a finding only by quoting the text that refutes it; record the dispute and let the user decide. Never drop a finding silently. After three BLOCKED rounds on the same gate, stop and ask the user to decide: a document that keeps failing usually has a decision missing, which a fourth critic cannot supply.

The user may override a BLOCKED gate. Record the override and the reason; the next stage will see it.

## 4. RECORD IT

Append a round to GAUNTLET.md in the project root (create it with a one-line purpose if it does not exist). Never rewrite earlier rounds: the ledger is the evidence that each stage was challenged before work was built on it.

```
## Gate: plan · Round 2 · 2026-11-15
**Verdict**: BLOCKED | PASS | OVERRIDDEN
**Critic**: gauntlet-critic on claude-fable-5-2 (or: what ran instead)
**Score**: 6/10 -- weakest point in one sentence
**Mechanical gate**: trace-check PASS / FAIL lines
| # | Severity | Where | Finding | Resolution |
```

Resolution is Fixed (with what changed), Disputed (with the quote), or Open. Then tell the user the verdict, the open Blockers, and the next command to run.
