# bothax-mcp

An MCP server that drives Growtopia on Android. It has two control paths: **ADB** for
taps, swipes, screenshots, files, and processes, and a **Lua bridge** for the Bothax
(BINTERNAL) API that only exists inside the game process. 34 tools in total.

The repo holds `server.py` (MCP + HTTP), `bridge.lua` (the script that runs in game),
three test files, `experiments/` with the probe scripts and what each of them proved,
and `docs/` with the Bothax API reference plus client setup notes.

## Why it has to go through Lua

The Bothax API lives inside the game process. There is no socket, CLI, or separate
library that can call `GetLocal`, `GetTiles`, `SendPacketRaw`, or `FindPath`. The only
way in is to run Lua inside that process and connect it back to the PC:

    bridge.lua  --HTTP-->  127.0.0.1:8770  --adb reverse-->  server.py on the PC

`adb reverse tcp:8770 tcp:8770` forwards port 8770 on the device to port 8770 on the PC.
Without that mapping, `MakeRequest` inside the game goes nowhere.

## Install

    python3 -m venv .venv
    .venv/bin/pip install "mcp[cli]"
    .venv/bin/pip install lupa        # only needed to compile-test the Lua templates

Requirements: `adb` on `PATH` (`ANDROID_HOME` and `ANDROID_SDK_ROOT` are also read),
Python 3.10 or newer, and a device with USB debugging or wireless adb.

## Device setup, once per boot

1. `adb devices`, or `adb connect <ip>:5555`, until the device shows up as `device`.
2. Start the server from your MCP client, or run `python server.py --http-only` for
   manual control over `curl`.
3. `install_bridge()`: pushes `bridge.lua` to
   `/sdcard/Android/media/com.rtsoft.growtopia/scripts/` and installs `adb reverse`.
4. In game, open the BINTERNAL executor, enable the API list, then run `bridge.lua`.
5. `bridge_status()` must answer `"polling": true`.

If a step fails, `bridge_doctor()` checks adb, the reverse mapping, and polling one by
one, then repairs a missing mapping.

## Connecting an MCP client

The server speaks plain stdio MCP:

```json
{
  "mcpServers": {
    "bothax-mcp": {
      "command": "/path/to/bothax-mcp/.venv/bin/python",
      "args": ["/path/to/bothax-mcp/server.py"]
    }
  }
}
```

Hermes uses the `mcp_servers` key with the same shape. Config snippets for other clients
are in [docs/clients.md](docs/clients.md).

If port 8770 is already held by a `--http-only` process, the server starts in `attached`
mode: Lua commands are forwarded to the port owner and the ADB tools keep working in
this process.

## Tools

| Tool | What it does |
|---|---|
| `device_info` | model, Android version, game state, bridge state |
| `screenshot` / `screenshot_crop` / `panel_crop` | capture the screen, crop a region, zoom the mod panel |
| `tap` / `swipe` / `key` / `type_text` | screen and ASCII text input |
| `launch_game` / `stop_game` | start or stop the game, then verify the process |
| `logcat` | device log, optionally filtered |
| `install_apk` | install an APK and report the real failure |
| `push_script` / `list_scripts` | manage scripts in the game folder |
| `install_bridge` | push `bridge.lua` and install `adb reverse` |
| `bridge_status` | whether the in-game script is polling |
| `bridge_doctor` / `adb_reconnect` | diagnose and recover the transport |
| `lua_eval` | run Lua in the game process and return the result |
| `game_snapshot` | player, world, inventory, object count, avatar tile |
| `go_to` | move the avatar to a tile (`CheckPath`, `FindPath`, position check) |
| `find_path` | BFS route to the nearest matching object plus an ASCII map; `move=true` also moves the avatar |
| `list_objects` | ground objects: oid, item id, name, tile |
| `collect_objects` | pick up objects with a `type=11` packet, filterable by item and radius |
| `drop_item` | drop an item, `amount=0` drops the whole stack |
| `traffic_start` / `traffic_dump` / `traffic_stats` / `traffic_stop` / `traffic_clear` | capture packets inside the game |
| `debug_log` | bridge log: commands, results, errors, `LogToConsole` output |
| `debug_state` | combined diagnostic summary |
| `api_list` / `api_doc` | Bothax function and structure documentation |

`lua_eval` is the main door: anything the executor can do can be sent from here.

```python
lua_eval("return GetLocal().name")
lua_eval("local w=GetWorld(); return {w.name, w.width, w.height}")
lua_eval("return #GetTiles()")
```

## Packets verified live

    place   {type=3,  state=0, value=<item id>, px=x, py=y, x=pos.x, y=pos.y}
    break   {type=3,  state=0, value=18, px=x, py=y}          -- 18 = Fist
    collect {type=11, state=0, value=<object oid>, px=obj.pos.x, py=obj.pos.y}
    drop    "action|dialog_return\ndialog_name|drop\nitem_drop|<id>|\nitem_count|<n>\n"

- `collect` carries the **object oid**, not the item id. One object can hold several
  units, so item count and object count differ. The avatar does not have to move.
- One `drop` packet is enough. The trailing pipe after the id (`item_drop|5026|`) is
  required.
- `break` is repeated until `GetTile(x,y).fg` changes. The hit count equals
  `GetItemInfo(id).breakhit`.

## Bridge protocol

Plain text, not JSON, so the Lua side needs no parser.

| Endpoint | Answer |
|---|---|
| `/health` | `ok`, marks this port as owned by the server |
| `/poll?sid=` | `<id>|<lua code>` or `none` |
| `/result` | result from the game (POST), with a GET fallback |
| `/ack` | confirms a command was taken |
| `/diag?msg=` | debug message from inside the game, written to the log |
| `/hello?sid=` | instance registration |
| `/status` / `/enqueue` | used by attached mode |
| `/call?tool=&args=` | manual control without an MCP client |

`MakeRequest` in this build returns `status = 0` (not 200) with `error = false` on
success, so judge by `error` and `content`, never by status. Lua results are serialised by
`enc()` (depth 5, 120 entries per table), which means strings come back escaped and the
server unescapes them before parsing.

### Multiple instances

Every `Execute` leaves a thread polling forever. `bridge.lua` sends `/hello?sid=<random>`
on start. The server serves one sid at a time, but that turn expires (`ACTIVE_TTL`, 20
seconds, in `_Bridge.claim()`): once the holder goes quiet a new instance takes over.
Without the expiry a stale sid makes every new instance answer `none` forever.

Re-sending (`reap`) happens only when the instance that took a command was replaced, not
because the result is slow. Commands whose caller already gave up (TIMEOUT) are dropped
from the queue, so they never run later.

## Movement, chat, and level

Movement cannot go through packets. `SendPacketRaw(false, {type=0, x=.., y=..})` is
accepted without error but does nothing, because the client resends its own position
every ~200 ms. What works: `FindPath` (the game's own fast walk) through `go_to`, or
press-and-hold on the arrow buttons through `swipe`.

    right arrow x=289 y=606, left arrow x=117 y=606
    swipe x y x y <ms>  ->  about 500 px/s, 1 tile = 32 px

Chat and emotes use text packets, and the newline must be a real character
(`string.char(10)`):

```lua
local nl = string.char(10)
pcall(SendPacket, 2, 'action|input' .. nl .. 'text|hello')
pcall(SendPacket, 2, 'action|input' .. nl .. 'text|/dab')
```

Level is not exposed by the API. `GetLocal()` only carries `name, netid, userid, country,
pos, clothing, invisible, isleft, mstate, smstate`, and `GetPlayerInfo()` only `gems`. The
level number only appears in the profile dialog (`action|wrench`).

## Traps that already cost time

1. **The API list is not ticked** in the executor settings. The mod console then sits at
   `active, waiting for commands` and the server sees no connection at all.
2. **`adb reverse` disappears** every time the adb transport drops. The symptom is zero
   `POLL` lines in the server log while `/diag` from the device still arrives. Fix it with
   `adb reverse tcp:8770 tcp:8770` or `bridge_doctor(auto_fix=True)`.
3. **A stale sid holds the turn.** The symptom is `polling: false`, `/diag` repeating with
   `peek=none`, and a log with no `POLL` lines. `ACTIVE_TTL` now handles it.
4. **Hook labels must be numbers.** `AddHook('OnSendPacketRaw', 'string_label', cb)`
   registers nothing, and a failed string-label attempt can kill existing hooks until the
   game restarts.
5. **Lua templates that use `.format()`** need `{{}}` for a literal brace. Templates that
   do not use `.format()` must not contain `{{}}`, because Lua reads that as a table
   holding an empty table.
6. **Hooks do not see packets we send ourselves.** `SendPacket` and `SendPacketRaw` from
   Lua never show up in the capturer. Verify injection through state changes (`GetTile`,
   `GetInventory`, `GetObjectList`), not through the capturer.

## Tests

    .venv/bin/python -m unittest tests_gt.py     # 33 tests, no device needed
    .venv/bin/python test_bridge_lua.py          # bridge.lua harness with a stubbed MakeRequest
    .venv/bin/python test_server.py              # stdio smoke test (needs a device)

`tests_gt.py` covers reap without duplication, dropping stale commands, attached mode,
`type_text` escaping, BFS pathfinding, sid takeover, and the Lua templates
(`collect_objects`, `drop_item`, `list_objects`) compiled with `lupa` before they reach the
game.

## Layout

    server.py           MCP server + HTTP control
    bridge.lua          in-game script: polling, execution, serialisation, capturer
    tests_gt.py         regression tests, no device
    test_bridge_lua.py  bridge.lua harness
    test_server.py      stdio smoke test
    pngio.py            PNG cropper used by screenshot_crop
    experiments/        probe scripts, each file states its result
    docs/               Bothax API reference and client notes

## Contributing

Pull requests are welcome: new tools, bridge fixes, and experiment scripts that document
what the game API does. Read [CONTRIBUTING.md](CONTRIBUTING.md) first; the short version:

- branch from `main`, one topic per PR;
- run the tests, and if you touched a tool, run it on a device and paste the output;
- AI-written code is allowed, but you must have run it and understand every line;
- the PR template asks for the evidence before review starts.

Nothing is pushed straight to `main`.

## License

MIT, see [LICENSE](LICENSE). Use it, fork it, ship it; keep the copyright notice.

## Limits

- **The executor is required.** If the BINTERNAL menu is still locked, `bridge.lua` cannot
  run and the whole Lua path is dead. ADB tools still work.
- **The game must be in the foreground.** Android freezes background processes and polling
  stops with them.
- **ADB must stay connected.** Wireless is flakier than USB, and every drop removes
  `adb reverse`.
- **One device, one active instance.** There is no multi-account isolation.
- **Account risk belongs to the user.** Automation on the official server can end in a
  sanction. This tool ships no detection evasion and is not meant for that.
