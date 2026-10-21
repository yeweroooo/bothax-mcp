# AGENTS.md

Instructions for coding agents working in this repo. `README.md` explains the product;
this file explains how to change it without breaking the control channel.

## What this is

An MCP server (stdio) that drives Growtopia on Android over two paths:

- ADB: taps, swipes, screenshots, files, processes.
- Lua bridge: `bridge.lua` runs inside the game process and polls an HTTP server on
  `127.0.0.1:8770`, reached through `adb reverse tcp:8770 tcp:8770`.

Files:

    server.py           MCP tools + HTTP endpoints + command queue
    bridge.lua          in-game script: poll, execute, serialise, capture
    pngio.py            PNG crop helper for screenshot_crop
    tests_gt.py         regression tests, no device
    test_bridge_lua.py  bridge.lua under Lua 5.4 with stubbed APIs
    test_server.py      stdio smoke test, needs a device
    experiments/        probes, each stating its result
    docs/               Bothax API reference, client configs

## Commands

    python3 -m venv .venv
    .venv/bin/pip install "mcp[cli]" lupa

    .venv/bin/python -m unittest tests_gt.py     # fast, no device
    .venv/bin/python test_bridge_lua.py          # Lua harness
    .venv/bin/python test_server.py              # needs a device and the game

    GT_BRIDGE_PORT=8791 .venv/bin/python server.py --http-only    # isolated bridge
    PATH="<sdk>/platform-tools:$PATH" .venv/bin/python server.py   # MCP over stdio

Never leave a stray process on the bridge port. If a port is already held, the server
enters `attached` mode and forwards Lua commands to the owner, which is correct for a
client but hides your own changes; restart the owner when you are testing server code.

## Verification rules

- A claim needs evidence in this repo. Run the tests, then exercise the tool live and
  quote the output. "Should work" is not a result.
- Regression first: add the failing test, watch it fail for the stated reason, then fix
  the cause. Do not keep a patch for a hypothesis that turned out wrong.
- Lua changes need `test_bridge_lua.py` plus one live call, because the harness stubs the
  game API.
- After editing `server.py`, restart the detached server before testing tools. A stale
  process serves the old code and makes correct changes look broken.
- Confirm the chain end to end after any restart: `bridge_status()` shows
  `"polling": true`, then one `lua_eval` returns something.

## Code conventions

- English only in identifiers, comments, docstrings, log lines, and JSON keys.
- Comments explain why, not what. If the line already says it, delete the comment.
- No em dash characters anywhere. Use a colon, comma, or parentheses.
- The first line of a tool docstring is the description MCP clients show. Keep it one
  sentence and do not start it with a blank line.
- Tool results are JSON with `indent=2`. Keep key names stable: `from`, `to`, `steps`,
  `move_counts`, `objects_before`, `sent`, `objects_left`, `inventory_delta`, `reason`,
  `world_pos`.
- Error strings start with `ERROR:` and name the fix when there is one. Every tool is
  wrapped in `_safe`, so raising is acceptable and will not kill the session.
- Lua templates are `str.format()` templates: literal braces must be doubled. A template
  that is not formatted must not contain `{{}}`; Lua would read it as a table holding an
  empty table.
- Hook labels must be numeric. String labels register nothing and can disable hooks that
  already work until the game restarts.

## Protocol facts that must not drift

    place   {type=3,  state=0, value=<item id>, px=x, py=y, x=pos.x, y=pos.y}
    break   {type=3,  state=0, value=18, px=x, py=y}
    collect {type=11, state=0, value=<object oid>, px=obj.pos.x, py=obj.pos.y}
    drop    "action|dialog_return\ndialog_name|drop\nitem_drop|<id>|\nitem_count|<n>\n"

- `collect` uses the object oid, not the item id. `item_id=0` means everything.
- The trailing pipe in `item_drop|<id>|` is required; without it the server ignores the
  drop.
- `MakeRequest` returns `status = 0` with `error = false` on success. Judge by `error`
  and `content`.
- `_Bridge.claim()` expires a quiet holder after `ACTIVE_TTL` (20 s). Removing that expiry
  makes every new instance answer `none` forever.
- `reap()` re-sends only commands whose instance was replaced, never slow ones.

## Things that look like bugs but are not

- The avatar does not move when a position packet is sent. The client resends its own
  position; use `FindPath` through `go_to`.
- The capturer never shows packets the script itself sends. Verify injection through
  `GetTile`, `GetInventory`, or `GetObjectList` instead.
- A `--http-only` process exiting with status 3 means another instance owns the port.
- Empty tool output with a healthy `/health` usually means the executor's API list is not
  ticked, or `adb reverse` is gone.

## Commits

Short imperative subject, then the reason. Mention what was verified. Do not commit
`.venv`, logs, pid files, or scratch scripts; probes belong in `experiments/` with a
header stating what they proved.

External contributions arrive through pull requests. Their bar is `CONTRIBUTING.md`: tests
run, live evidence pasted, English comments, no renamed JSON keys. Review the diff against
these points before merging.
