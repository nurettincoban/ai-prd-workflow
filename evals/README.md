# Evals

A [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) suite that measures what the workflow adds over a plain agent. Every case runs twice: with this plugin loaded, and without it. The difference (Δ) is what the workflow contributed.

| Case | Fixture | What a grader checks |
|---|---|---|
| `verify-prd-finds-planted-problems` | The v2.0 url-shortener `PRD.md` | The review names one of ten problems found by hand, such as the 10,000 vs 10M scale contradiction or HTTP 301 caching breaking click analytics |
| `workflow-status-finds-planted-gaps` | All v2.0 url-shortener artifacts | The status report names one of the cross-document gaps, such as F7 having no RFC or no RFC building the UI |
| `extract-features-keeps-ids` | v2.0 `PRD.md` + `FEATURES.md` + RFCs, with two requirements added to the earliest category | Existing feature IDs keep their meaning and the new features take F19 and F20 — the RFCs cite features by number |

The fixtures come from [`examples/url-shortener/before/`](../examples/url-shortener/before/), and the problems they contain are listed in [`examples/url-shortener/README.md`](../examples/url-shortener/README.md).

## Running it

You need Claude Code 2.1.269 or later. From the repository root:

```bash
claude plugin eval . --scaffold --allow-tools Write Edit
```

- `--scaffold` lets each case's `scaffold.sh` copy its fixture into the run's empty workspace and commit it to a throwaway git repository.
- `--allow-tools Write Edit` lets the agent write `PRD-REVIEW.md` and update `FEATURES.md`. The suite never needs Bash, so it also runs on native Windows.
- Every run is a real model call on your account. The full suite is 3 cases × 3 runs × 2 arms, plus the agent's own work on each. Add `--max-cost-usd 10` to cap spend, and `--case <name> --runs 1 --ablation none` to iterate on one case cheaply.

## How the graders work

All graders except `skill-fired` are regular expressions. They cost nothing, and they read a long file the same way every run. Each was checked two ways before it was committed:

| Case | Real fresh-context run of the command | The fixture itself |
|---|---|---|
| `verify-prd-finds-planted-problems` | 10 of 10 graders match | 0 of 10 match |
| `workflow-status-finds-planted-gaps` | 6 of 7 match — the miss is real: the run did not flag the stale Node and React versions | 0 of 7 match |
| `extract-features-keeps-ids` | 7 of 7 match (new features became F19 and F20; F1–F18 unchanged) | on a copy with F7 renumbered, the F7 grader fails |

A grader that matched the fixture would give credit to an agent that merely quoted a problem without noticing it; four early patterns did exactly that and were tightened.

`skill-fired` checks that the skill was actually invoked. In a two-arm run it is reported but not scored, since it can never pass without the plugin.

A regex can still reward an agent that mentions a problem without understanding it, and miss one phrased in an unexpected way. Treat a single run's score as noisy, and compare Δ across the default three runs.
