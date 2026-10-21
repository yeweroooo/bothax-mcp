#!/usr/bin/env python3
"""
Exercise bridge.lua without the game: stub MakeRequest / RunThread / LogToConsole / Sleep
with Lua 5.4 (lupa), then run one command and check the result.
"""
from lupa import LuaRuntime

L = LuaRuntime(unpack_returned_tuples=True)

HARNESS = r"""
-- state uji
local polls, posted, logs = 0, {}, {}
local done = false

function MakeRequest(url, method, headers, content, timeout)
  if url:find('/poll') then
    polls = polls + 1
    if polls == 1 then
      return { status = 200, content = 'abc123|' .. queue_cmd }
    end
    -- stop the bridge the supported way: _BRIDGE_STOP()
    if done then pcall(_BRIDGE_STOP) end
    return { status = 200, content = 'none' }
  elseif url:find('/result') then
    posted[#posted + 1] = content
    done = true
    return { status = 200, content = 'ok' }
  end
  error('url tak dikenal: ' .. tostring(url))
end

function RunThread(f) f() end

function LogToConsole(s) logs[#logs + 1] = s end

function Sleep(ms) end

-- stub API game
function GetLocal() return { name = 'TestUser', userid = 7, pos = { x = 1.5, y = 2 } } end

function GetWorld() return { name = 'WORLD1', width = 100, height = 60 } end

function GetInventory() return { items = { [1] = { id = 242, count = 3 } } } end

function GetObjectList() return { [1] = { id = 1 }, [2] = { id = 2 } } end

-- fake hooks used to exercise the capturer
_hooks = {}
function AddHook(ev, label, cb) _hooks[label] = { ev = ev, cb = cb } end
function RemoveHook(label) _hooks[label] = nil end
function fire(ev, ...)
  for _, h in pairs(_hooks) do
    if h.ev == ev then h.cb(...) end
  end
end

function get_posted() return posted end
function get_logs() return logs end
"""

L.execute(HARNESS)
L.globals()["queue_cmd"] = "return { me = GetLocal(), w = GetWorld(), inv = GetInventory(), objs = GetObjectList() }"

chunk = L.eval("function(s) return load(s, '=bridge') end")
fn = chunk(open("bridge.lua").read())
try:
    fn()
except Exception as e:  # HARNESS_STOP diharapkan
    if "HARNESS_STOP" not in str(e):
        raise

posted = L.globals().get_posted()
logs = L.globals().get_logs()
print("POST count:", len(posted))
for p in posted.values() if hasattr(posted, "values") else [posted[i] for i in range(1, len(posted) + 1)]:
    print("BODY:", p)
print("LOGS:", list(logs.values()) if hasattr(logs, "values") else logs)

buf = L.globals()._BRIDGE_LOG
entries = buf(10)
print("BUFFER _BRIDGE_LOG:")
for i in range(1, len(entries) + 1):
    print("  ", entries[i])
assert len(entries) >= 2, "log buffer is empty"

# ---- uji traffic capture
g = L.globals()
print("\nTRAFFIC:", g._TRAFFIC_START(100))
L.execute("fire('OnSendPacketRaw', { type = 10, x = 12.5, y = 34.25, value = 1796, netid = 7, extrasize = 0 })")
L.execute("fire('OnSendPacket', 3, 'action|join_request')")
L.execute("fire('OnVariant', { [0] = 'OnConsoleMessage' }, 99, 0)")
L.execute("fire('OnProcessTankUpdate', { type = 0, netid = 7 })")
dump = g._TRAFFIC_DUMP(10)
print("DUMP:")
for i in range(1, len(dump) + 1):
    print("  ", dump[i])
stats = g._TRAFFIC_STATS()
print("STATS: total=", stats.total, "buffer=", stats.buffer, "active=", stats.active)
print("STOP:", g._TRAFFIC_STOP())
assert len(dump) == 4, f"expected 4 events, got {len(dump)}"
txt = g._TRAFFIC_TEXT(10)
print("TEXT separator count:", txt.count("\x1e") + 1)
assert txt.count("\x1e") == 3, "four records need three 0x1e separators"
assert g._TRAFFIC_STATS().active is False
print("  [OK] traffic capture + dump + stop")
