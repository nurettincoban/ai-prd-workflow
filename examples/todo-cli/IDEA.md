# The idea, in the user's words

I want a tiny command-line to-do list called `td`. I live in the terminal and every to-do app I try is too much.

Answers to the questions an interviewer would ask:

- Who is it for: me and people like me, developers who work in a terminal. One user, one machine. No accounts, no sync, no server.
- What it does: add a task, list tasks, mark a task done, remove a task. That's it for v1. Maybe clearing all done tasks.
- Language: Python, standard library only, so it runs anywhere Python 3.10+ is installed with nothing to pip install.
- Where data lives: one JSON file in the home directory, and I want to be able to point it somewhere else with an environment variable.
- It must never lose my tasks, even if it crashes halfway through saving.
- Output should be plain text that I can pipe into grep. Errors go to stderr with a non-zero exit code.
- Platforms: macOS and Linux for sure. Windows would be nice but I won't test it.
- Success: I use it every day for a month and never open the JSON file by hand.
- Not in v1: due dates, priorities, tags, colors, multiple lists.
- Timeline: a weekend.
