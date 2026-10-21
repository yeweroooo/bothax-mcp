#!/usr/bin/env python3
"""bothax-mcp: MCP server that drives Growtopia through ADB and an in-game Lua bridge.

Two control paths:
  1. ADB: tap, swipe, screenshot, launch, logcat, push scripts.
  2. BRIDGE: Lua runs inside the game process; bridge.lua polls HTTP on 127.0.0.1,
     reached through 'adb reverse tcp:PORT tcp:PORT'.

Run: python server.py (stdio, for MCP clients)."""

from __future__ import annotations

import functools
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer

def _find_adb() -> str:
    """Locate adb: PATH, then ANDROID_SDK_ROOT/ANDROID_HOME, then the per-OS default."""
    found = shutil.which("adb")
    if found:
        return found
    roots = [
        os.environ.get("ANDROID_SDK_ROOT", ""),
        os.environ.get("ANDROID_HOME", ""),
    ]
    for root in filter(None, roots):
        cand = Path(root) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
        if cand.exists():
            return str(cand)
    home = Path.home()
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        guesses = [local / "Android/Sdk/platform-tools/adb.exe"]
    elif sys.platform == "darwin":
        guesses = [home / "Library/Android/sdk/platform-tools/adb"]
    else:
        guesses = [
            home / "Android/Sdk/platform-tools/adb",
            Path("/usr/lib/android-sdk/platform-tools/adb"),
            Path("/opt/android-sdk/platform-tools/adb"),
        ]
    for cand in guesses:
        if cand.exists():
            return str(cand)
    return "adb"  # let the missing binary surface when adb is actually used


TMP_DIR = Path(tempfile.gettempdir())
# GT_LOG_PATH overrides this; the default follows TMPDIR.
# (some setups do not use /tmp, so never assume it).
LOG_PATH = Path(os.environ.get("GT_LOG_PATH") or (TMP_DIR / "bridge_http.log"))

ADB = _find_adb()
PACKAGE = "com.rtsoft.growtopia"
ACTIVITY = "com.rtsoft.growtopia/.Main"
SCRIPT_DIR = f"/sdcard/Android/media/{PACKAGE}/scripts"
BRIDGE_PORT = int(os.environ.get("GT_BRIDGE_PORT", "8770"))
POLL_WAIT = 1.0          # detik long-poll
ACTIVE_TTL = 20.0        # holder sid is considered dead after this much silence
RESULT_TIMEOUT = 12.0     # default wait for one eval result

mcp = MCPServer("bothax-mcp")


def _safe(fn):
    """Return any exception as an 'ERROR: ...' string, so one bad call cannot kill the session."""

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {type(e).__name__}: {e}"

    return wrapper


def adb(*args: str, timeout: int = 20, check: bool = False) -> subprocess.CompletedProcess:
    """Run adb with a short timeout; a dead wireless transport can hang for minutes."""
    cmd = [ADB, *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"adb {' '.join(args[:2])} timeout {timeout}s "
            f"(device offline? check `adb devices`, or `adb kill-server`)"
        ) from None
    if check and p.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {p.stderr.strip() or p.stdout.strip()}")
    return p


def adb_shell(cmd: str, timeout: int = 60) -> str:
    return adb("shell", cmd, timeout=timeout).stdout.strip()


def device_serial() -> str:
    out = adb("devices").stdout.splitlines()[1:]
    for line in out:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    raise RuntimeError("no ADB device connected")


def game_pid() -> int | None:
    out = adb_shell(f"pidof {PACKAGE}")
    return int(out.split()[0]) if out.strip() else None


def _tmp_png(prefix: str) -> str:
    """Temp PNG path that honours TMPDIR instead of assuming /tmp."""
    return str(TMP_DIR / f"{prefix}_{int(time.time() * 1000)}.png")


def _screencap(dest: str) -> str:
    """Capture the screen as PNG bytes."""
    try:
        p = subprocess.run(
            [ADB, "exec-out", "screencap", "-p"], capture_output=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("screencap timeout 60s (device offline?)") from None
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(f"screencap failed: {p.stderr.decode(errors='replace')[:200].strip()}")
    Path(dest).write_bytes(p.stdout)
    return dest


# ------------------------------------------------------- helpers: input teks

_LUA_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}


def _unescape_lua(s: str) -> str:
    """Undo enc() escaping from bridge.lua before parsing a result."""
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            out.append(_LUA_ESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _input_text_payload(text: str) -> str:
    """Percent-encode spaces for 'input text'."""
    if any(ord(c) > 127 for c in text):
        raise ValueError(
            "text contains non-ASCII characters; `input text` only accepts ASCII "
            "(use ADBKeyboard, or send text through the bridge)"
        )
    if "\n" in text or "\r" in text:
        raise ValueError("newlines are not supported; send KEYCODE_ENTER separately")
    return text.replace(" ", "%s")


def _sh_single_quote(s: str) -> str:
    """Quote for the device shell without losing quotes or metacharacters."""
    return "'" + s.replace("'", "'\\''") + "'"


def _input_text_command(text: str) -> str:
    return f"input text {_sh_single_quote(_input_text_payload(text))}"


class _Bridge:
    """Command queue and result store shared by the tools and the HTTP endpoints."""

    def __init__(self) -> None:
        self.cmds: queue.Queue[tuple[str, str]] = queue.Queue()
        self.pending: dict[str, dict] = {}
        self.inflight: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.last_poll = 0.0
        self.last_result = 0.0
        self.sid: str | None = None
        self.active: str | None = None
        self.last_diag: dict | None = None
        # A command its caller gave up on must not run later, when a new bridge appears.
        self.cancelled: set[str] = set()

    def submit(self, code: str, timeout: float) -> str:
        if BRIDGE_MODE == "attached":
            return _submit_remote(code, timeout)
        cmd_id = uuid.uuid4().hex[:12]
        ev = threading.Event()
        box: dict = {"event": ev, "status": None, "text": None}
        with self.lock:
            self.pending[cmd_id] = box
        self.cmds.put((cmd_id, code))
        ev.wait(timeout)
        with self.lock:
            self.pending.pop(cmd_id, None)
            if not ev.is_set():
                self.cancelled.add(cmd_id)
        if not ev.is_set():
            return f"TIMEOUT: no result within {timeout:.0f}s (is the bridge polling?)"
        if box["status"] == "ok":
            return box["text"] or "(empty)"
        return f"ERROR: {box['text']}"

    def deliver(self, cmd_id: str, status: str, text: str) -> None:
        with self.lock:
            self.cancelled.discard(cmd_id)
            box = self.pending.get(cmd_id)
            self.inflight.pop(cmd_id, None)
            self.last_result = time.time()
            if box:
                box["status"] = status
                box["text"] = text
                box["event"].set()

    def deliver_latest(self, status: str, text: str) -> None:
        """Deliver to the newest pending command, for clients that send no id."""
        with self.lock:
            if not self.pending:
                self.last_result = time.time()
                return
            cid = next(reversed(self.pending))
        self.deliver(cid, status, text)

    def claim(self, sid: str) -> bool:
        """True when this instance may receive commands.

        The active instance keeps its turn while it keeps polling, but the turn expires after
        ACTIVE_TTL. Without that expiry a stale sid answers 'none' to every new instance, so
        polling looks healthy while no command ever arrives."""
        now = time.time()
        if not sid:
            return True
        if not self.active:
            self.active, self.sid = sid, sid
            _trace(f"active instance: {sid}")
            return True
        if sid == self.active:
            return True
        if now - self.last_poll < ACTIVE_TTL:
            return False
        self.active, self.sid = sid, sid
        _trace(f"active instance taken over after {now - self.last_poll:.0f}s of silence: {sid}")
        return True

    def next_cmd(self) -> tuple[str, str] | None:
        while True:
            try:
                cmd = self.cmds.get_nowait()
            except queue.Empty:
                return None
            with self.lock:
                if cmd[0] in self.cancelled:
                    # Caller already timed out: drop it instead of running it.
                    self.cancelled.discard(cmd[0])
                    continue
                self.last_poll = time.time()
                self.inflight[cmd[0]] = {
                    "code": cmd[1],
                    "ts": time.time(),
                    "tries": 1,
                    # Instance that took this command; reap() compares it later.
                    "sid": self.active,
                }
            return cmd

    def reap(self, retry_after: float = 6.0, max_tries: int = 3) -> None:
        """Re-send commands that are clearly lost, never ones still running.

        A command is re-queued only when the instance that took it was replaced, which means it
        will never be answered. The old rule (re-send after retry_after) executed every slow
        command twice, for example Sleep(8000)."""
        now = time.time()
        requeue: list[tuple[str, str]] = []
        with self.lock:
            for cid, info in list(self.inflight.items()):
                if cid not in self.pending:
                    self.inflight.pop(cid, None)
                    continue
                if now - info["ts"] < retry_after:
                    continue
                taken_over = info.get("sid") is not None and self.active != info.get("sid")
                if not taken_over:
                    continue
                if info["tries"] >= max_tries:
                    self.inflight.pop(cid, None)
                    continue
                info["tries"] += 1
                info["ts"] = now
                info["sid"] = self.active
                requeue.append((cid, info["code"]))
        for cid, code in requeue:
            _trace(f"REQUEUE {cid} (percobaan {self.inflight.get(cid, {}).get('tries')})")
            self.cmds.put((cid, code))

    def status(self) -> dict:
        if BRIDGE_MODE == "attached":
            # A local queue would be empty and misleading: report the port owner instead.
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{BRIDGE_PORT}/status", timeout=3
                ) as r:
                    remote = json.loads(r.read().decode())
                remote["mode"] = "attached"
                remote["owner_port"] = BRIDGE_PORT
                return remote
            except Exception as e:  # noqa: BLE001
                return {
                    "mode": "attached",
                    "port": BRIDGE_PORT,
                    "owner_port": BRIDGE_PORT,
                    "error": f"port owner did not answer: {e}",
                }
        now = time.time()
        with self.lock:
            waiting = len(self.pending)
        return {
            "polling": (now - self.last_poll) < 90 if self.last_poll else False,
            "last_poll_ago_s": round(now - self.last_poll, 1) if self.last_poll else None,
            "last_result_ago_s": round(now - self.last_result, 1) if self.last_result else None,
            "queued": self.cmds.qsize(),
            "waiting": waiting,
            "port": BRIDGE_PORT,
            "mode": BRIDGE_MODE,
            "log_path": str(LOG_PATH),
        }


BRIDGE = _Bridge()

# "owner"    : this process holds the bridge port (normal case)
# "attached" : another bothax-mcp instance already holds it, for example a
#              leftover `server.py --http-only`, so commands go there through
#              /enqueue. Without this the MCP client would die on a busy port
#              and take every ADB tool down with it.
BRIDGE_MODE = "owner"


def _submit_remote(code: str, timeout: float) -> str:
    """Forward a command to the instance that owns the bridge port."""
    payload = json.dumps({"code": code, "timeout": timeout}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{BRIDGE_PORT}/enqueue",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout + 8) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return f"ERROR: bridge instance owning the port did not answer: {e}"


def _bridge_alive(timeout: float = 1.5) -> bool:
    """True when the port answers /health, meaning another bothax-mcp owns it."""
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{BRIDGE_PORT}/health", timeout=timeout
        ) as r:
            return r.read().strip() == b"ok"
    except Exception:  # noqa: BLE001
        return False


def _trace(msg: str) -> None:
    """Append a line to the bridge log. Best effort, never raises."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:  # noqa: BLE001
        pass


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # senyap
        pass

    def _send(self, body: str, code: int = 200) -> None:
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802 (name required by BaseHTTPRequestHandler)
        if self.path.startswith("/health"):
            return self._send("ok")
        if self.path.startswith("/status"):
            return self._send(json.dumps(BRIDGE.status(), indent=2))
        if self.path.startswith("/hello"):
            p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            new_sid = (p.get("sid") or [""])[0]
            if new_sid:
                BRIDGE.sid = new_sid
                BRIDGE.active = new_sid
                BRIDGE.last_poll = time.time()
                _trace(f"HELLO active instance: {new_sid}")
            return self._send("ok")
        if self.path.startswith("/poll"):
            sid = (urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("sid") or [""])[0]
            if not BRIDGE.claim(sid):
                # Old instance still holds the turn: answer none and leave last_poll alone.
                return self._send("none")
            deadline = time.time() + POLL_WAIT
            while time.time() < deadline:
                cmd = BRIDGE.next_cmd()
                if cmd:
                    _trace(f"POLL -> send {cmd[0]} ({len(cmd[1])} B) sid={sid or '-'}")
                    return self._send(f"{cmd[0]}|{cmd[1]}")
                time.sleep(0.15)
            BRIDGE.last_poll = time.time()
            _trace("POLL -> none")
            return self._send("none")
        if self.path.startswith("/diag"):
            p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            msg = (p.get("msg") or ["?"])[0]
            BRIDGE.last_diag = {"msg": msg, "ts": time.time()}
            _trace(f"DIAG klien: {msg}")
            return self._send("ok")
        if self.path.startswith("/ack"):
            p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            _trace(f"ACK sid={(p.get('sid') or ['?'])[0]} id={(p.get('id') or ['?'])[0]} len={(p.get('len') or ['?'])[0]}")
            return self._send("ok")
        if self.path.startswith("/result"):
            # Fallback: the game can post results as a GET query when POST fails.
            q = urllib.parse.urlparse(self.path).query
            p = urllib.parse.parse_qs(q)
            cid = (p.get("id") or [""])[0]
            st = (p.get("st") or ["ok"])[0]
            data = (p.get("d") or [""])[0]
            if cid:
                _trace(f"RESULT-GET {cid} {st} ({len(data)} B)")
                BRIDGE.deliver(cid, st, data)
                return self._send("ok", 200)
            _trace("RESULT-GET without id")
            return self._send("bad query", 400)
        if self.path.startswith("/call"):
            # Manual control without an MCP client: /call?tool=...&args=<json>
            from urllib.parse import parse_qs, urlparse

            q = parse_qs(urlparse(self.path).query)
            name = (q.get("tool") or [""])[0]
            fn = CONTROL_TOOLS.get(name)
            if not fn:
                return self._send("unknown tool: " + name, 404)
            try:
                kwargs = json.loads((q.get("args") or ["{}"])[0])
                return self._send(str(fn(**kwargs)))
            except Exception as e:  # noqa: BLE001
                return self._send(f"error: {e}", 500)
        return self._send("not found", 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        _trace(f"POST {self.path} ({n} B) ct={self.headers.get('Content-Type')}")
        if self.path.startswith("/enqueue"):
            raw = self.rfile.read(n).decode("utf-8", "replace")
            try:
                body = json.loads(raw)
            except Exception:  # noqa: BLE001
                return self._send("bad json", 400)
            code = str(body.get("code") or "")
            timeout = float(body.get("timeout") or RESULT_TIMEOUT)
            return self._send(BRIDGE.submit(code, timeout))
        if self.path.startswith("/result"):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n).decode("utf-8", "replace")
            parts = raw.split("|", 2)
            if len(parts) == 3:
                _trace(f"RESULT {parts[0]} {parts[1]} ({len(parts[2])} B)")
                BRIDGE.deliver(parts[0], parts[1], parts[2])
                return self._send("ok")
            if len(parts) == 2:
                # Legacy client without an id: hand it to whatever is still pending.
                _trace(f"RESULT-NO-ID {parts[0]} ({len(parts[1])} B)")
                BRIDGE.deliver_latest(parts[0], parts[1])
                return self._send("ok")
            _trace(f"RESULT-RUSAK: {raw[:60]!r}")
            return self._send("bad payload", 400)
        return self._send("not found", 404)


def start_bridge_server() -> int:
    global BRIDGE_MODE
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", BRIDGE_PORT), _Handler)
    except OSError as e:
        # Port taken. If the owner is another bothax-mcp, stay alive in attached mode.
        if _bridge_alive():
            BRIDGE_MODE = "attached"
            print(
                f"[bothax-mcp] port {BRIDGE_PORT} is held by another bothax-mcp instance; "
                f"attached mode (Lua commands are forwarded there)",
                file=sys.stderr,
                flush=True,
            )
            return BRIDGE_PORT
        raise RuntimeError(
            f"port {BRIDGE_PORT} is used by a process that is not bothax-mcp: {e}. "
            f"Check `ss -ltnp | grep {BRIDGE_PORT}`, or set GT_BRIDGE_PORT."
        ) from e
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    def _reaper() -> None:
        while True:
            time.sleep(1.0)
            try:
                BRIDGE.reap()
            except Exception:  # noqa: BLE001
                pass

    threading.Thread(target=_reaper, daemon=True).start()
    return BRIDGE_PORT


@mcp.tool()
@_safe
def device_info() -> str:
    """Device model, Android version, game process, and bridge state."""
    info = {}
    try:
        info["serial"] = device_serial()
        # One round-trip for four properties; each adb call costs 1-2 s on wireless.
        props = adb_shell(
            "getprop ro.build.version.release; getprop ro.build.version.sdk; "
            "getprop ro.product.cpu.abi; getprop ro.product.model"
        ).splitlines()
        for key, val in zip(("android", "sdk", "abi", "model"), props):
            info[key] = val.strip()
        # pid and window focus in the same call.
        probe = adb_shell(
            f"pidof {PACKAGE}; "
            f"dumpsys window | grep -m1 mCurrentFocus "
            f"|| dumpsys activity activities | grep -m1 mResumedActivity"
        ).splitlines()
        pid = None
        if probe:
            first = probe[0].split()
            if first and first[0].isdigit():
                pid = int(first[0])
        info["game_running"] = bool(pid)
        info["game_pid"] = pid
        focus = next(
            (l.strip() for l in probe if "mCurrentFocus" in l or "mResumedActivity" in l),
            "",
        )
        if focus:
            info["focus"] = focus
        info["bridge"] = BRIDGE.status()
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"
    return json.dumps(info, indent=2)


@mcp.tool()
@_safe
def screenshot(save_to: str = ""):
    """Return the screen as an image."""
    return Image(path=_screencap(save_to or _tmp_png("gt_shot")))


@mcp.tool()
@_safe
def screenshot_crop(x0: int, y0: int, x1: int, y1: int, save_to: str = ""):
    """Screenshot cropped to a region.

    Use it to read small widgets clearly before choosing tap coordinates."""
    src = _screencap(_tmp_png("gt_full"))
    dst = save_to or _tmp_png("gt_crop")

    import pngio
    try:
        pngio.crop(src, dst, x0, y0, x1, y1)
    except Exception as e:  # noqa: BLE001
        return f"ERROR: crop failed: {e}"
    return Image(path=dst)


@mcp.tool()
@_safe
def panel_crop(x0: int = 0, y0: int = 0, x1: int = 1100, y1: int = 950):
    """Crop the mod panel area (top-left by default)."""
    return screenshot_crop(x0, y0, x1, y1)


@mcp.tool()
@_safe
def tap(x: int, y: int) -> str:
    """Tap a screen coordinate."""
    adb("shell", f"input tap {x} {y}")
    return f"tap {x},{y}"


@mcp.tool()
@_safe
def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Swipe from (x1,y1) to (x2,y2)."""
    adb("shell", f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
    return f"swipe {x1},{y1} -> {x2},{y2} ({duration_ms}ms)"


@mcp.tool()
@_safe
def key(code: str) -> str:
    """Send a keyevent, for example KEYCODE_BACK or KEYCODE_ENTER."""
    adb("shell", f"input keyevent {code}")
    return f"key {code}"


@mcp.tool()
@_safe
def type_text(text: str) -> str:
    """Type ASCII text on the device.

    Spaces are sent as %s and the payload is quoted for the device shell, so quotes and
    metacharacters survive. Non-ASCII is rejected with a clear message."""
    try:
        cmd = _input_text_command(text)
    except ValueError as e:
        return f"ERROR: {e}"
    p = adb("shell", cmd)
    if p.returncode != 0:
        return f"ERROR: input text failed: {(p.stderr or p.stdout).strip()[:200]}"
    return f"typed {len(text)} chars"


@mcp.tool()
@_safe
def launch_game() -> str:
    """Start Growtopia and wait until its activity has focus."""
    p = adb("shell", f"am start -W -n {ACTIVITY}", timeout=60)
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0 or "Error" in out:
        return f"ERROR: am start failed: {out[:200]}"
    time.sleep(2)
    pid = game_pid()
    return f"launched, pid={pid}" if pid else "launched but the process is not visible yet"


@mcp.tool()
@_safe
def stop_game() -> str:
    """Force-stop Growtopia and confirm the process is gone."""
    p = adb("shell", f"am force-stop {PACKAGE}")
    if p.returncode != 0:
        return f"ERROR: force-stop failed: {(p.stderr or p.stdout).strip()[:200]}"
    time.sleep(0.5)
    pid = game_pid()
    return "stopped" if pid is None else f"still running, pid={pid}"


@mcp.tool()
@_safe
def logcat(lines: int = 60, grep: str = "") -> str:
    """Recent logcat lines, optionally filtered."""
    fetch = max(lines * 10, 400) if grep else lines
    out = adb("logcat", "-d", "-t", str(fetch)).stdout
    if grep:
        kept = [l for l in out.splitlines() if grep.lower() in l.lower()]
        out = "\n".join(kept[-lines:])
    return out.strip() or "(empty)"


@mcp.tool()
@_safe
def install_apk(apk_path: str) -> str:
    """Install or replace an APK, reporting the failure rather than adb output."""
    if not Path(apk_path).expanduser().exists():
        return f"ERROR: file not found: {apk_path}"
    p = adb("install", "-r", str(Path(apk_path).expanduser()), timeout=600)
    text = (p.stdout + p.stderr).strip()
    if p.returncode != 0 or "Failure" in text:
        return f"ERROR: install failed: {text[:300]}"
    return text


@mcp.tool()
@_safe
def push_script(local_path: str, name: str = "") -> str:
    """Copy a .lua file into the game's scripts folder."""
    src = Path(local_path).expanduser()
    if not src.exists():
        return f"ERROR: file not found: {local_path}"
    name = name or src.name
    adb_shell(f"mkdir -p {SCRIPT_DIR}")
    p = adb("push", str(src), f"{SCRIPT_DIR}/{name}")
    text = (p.stdout or p.stderr).strip()
    if p.returncode != 0:
        return f"ERROR: push failed: {text[:200]}"
    return text or f"pushed {name}"


@mcp.tool()
@_safe
def list_scripts() -> str:
    """List the scripts available on the device."""
    out = adb_shell(f"ls -l {SCRIPT_DIR}")
    return out or "(empty folder)"


@mcp.tool()
@_safe
def install_bridge() -> str:
    """Push bridge.lua and set up adb reverse for the control channel."""
    local = Path(__file__).with_name("bridge.lua")
    if not local.exists():
        return f"ERROR: {local} does not exist"
    adb_shell(f"mkdir -p {SCRIPT_DIR}")
    push = adb("push", str(local), f"{SCRIPT_DIR}/bridge.lua")
    if push.returncode != 0:
        return f"ERROR: pushing bridge.lua failed: {(push.stderr or push.stdout).strip()[:200]}"
    rev = adb("reverse", f"tcp:{BRIDGE_PORT}", f"tcp:{BRIDGE_PORT}")
    # Do not trust the return code: adb reverse can silently fail to install.
    listing = adb("reverse", "--list").stdout
    installed = f"tcp:{BRIDGE_PORT}" in listing
    if not installed:
        return (
            f"ERROR: adb reverse did not install (rc={rev.returncode}): "
            f"{(rev.stderr or rev.stdout).strip()[:200]}"
        )
    return (
        f"bridge.lua -> {SCRIPT_DIR}/bridge.lua\n"
        f"adb reverse tcp:{BRIDGE_PORT} -> installed\n"
        f"run bridge.lua once from the game executor menu"
    )


@mcp.tool()
@_safe
def bridge_status() -> str:
    """Whether bridge.lua is polling from inside the game."""
    return json.dumps(BRIDGE.status(), indent=2)


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@mcp.tool()
@_safe
def adb_reconnect(address: str = "") -> str:
    """Recover a dropped adb transport, typical for wireless adb and emulators."""
    notes: list[str] = []
    if address:
        notes.append(adb("connect", address, timeout=25).stdout.strip() or f"connect {address}")
    try:
        off = [
            l.split()[0]
            for l in adb("devices", timeout=10).stdout.splitlines()[1:]
            if l.strip() and l.split()[1:2] == ["offline"]
        ]
    except Exception as e:  # noqa: BLE001
        off = []
        notes.append(f"devices failed: {e}")
    if off:
        notes.append(adb("reconnect", timeout=25).stdout.strip() or "reconnect offline")
    devs = adb("devices", timeout=10).stdout.splitlines()[1:]
    summary = "; ".join(l.strip() for l in devs if l.strip()) or "(no device)"
    return "\n".join([*notes, f"device now: {summary}"])


@mcp.tool()
@_safe
def bridge_doctor(auto_fix: bool = True) -> str:
    """Check the whole control chain and fix what is safe to fix.

    Verifies device visibility, adb reverse mapping, bridge polling, and API availability,
    then reports what it changed."""
    steps: list[dict] = []
    fixes: list[str] = []

    def add(name: str, ok: bool, detail) -> None:
        steps.append({"check": name, "ok": bool(ok), "detail": detail})

    add("adb binary", bool(shutil.which(ADB) or Path(ADB).exists()), ADB)

    devs: list[str] = []
    try:
        devs = [l.strip() for l in adb("devices", timeout=10).stdout.splitlines()[1:] if l.strip()]
    except Exception as e:  # noqa: BLE001
        add("adb devices", False, str(e))
    online = [l.split()[0] for l in devs if l.split()[1:2] == ["device"]]
    offline = [l.split()[0] for l in devs if l.split()[1:2] in (["offline"], ["unauthorized"])]
    add("device online", bool(online), online or (offline and [f"{s} (offline/unauthorized)" for s in offline]) or "none")

    pid = None
    if online:
        try:
            pid = game_pid()
            add("game running", pid is not None, f"pid={pid}" if pid else "Growtopia is not running")
        except Exception as e:  # noqa: BLE001
            add("game running", False, str(e))
        try:
            listing = adb("reverse", "--list", timeout=10).stdout
            mapped = f"tcp:{BRIDGE_PORT}" in listing
            if not mapped and auto_fix:
                adb("reverse", f"tcp:{BRIDGE_PORT}", f"tcp:{BRIDGE_PORT}", timeout=10)
                listing = adb("reverse", "--list", timeout=10).stdout
                mapped = f"tcp:{BRIDGE_PORT}" in listing
                if mapped:
                    fixes.append(f"adb reverse tcp:{BRIDGE_PORT} dipasang ulang")
            add("adb reverse", mapped, listing.strip() or "(no mapping yet)")
        except Exception as e:  # noqa: BLE001
            add("adb reverse", False, str(e))

    port_ok = _port_open("127.0.0.1", BRIDGE_PORT)
    add("bridge port on host", port_ok, f"127.0.0.1:{BRIDGE_PORT}")

    st = BRIDGE.status()
    polling = bool(st.get("polling"))
    add("bridge polling", polling, st)
    diag = st.get("last_diag")
    if diag:
        add("last diag", True, diag)

    if not port_ok:
        verdict = (
            "no bridge server on this port; run `python server.py` "
            "(or `--http-only` for the bridge alone), or enable the MCP server"
        )
    elif not online:
        verdict = (
            "device is not online: connect USB or call `adb_reconnect('ip:5555')`; "
            "if it stays `unauthorized`, accept the debugging prompt on the device"
        )
    elif pid is None:
        verdict = "device ready but Growtopia is not running -> launch_game()"
    elif not polling:
        verdict = (
            "port and reverse are ready, but bridge.lua is not polling. Run "
            "bridge.lua from the executor AND make sure the API list is enabled "
            "in the executor settings, otherwise MakeRequest fails before it "
            "leaves the game. Check the 'PROBE /health' line in the mod console."
        )
    else:
        verdict = "chain complete: ADB -> adb reverse -> bridge.lua polling"

    return json.dumps(
        {"steps": steps, "fixes": fixes, "conclusion": verdict}, indent=2
    )


_FIND_PATH_LUA = """
local needle = tostring({target}):lower()
local margin = {margin}
local p = GetLocal().pos
local px, py = math.floor(p.x / 32), math.floor(p.y / 32)
local cache, best, bestd = {{}}, nil, 1e9
for _, t in pairs(GetTiles()) do
  local fg = tonumber(t.fg) or 0
  if fg > 0 then
    local n = cache[fg]
    if n == nil then
      local ok, i = pcall(GetItemInfo, fg)
      n = (ok and i and tostring(i.name):lower()) or ''
      cache[fg] = n
    end
    if n:find(needle, 1, true) then
      local d = math.abs(t.x - px) + math.abs(t.y - py)
      if d < bestd then bestd, best = d, t end
    end
  end
end
if not best then return 'NOTFOUND' end
local w, h = GetWorld().width, GetWorld().height
local x0 = math.max(0, math.min(px, best.x) - margin)
local x1 = math.min(w - 1, math.max(px, best.x) + margin)
local y0 = math.max(0, math.min(py, best.y) - margin)
local y1 = math.min(h - 1, math.max(py, best.y) + margin)
local rows = {{}}
for y = y0, y1 do
  local r = {{}}
  for x = x0, x1 do
    local t = GetTile(x, y)
    local solid = t and t.collidable
    local fg = t and tonumber(t.fg) or 0
    local ch = '.'
    if x == best.x and y == best.y then ch = 'D'
    elseif solid then ch = '#'
    elseif fg > 0 then ch = 'o' end
    r[#r + 1] = ch
  end
  rows[#rows + 1] = string.format('%02d%s', y, table.concat(r))
end
return table.concat({{
  string.format('target=%d,%d', best.x, best.y),
  string.format('fg=%s', tostring(best.fg)),
  string.format('name=%s', tostring(cache[tonumber(best.fg)] or '')),
  string.format('player=%d,%d', px, py),
  string.format('bbox=%d,%d,%d,%d', x0, y0, x1, y1),
}}, '\\n') .. '\\ngrid\\n' .. table.concat(rows, '\\n')
"""


def _lua_literal(s: str) -> str:
    out = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"' + out + '"'


def _bfs_path(
    solids: set[tuple[int, int]],
    start: tuple[int, int],
    goal: tuple[int, int],
    bounds: tuple[int, int, int, int],
) -> list[tuple[int, int, str]] | None:
    """BFS over the tile grid with the moves the avatar can actually make:
    walk, drop down, fall, and jump one tile up."""
    x0, y0, x1, y1 = bounds

    def inb(p: tuple[int, int]) -> bool:
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1

    def free(p: tuple[int, int]) -> bool:
        return inb(p) and p not in solids

    def supported(p: tuple[int, int]) -> bool:
        below = (p[0], p[1] + 1)
        return (not free(below))

    import heapq

    start_state = (start[0], start[1])
    dist: dict[tuple[int, int], int] = {start_state: 0}
    prev: dict[tuple[int, int], tuple[tuple[int, int], str] | None] = {start_state: None}
    pq: list[tuple[int, tuple[int, int]]] = [(0, start_state)]

    def push(cur, nxt, cost, how):
        nd = dist[cur] + cost
        if nd < dist.get(nxt, 1 << 30):
            dist[nxt] = nd
            prev[nxt] = (cur, how)
            heapq.heappush(pq, (nd, nxt))

    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 1 << 30):
            continue
        if cur == goal:
            break
        x, y = cur
        # flat walk or step down
        for dx in (-1, 1):
            side = (x + dx, y)
            if free(side):
                if supported(side):
                    push(cur, side, 1, "walk")
                else:
                    # stepping into air: fall until something holds
                    ny = y
                    while ny + 1 <= y1 and free((x + dx, ny + 1)):
                        ny += 1
                    push(cur, (x + dx, ny), 1 + (ny - y), "fall")
            diag = (x + dx, y + 1)
            if free(diag) and supported(diag):
                push(cur, diag, 1, "step_down")
        # jump one tile up; two tiles of headroom must be free
        for dx in (-1, 0, 1):
            up = (x + dx, y - 1)
            if free(up) and free((x + dx, y - 2)):
                push(cur, up, 2, "jump")
        # straight fall
        down = (x, y + 1)
        if free(down):
            ny = y
            while ny + 1 <= y1 and free((x, ny + 1)):
                ny += 1
            push(cur, (x, ny), 1 + (ny - y), "fall")

    target = goal
    if target not in dist:
        # may stop beside the door when the door tile is solid
        cands = [
            (goal[0] + dx, goal[1] + dy)
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
        ]
        cands = [c for c in cands if c in dist]
        if not cands:
            return None
        target = min(cands, key=lambda c: dist[c])

    steps: list[tuple[int, int, str]] = []
    node = target
    while node is not None:
        entry = prev.get(node)
        how = entry[1] if entry else "start"
        steps.append((node[0], node[1], how))
        node = entry[0] if entry else None
    steps.reverse()
    return steps


_MOVE_LUA = """
local tx, ty = {tx}, {ty}
local p0 = GetLocal().pos
local chk = false
local okc, c = pcall(CheckPath, tx, ty)
if okc then chk = (c == true) end
if not chk then
  return string.format('BLOCKED from=%d,%d tile=%d,%d',
    math.floor(p0.x / 32), math.floor(p0.y / 32), tx, ty)
end
local okf, errf = pcall(FindPath, tx, ty)
-- FindPath can take more than one tick: poll the position (max ~1.5 s)
-- before calling it a failure.
local p1 = p0
local tries = 0
while tries < 8 do
  Sleep(200)
  tries = tries + 1
  p1 = GetLocal().pos
  if math.floor(p1.x / 32) ~= math.floor(p0.x / 32)
     or math.floor(p1.y / 32) ~= math.floor(p0.y / 32) then
    break
  end
end
return string.format('chk=true ok=%s err=%s from=%d,%d to=%d,%d pos=%.0f,%.0f tries=%d',
  tostring(okf), tostring(errf),
  math.floor(p0.x / 32), math.floor(p0.y / 32),
  math.floor(p1.x / 32), math.floor(p1.y / 32), p1.x, p1.y, tries)
"""


def _kv_parse(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split():
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def _move_to_tile(tx: int, ty: int) -> dict[str, str]:
    """Move with FindPath, then poll the position until the avatar really arrives."""
    raw = BRIDGE.submit(_MOVE_LUA.format(tx=int(tx), ty=int(ty)).strip(), 20)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return {"error": raw}
    raw = _unescape_lua(raw).strip()
    data = _kv_parse(raw)
    if raw.startswith("BLOCKED"):
        data["blocked"] = "1"
    return data


@mcp.tool()
@_safe
def go_to(tilex: int, tiley: int) -> str:
    """Move the avatar to a tile using the game's own FindPath.

    CheckPath gates the call, FindPath executes it, and the position is read back to prove
    the move happened. Movement is the client's fast-walk, not step-by-step animation."""
    r = _move_to_tile(tilex, tiley)
    if "error" in r:
        return r["error"]
    if r.get("blocked"):
        return json.dumps(
            {
                "moved": False,
                "reason": f"CheckPath({tilex},{tiley}) = false (solid tile)",
                "from": r.get("from"),
            },
            indent=2,
        )
    return json.dumps(
        {
            "moved": r.get("from") != r.get("to"),
            "from": r.get("from"),
            "to": r.get("to"),
            "target": [int(tilex), int(tiley)],
            "world_pos": r.get("pos"),
            "findpath_ok": r.get("ok") == "true",
            "wait_ticks": r.get("tries"),
        },
        indent=2,
    )


_COLLECT_LUA = r"""
local item = {item}
local radius = {radius}
local delay = {delay}
local p = GetLocal().pos
local before = {{}}
for _, it in pairs(GetInventory()) do before[it.id] = (before[it.id] or 0) + (it.amount or 0) end
local total, sent, daftar = 0, 0, {{}}
for _, o in pairs(GetObjectList()) do
  total = total + 1
  local ok = (item == 0) or (o.id == item)
  if ok and radius > 0 then
    local dx, dy = (o.pos.x - p.x) / 32.0, (o.pos.y - p.y) / 32.0
    if math.sqrt(dx * dx + dy * dy) > radius then ok = false end
  end
  if ok then
    SendPacketRaw(false, {{
      type = 11, state = 0, value = o.oid,
      px = o.pos.x, py = o.pos.y, x = p.x, y = p.y
    }})
    sent = sent + 1
    if #daftar < 40 then
      daftar[#daftar + 1] = string.format('%s@%d,%d', tostring(o.id),
        math.floor(o.pos.x / 32), math.floor(o.pos.y / 32))
    end
    Sleep(delay)
  end
end
Sleep(700)
local sisa = 0
for _ in pairs(GetObjectList()) do sisa = sisa + 1 end
local after = {{}}
for _, it in pairs(GetInventory()) do after[it.id] = (after[it.id] or 0) + (it.amount or 0) end
local delta = {{}}
for id, v in pairs(after) do
  local d = v - (before[id] or 0)
  if d ~= 0 then delta[#delta + 1] = string.format('%d:%+d', id, d) end
end
table.sort(delta)
return string.format('objects_before=%d sent=%d objects_left=%d delta_inv=%s list=%s',
  total, sent, sisa, table.concat(delta, ','), table.concat(daftar, ' '))
"""

_LIST_OBJECTS_LUA = r"""
local daftar = {}
for _, o in pairs(GetObjectList()) do
  local nm = '?'
  local ok, info = pcall(GetItemInfo, o.id)
  if ok and info and info.name then nm = tostring(info.name) end
  daftar[#daftar + 1] = string.format('oid=%s id=%s name=%s tile=%d,%d',
    tostring(o.oid), tostring(o.id), nm,
    math.floor(o.pos.x / 32), math.floor(o.pos.y / 32))
end
table.sort(daftar)
return string.format('count=%d|%s', #daftar, table.concat(daftar, '|'))
"""


_DROP_LUA = r"""
local id = {item}
local amount = {amount}
local ada = 0
for _, it in pairs(GetInventory()) do if it.id == id then ada = ada + it.amount end end
if ada <= 0 then return 'id={item} inv_before=0 inv_after=0 count=0 objects=0 total_amount=0 reason=missing' end
if amount <= 0 or amount > ada then amount = ada end
SendPacket(2, 'action|dialog_return\ndialog_name|drop\nitem_drop|' .. id .. '|\nitem_count|' .. amount .. '\n')
Sleep(1200)
local objs, total = 0, 0
for _, o in pairs(GetObjectList()) do
  objs = objs + 1
  if o.id == id then total = total + (o.amount or 0) end
end
local sisa = 0
for _, it in pairs(GetInventory()) do if it.id == id then sisa = sisa + it.amount end end
return string.format('id=%d count=%d inv_before=%d inv_after=%d objects=%d total_amount=%d reason=ok',
  id, amount, ada, sisa, objs, total)
"""


@mcp.tool()
@_safe
def drop_item(item_id: int, amount: int = 0) -> str:
    """Drop an item on the avatar's tile with one packet.

    Format: action|dialog_return, dialog_name|drop, item_drop|<id>|, item_count|<n>.
    amount=0 drops the whole stack. One object can carry several units, so object count is
    not item count."""
    code = _DROP_LUA.format(item=int(item_id), amount=int(amount)).strip()
    raw = BRIDGE.submit(code, 20)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    meta = _kv_parse(_unescape_lua(raw))
    if not meta:
        return raw
    out = {}
    for k, v in meta.items():
        try:
            out[k] = int(v)
        except ValueError:
            out[k] = v
    return json.dumps(out, indent=2)


@mcp.tool()
@_safe
def collect_objects(item_id: int = 0, radius: float = 0, delay_ms: int = 60) -> str:
    """Pick up ground objects with a type=11 packet.

    The packet is SendPacketRaw(false, {type=11, state=0, value=<object oid>,
    px=<object pos.x>, py=<object pos.y>}). value is the object's oid, not the item id.
    item_id=0 collects everything; radius limits the distance in tiles. The avatar does not
    move."""
    delay = max(0, min(int(delay_ms), 1000))
    code = _COLLECT_LUA.format(item=int(item_id), radius=float(radius), delay=delay).strip()
    raw = BRIDGE.submit(code, 30)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    raw = _unescape_lua(raw)
    meta = _kv_parse(raw)
    if not meta:
        return json.dumps({"raw": raw}, indent=2)
    delta = {}
    for pasangan in (meta.get("delta_inv") or "").split(","):
        if ":" in pasangan:
            k, v = pasangan.split(":", 1)
            try:
                delta[int(k)] = int(v)
            except ValueError:
                delta[k] = v
    return json.dumps(
        {
            "target": int(item_id) if item_id else "all",
            "objects_before": int(meta.get("objects_before", 0) or 0),
            "sent": int(meta.get("sent", 0) or 0),
            "objects_left": int(meta.get("objects_left", 0) or 0),
            "inventory_delta": delta,
            "list": (meta.get("list") or "").split(),
        },
        indent=2,
    )


@mcp.tool()
@_safe
def list_objects() -> str:
    """Ground objects with their oid, item id, name, and tile."""
    raw = BRIDGE.submit(_LIST_OBJECTS_LUA.strip(), 20)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    raw = _unescape_lua(raw)
    title, _, body = raw.partition("|")
    items = [b for b in body.split("|") if b.strip()]
    return json.dumps({"count": len(items), "objects": items}, indent=2)


@mcp.tool()
@_safe
def find_path(target: str = "door", margin: int = 10, move: bool = False) -> str:
    """Find a walking route from the avatar to the nearest tile whose item name matches.

    The grid is read from the game and searched with BFS. The result lists waypoints plus
    an ASCII map with the route marked. move=True also moves the avatar with FindPath."""
    code = _FIND_PATH_LUA.format(target=_lua_literal(target), margin=int(margin))
    raw = BRIDGE.submit(code.strip(), 25)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    # enc() in bridge.lua quotes the string and escapes newlines
    raw = _unescape_lua(raw)
    if raw.strip() == "NOTFOUND" or "NOTFOUND" in raw[:40]:
        return f"no tile name contains '{target}' in this world"

    lines = raw.splitlines()
    meta: dict[str, str] = {}
    grid: list[str] = []
    in_grid = False
    for line in lines:
        if line.strip() == "grid":
            in_grid = True
            continue
        if not in_grid:
            if "=" in line:
                k, v = line.split("=", 1)
                meta[k] = v.strip()
        else:
            grid.append(line)

    tx, ty = (int(v) for v in meta["target"].split(","))
    px, py = (int(v) for v in meta["player"].split(","))
    x0, y0, x1, y1 = (int(v) for v in meta["bbox"].split(","))

    solids: set[tuple[int, int]] = set()
    for row in grid:
        y = int(row[:2])
        body = row[2:]
        for i, ch in enumerate(body):
            if ch in "#o":
                solids.add((x0 + i, y))
    # the door itself is not an obstacle
    solids.discard((tx, ty))

    steps = _bfs_path(solids, (px, py), (tx, ty), (x0, y0, x1, y1))
    if steps is None:
        return json.dumps(
            {
                "target": {"tile": [tx, ty], "name": meta.get("name")},
                "from": [px, py],
                "conclusion": "no route with these moves (blocked, or an item is required)",
            },
            indent=2,
        )

    moves = [s[2] for s in steps if s[2] != "start"]
    move_counts: dict[str, int] = {}
    for m in moves:
        move_counts[m] = move_counts.get(m, 0) + 1

    # ASCII map with the route
    marks = {(s[0], s[1]): "*" for s in steps}
    marks[(px, py)] = "A"
    marks[(tx, ty)] = "D"
    map_lines = []
    for row in grid:
        y = int(row[:2])
        body = list(row[2:])
        for i, ch in enumerate(body):
            p = (x0 + i, y)
            if p in marks:
                body[i] = marks[p]
        map_lines.append(f"{y:02d} {''.join(body)}")

    waypoints = [
        {
            "tile": [x, y],
            # world pixels, same as GetLocal().pos, not screen coordinates
            "world_pos": [x * 32 + 16, y * 32 + 32],
            "action": how,
        }
        for x, y, how in steps
    ]
    result = {
        "target": {"tile": [tx, ty], "fg": meta.get("fg"), "name": meta.get("name")},
        "from": [px, py],
        "steps": len(steps) - 1,
        "move_counts": move_counts,
        "waypoints": waypoints,
        "map": map_lines,
    }

    if move:
        # FindPath moves the avatar at once; CheckPath says whether a tile is passable.
    # If the target is solid, move to the last walkable waypoint instead.
        r = _move_to_tile(tx, ty)
        if r.get("blocked") or "error" in r:
            tries = 0
            for sx, sy, _how in reversed(steps):
                if tries >= 3:
                    break
                tries += 1
                r2 = _move_to_tile(sx, sy)
                if not r2.get("blocked") and "error" not in r2:
                    result["note"] = (
                        f"target tile ({tx},{ty}) is not passable; "
                        f"avatar moved to waypoint ({sx},{sy})"
                    )
                    r = r2
                    break
        if "error" in r:
            result["move"] = {"moved": False, "error": r["error"]}
        elif r.get("blocked"):
            result["move"] = {
                "moved": False,
                "reason": "CheckPath rejected every candidate tile (route blocked)",
            }
        else:
            result["move"] = {
                "moved": r.get("from") != r.get("to"),
                "from": r.get("from"),
                "to": r.get("to"),
                "world_pos": r.get("pos"),
            }

    return json.dumps(result, indent=2)


@mcp.tool()
@_safe
def lua_eval(code: str, timeout_s: float = RESULT_TIMEOUT) -> str:
    """Run Lua inside the game process and return its result."""
    return BRIDGE.submit(code, timeout_s)


@mcp.tool()
@_safe
def game_snapshot() -> str:
    """Player, world, inventory, object count, and the tile under the avatar."""
    code = """
local out = {}
local ok, local_p = pcall(function() return GetLocal() end)
if ok and local_p then
  out.name = local_p.name
  out.userid = local_p.userid
  if local_p.pos then
    -- position in pixels; 32 px = 1 tile (see docs/structures/Vec2.md)
    local px, py = local_p.pos.x, local_p.pos.y
    out.pos = { x = px, y = py }
    out.pos_tile = { x = math.floor(px / 32), y = math.floor(py / 32) }
    local okt, t = pcall(GetTile, math.floor(px / 32), math.floor(py / 32) + 1)
    if okt and type(t) == 'table' then
      out.tile_bawah = { fg = t.fg, bg = t.bg }
    end
  end
end
local okw, w = pcall(function() return GetWorld() end)
if okw and w then
  out.world = w.name
  out.world_size = w.width and (tostring(w.width) .. 'x' .. tostring(w.height)) or nil
end
local oki, inv = pcall(function() return GetInventory() end)
if oki and inv and inv.items then
  local n = 0
  for _ in pairs(inv.items) do n = n + 1 end
  out.inventory_items = n
end
local oko, objs = pcall(function() return GetObjectList() end)
if oko and objs then
  local n = 0
  for _ in pairs(objs) do n = n + 1 end
  out.objects = n
end
return out
"""
    return BRIDGE.submit(code.strip(), RESULT_TIMEOUT)


@mcp.tool()
@_safe
def traffic_start(max: int = 400) -> str:
    """Start capturing packets with the four Bothax hooks.
    Packets keep flowing; the capturer only reads."""
    return BRIDGE.submit(f"return _TRAFFIC_START({int(max)})", 10)


@mcp.tool()
@_safe
def traffic_stop() -> str:
    """Stop the packet capturer."""
    return BRIDGE.submit("return _TRAFFIC_STOP()", 10)


@mcp.tool()
@_safe
def traffic_dump(lines: int = 50, contains: str = "") -> str:
    """Latest capture lines, newest last. contains filters by type, for example SENDRAW."""
    raw = BRIDGE.submit(f"return _TRAFFIC_TEXT({int(lines)})", 10)
    # Lua returns one string separated by 0x1e, then enc() quotes it
    text = "\n".join(p for p in _unescape_lua(raw).split("\x1e") if p.strip()) or "(empty buffer)"
    if not contains:
        return text
    kept = [l for l in text.splitlines() if contains.lower() in l.lower()]
    return "\n".join(kept) if kept else f"(no line contains '{contains}'; {len(text.splitlines())} lines total)"


@mcp.tool()
@_safe
def traffic_stats() -> str:
    """Capturer statistics: active, events, buffer size, counts per kind."""
    return BRIDGE.submit("return _TRAFFIC_STATS()", 10)


@mcp.tool()
@_safe
def traffic_clear() -> str:
    """Empty the capture buffer without stopping the capturer."""
    return BRIDGE.submit("return _TRAFFIC_CLEAR()", 10)


@mcp.tool()
@_safe
def debug_log(lines: int = 40) -> str:
    """Bridge log from inside the game: commands, results, errors, and LogToConsole output."""
    return BRIDGE.submit(f"return _BRIDGE_LOG({int(lines)})", 8)


@mcp.tool()
@_safe
def debug_state() -> str:
    """Combined diagnostics: game process, bridge, logcat errors, and the bridge log tail."""
    out = {}
    try:
        pid = game_pid()
        out["game_pid"] = pid
        out["game_running"] = bool(pid)
        if pid:
            out["uid"] = adb_shell(f"dumpsys package {PACKAGE} | grep -m1 appId").strip()
            out["focus"] = adb_shell("dumpsys window | grep -m1 mCurrentFocus").strip()
        out["bridge"] = BRIDGE.status()
        crash = adb("logcat", "-d", "-t", "400").stdout
        errs = [l for l in crash.splitlines() if ("FATAL" in l or "AndroidRuntime" in l)]
        out["logcat_errors"] = errs[-5:] if errs else []
        if out["bridge"]["polling"]:
            out["bridge_log_tail"] = BRIDGE.submit("return _BRIDGE_LOG(8)", 8)
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return json.dumps(out, indent=2)


@mcp.tool()
@_safe
def api_list() -> str:
    """Local documentation index for Bothax functions and structures."""
    root = Path(__file__).with_name("docs")
    funcs = sorted(p.stem for p in (root / "functions").glob("*.md"))
    structs = sorted(p.stem for p in (root / "structures").glob("*.md"))
    examples = sorted(p.name for p in root.glob("*.lua"))
    return (
        f"FUNGSI ({len(funcs)}): {', '.join(funcs)}\n\n"
        f"STRUKTUR ({len(structs)}): {', '.join(structs)}\n\n"
        f"CONTOH: {', '.join(examples)}"
    )


@mcp.tool()
@_safe
def api_doc(name: str) -> str:
    """Read one documentation file, for example GetTile or GameUpdatePacket."""
    root = Path(__file__).with_name("docs")
    for cand in (
        root / "functions" / f"{name}.md",
        root / "structures" / f"{name}.md",
        root / name,
        root / f"{name}.lua",
    ):
        if cand.exists():
            return cand.read_text(encoding="utf-8")
    return f"no doc named '{name}'. Call api_list() for the index."


CONTROL_TOOLS = {
    "device_info": device_info,
    "screenshot": screenshot,
    "screenshot_crop": screenshot_crop,
    "panel_crop": panel_crop,
    "tap": tap,
    "swipe": swipe,
    "key": key,
    "type_text": type_text,
    "launch_game": launch_game,
    "stop_game": stop_game,
    "logcat": logcat,
    "install_apk": install_apk,
    "push_script": push_script,
    "list_scripts": list_scripts,
    "install_bridge": install_bridge,
    "bridge_status": bridge_status,
    "bridge_doctor": bridge_doctor,
    "adb_reconnect": adb_reconnect,
    "find_path": find_path,
    "go_to": go_to,
    "collect_objects": collect_objects,
    "list_objects": list_objects,
    "drop_item": drop_item,
    "lua_eval": lua_eval,
    "game_snapshot": game_snapshot,
    "traffic_start": traffic_start,
    "traffic_stop": traffic_stop,
    "traffic_dump": traffic_dump,
    "traffic_stats": traffic_stats,
    "traffic_clear": traffic_clear,
    "debug_log": debug_log,
    "debug_state": debug_state,
    "api_list": api_list,
    "api_doc": api_doc,
}


def main() -> None:
    port = start_bridge_server()
    if "--http-only" in sys.argv:
        if BRIDGE_MODE == "attached":
            print(
                f"port {port} is held by another bothax-mcp instance; "
                f"this --http-only process is not needed (exiting)",
                file=sys.stderr,
                flush=True,
            )
            raise SystemExit(3)
        print(f"bridge + HTTP control ready on 127.0.0.1:{port}", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return
    mcp.run()


if __name__ == "__main__":
    main()
