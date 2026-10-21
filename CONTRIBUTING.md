# Contributing

Contributions are welcome: new MCP tools, fixes to the bridge, better Lua probes, and
experiment scripts that document what the game API actually does.

Everything lands through a pull request. Nothing is pushed straight to `main`.

## What is worth contributing

- **New MCP tools** in `server.py`. Open an issue first if the tool changes an existing
  result shape or needs a new endpoint.
- **Experiments** in `experiments/`: a Lua script that answers one question about the game
  API, with a header stating what it proved. Negative results are useful too.
- **Fixes** with a reproduction: the failing test, the log line, or the packet dump.
- **Docs** in `docs/`, or corrections to `README.md` when it no longer matches behaviour.

Not accepted: detection evasion, credential or session stealing, anything that attacks
other players' accounts, or code that only works on your machine.

## Before you open a pull request

1. Fork the repo and branch from `main`.
2. Make the change small enough to review in one sitting. One topic per PR.
3. Run the tests that exist today:

       python3 -m venv .venv
       .venv/bin/pip install "mcp[cli]" lupa
       .venv/bin/python -m unittest tests_gt.py
       .venv/bin/python test_bridge_lua.py

4. If your change touches a tool, run it against a real device and keep the output. A PR
   that says "tested" without a line of output is treated as untested.
5. If your change touches `bridge.lua`, run it in game at least once. The harness stubs the
   game API and cannot catch everything.
6. Review your own diff first. Read it as if someone else wrote it.

## AI-assisted code

AI-written code is allowed. It is held to the same bar as hand-written code, which means:

- You ran it. Not "it compiles", not "the model said it works": you executed the tool or
  the test and you have the output.
- The tests pass locally, and you added one when you fixed a bug.
- You understand every line you are submitting. If a reviewer asks why a line exists, "the
  model wrote it" is not an answer.
- No invented API calls. If a Bothax function is not in `docs/`, prove it exists with
  `api_list()`, `api_doc()`, or a `lua_eval` result before using it.
- No fabricated evidence. A pasted output that you did not produce gets the PR closed.

Unreviewed, unrun AI output is the main reason PRs get rejected here. Keep the diff small
and show the run.

## Code rules

- English everywhere: identifiers, comments, docstrings, log lines, JSON keys.
- Comments explain why. If the line already says what it does, drop the comment.
- No em dash characters. Use a colon, comma, or parentheses.
- The first line of a tool docstring is the description MCP clients display. One sentence,
  no leading blank line.
- Tool results are JSON with `indent=2`. Do not rename existing keys; add new ones.
- Errors start with `ERROR:` and say what to do next. Tools are wrapped in `_safe`, so
  raising is fine.
- Lua templates that go through `.format()` need `{{}}` for literal braces. Templates that
  are not formatted must not contain `{{}}`.
- Hook labels must be numeric. A string label registers nothing and can break hooks that
  already work.

## Adding an experiment

`experiments/` is a record of what the game API does, including dead ends. A good one:

    -- What question this script answers.
    -- Result: what actually happened, with the numbers you saw.

Requirements: no credentials, no absolute paths from your machine, no infinite loops that
cannot be stopped, and the result line filled in. If the probe failed, say it failed and
what the failure looked like.

## Review

- A maintainer reads the diff and the evidence you pasted.
- Expect a request for the exact command and its output if the PR claims a live result.
- Changes to packet formats, `_Bridge`, or the polling protocol need a second look at the
  traps listed in `README.md` and `AGENTS.md`.
- Review can take a while. A polite ping after a week is fine.

Once merged, the PR author is credited in the commit history. There is no CLA: by opening
a pull request you agree that your contribution ships under the repo's [MIT license](LICENSE).

## Reporting a problem

Open an issue with: what you ran, what you expected, what happened, and the relevant lines
from `debug_log()` or `logcat`. If the bridge is involved, include `bridge_status()` and the
`bridge_doctor()` output.
