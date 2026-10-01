## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- next to these instructions, or in the project's `scripts/` folder -- run `python3 trace-check.py .` and fix every FAIL it reports. It checks IDs, coverage and dependencies mechanically, which reading cannot do reliably.
- State that you ran this check and what it turned up.
