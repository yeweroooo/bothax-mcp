#!/usr/bin/env python3
"""
gt-mcp — MCP server yang mengendalikan Growtopia + panel BINTERNAL.

Dua jalur kontrol:
  1. ADB   : tap, swipe, screenshot, launch, logcat, push script.
  2. BRIDGE: perintah Lua dieksekusi di dalam proses game lewat script
             bridge.lua yang polling HTTP (MakeRequest) ke 127.0.0.1,
             dihubungkan dengan `adb reverse tcp:PORT tcp:PORT`.

Jalankan: python server.py            (stdio, untuk klien MCP)
"""

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

# ---------------------------------------------------------------- konfigurasi

def _find_adb() -> str:
    """Cari adb di Linux/macOS/Windows tanpa jalur yang di-hardcode.

    Urutan: PATH -> ANDROID_SERIAL? tidak -> SDK env -> lokasi bawaan per OS.
    """
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
    return "adb"  # biarkan error-nya muncul saat dipakai, dengan pesan jelas


TMP_DIR = Path(tempfile.gettempdir())
# Path log bisa ditentukan sendiri lewat GT_LOG_PATH; default mengikuti TMPDIR
# (di sebagian setup TMPDIR bukan /tmp, jadi jangan diasumsikan).
LOG_PATH = Path(os.environ.get("GT_LOG_PATH") or (TMP_DIR / "bridge_http.log"))

ADB = _find_adb()
PACKAGE = "com.rtsoft.growtopia"
ACTIVITY = "com.rtsoft.growtopia/.Main"
SCRIPT_DIR = f"/sdcard/Android/media/{PACKAGE}/scripts"
BRIDGE_PORT = int(os.environ.get("GT_BRIDGE_PORT", "8770"))
POLL_WAIT = 1.0          # detik long-poll
ACTIVE_TTL = 20.0        # sid pemegang giliran dianggap mati setelah sunyi ini
RESULT_TIMEOUT = 12.0     # default tunggu hasil eval

mcp = MCPServer("growtopia-bothax")


def _safe(fn):
    """Jangan biarkan satu kegagalan adb membuat seluruh tool call meledak.

    Tanpa ini, `adb` yang timeout (device offline) naik sebagai traceback
    UnexpectedToolError dan klien hanya melihat "Error executing tool" tanpa
    penyebab yang bisa ditindaklanjuti.
    """

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa: BLE001
            return f"ERROR: {type(e).__name__}: {e}"

    return wrapper


# ------------------------------------------------------------------- adb util


def adb(*args: str, timeout: int = 20, check: bool = False) -> subprocess.CompletedProcess:
    """Panggil adb. Timeout pendek: adb bisa menggantung menit-menitan kalau
    ada transport offline (device wireless mati), dan itu membekukan tool MCP."""
    cmd = [ADB, *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"adb {' '.join(args[:2])} timeout {timeout}s "
            f"(device offline? cek `adb devices`, atau `adb kill-server`)"
        ) from None
    if check and p.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} gagal: {p.stderr.strip() or p.stdout.strip()}")
    return p


def adb_shell(cmd: str, timeout: int = 60) -> str:
    return adb("shell", cmd, timeout=timeout).stdout.strip()


def device_serial() -> str:
    out = adb("devices").stdout.splitlines()[1:]
    for line in out:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    raise RuntimeError("tidak ada perangkat ADB yang terhubung")


def game_pid() -> int | None:
    out = adb_shell(f"pidof {PACKAGE}")
    return int(out.split()[0]) if out.strip() else None


def _tmp_png(prefix: str) -> str:
    """Path sementara lintas OS (bukan /tmp hardcode) + resolusi milidetik."""
    return str(TMP_DIR / f"{prefix}_{int(time.time() * 1000)}.png")


def _screencap(dest: str) -> str:
    """Screenshot ke `dest`; raise RuntimeError dengan pesan yang bisa dibaca."""
    try:
        p = subprocess.run(
            [ADB, "exec-out", "screencap", "-p"], capture_output=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("screencap timeout 60s (device offline?)") from None
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(f"screencap gagal: {p.stderr.decode(errors='replace')[:200].strip()}")
    Path(dest).write_bytes(p.stdout)
    return dest


# ------------------------------------------------------- helpers: input teks

_LUA_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}


def _unescape_lua(s: str) -> str:
    """Kebalikan enc() di bridge.lua (\\, \\n, \\" ) dalam satu lintasan.

    Penggantian berurutan gaya lama (`\\\\"` lalu `\\\\\\\\`) merusak urutan
    campuran seperti `\\\\\\"` (backslash diikuti kutip ter-escape).
    """
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
    """Teks untuk `input text`: spasi jadi %s, sisanya apa adanya."""
    if any(ord(c) > 127 for c in text):
        raise ValueError(
            "teks berisi karakter non-ASCII; `input text` hanya menerima ASCII "
            "(pakai ADBKeyboard, atau kirim teks lewat bridge)"
        )
    if "\n" in text or "\r" in text:
        raise ValueError("baris baru tidak didukung; kirim key KEYCODE_ENTER terpisah")
    return text.replace(" ", "%s")


def _sh_single_quote(s: str) -> str:
    """Kutip untuk sh di perangkat: aman untuk & ; | $ ( ) ` * ? dan kutip."""
    return "'" + s.replace("'", "'\\''") + "'"


def _input_text_command(text: str) -> str:
    return f"input text {_sh_single_quote(_input_text_payload(text))}"


# ------------------------------------------------------------ bridge (HTTP)

class _Bridge:
    """
    Antrean perintah untuk sisi Lua + tempat hasilnya mendarat.

    Protokol (plain text, tanpa JSON di sisi Lua):
      bridge GET  /poll?sid=<id>  -> "<cmd_id>|<lua code>"  atau "none"
      bridge POST /result         -> body: "<cmd_id>|<ok|err>|<teks hasil>"
      server GET  /health         -> "ok"
    """

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
        # perintah yang sudah ditinggalkan pemanggilnya (timeout): jangan
        # dieksekusi terlambat saat bridge baru muncul belakangan.
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
            return f"TIMEOUT: tidak ada hasil dalam {timeout:.0f}s (bridge tidak polling?)"
        if box["status"] == "ok":
            return box["text"] or "(kosong)"
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
        """Untuk klien yang tidak mengirim id: layani perintah terbaru."""
        with self.lock:
            if not self.pending:
                self.last_result = time.time()
                return
            cid = next(reversed(self.pending))
        self.deliver(cid, status, text)

    def claim(self, sid: str) -> bool:
        """True bila instance ini boleh menerima perintah.

        Instance yang sudah aktif diprioritaskan selama masih mem-poll, supaya
        skrip lama yang masih hidup tidak dicampuri. Tapi giliran itu harus
        kedaluwarsa: tanpa TTL, sid basi (game di-restart / skrip dijalankan
        ulang) membuat instance baru dijawab 'none' selamanya — poll tampak
        jalan, perintah tidak pernah sampai.
        """
        now = time.time()
        if not sid:
            return True
        if not self.active:
            self.active, self.sid = sid, sid
            _trace(f"instance aktif: {sid}")
            return True
        if sid == self.active:
            return True
        if now - self.last_poll < ACTIVE_TTL:
            return False
        self.active, self.sid = sid, sid
        _trace(f"instance aktif (ambil alih, sunyi {now - self.last_poll:.0f}s): {sid}")
        return True

    def next_cmd(self) -> tuple[str, str] | None:
        while True:
            try:
                cmd = self.cmds.get_nowait()
            except queue.Empty:
                return None
            with self.lock:
                if cmd[0] in self.cancelled:
                    # pemanggil sudah menyerah (TIMEOUT): buang, jangan eksekusi
                    self.cancelled.discard(cmd[0])
                    continue
                self.last_poll = time.time()
                self.inflight[cmd[0]] = {
                    "code": cmd[1],
                    "ts": time.time(),
                    "tries": 1,
                    # instance yang menerima perintah ini: dasar keputusan reap()
                    "sid": self.active,
                }
            return cmd

    def reap(self, retry_after: float = 6.0, max_tries: int = 3) -> None:
        """Kirim ulang perintah yang JELAS hilang, bukan yang masih dikerjakan.

        Aturan lama (kirim ulang setelah retry_after tanpa hasil) mengeksekusi
        perintah dua kali setiap kali Lua butuh >6 detik — mis. `Sleep(8000)`
        atau loop berat. Sekarang perintah hanya dikirim ulang kalau instance
        yang menerimanya sudah digantikan instance lain (/hello dengan sid
        baru, biasanya karena game restart): hanya saat itu perintah benar-benar
        tidak akan pernah dijawab.
        """
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
            # Antrean lokal kosong dan menyesatkan: yang memegang klien adalah
            # instance pemilik port, jadi laporkan statusnya.
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
                    "error": f"pemilik port tidak menjawab: {e}",
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

# "owner"    : proses ini yang memegang port bridge (perilaku normal)
# "attached" : port sudah dipegang instance gt-mcp lain (mis. sisa
#              `server.py --http-only`), jadi perintah dikirim ke sana lewat
#              /enqueue. Tanpa ini proses MCP mati total hanya karena port
#              bentrok, dan seluruh tool ADB ikut hilang.
BRIDGE_MODE = "owner"



def _submit_remote(code: str, timeout: float) -> str:
    """Kirim perintah ke instance gt-mcp yang memegang port bridge."""
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
        return f"ERROR: instance bridge pemilik port tidak menjawab: {e}"


def _bridge_alive(timeout: float = 1.5) -> bool:
    """True kalau port bridge dipegang instance gt-mcp (punya /health -> ok)."""
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{BRIDGE_PORT}/health", timeout=timeout
        ) as r:
            return r.read().strip() == b"ok"
    except Exception:  # noqa: BLE001
        return False


def _trace(msg: str) -> None:
    """Catat lalu lintas HTTP bridge ke file agar bisa diaudit."""
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

    def do_GET(self):  # noqa: N802 (nama wajib dari BaseHTTPRequestHandler)
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
                _trace(f"HELLO instance aktif: {new_sid}")
            return self._send("ok")
        if self.path.startswith("/poll"):
            sid = (urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("sid") or [""])[0]
            if not BRIDGE.claim(sid):
                # instance lama masih memegang giliran: jangan beri perintah,
                # cukup jawab "none" (dan jangan update last_poll-nya)
                return self._send("none")
            deadline = time.time() + POLL_WAIT
            while time.time() < deadline:
                cmd = BRIDGE.next_cmd()
                if cmd:
                    _trace(f"POLL -> kirim {cmd[0]} ({len(cmd[1])} B) sid={sid or '-'}")
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
            # Jalur cadangan: hasil dikirim lewat GET query kalau POST gagal.
            q = urllib.parse.urlparse(self.path).query
            p = urllib.parse.parse_qs(q)
            cid = (p.get("id") or [""])[0]
            st = (p.get("st") or ["ok"])[0]
            data = (p.get("d") or [""])[0]
            if cid:
                _trace(f"RESULT-GET {cid} {st} ({len(data)} B)")
                BRIDGE.deliver(cid, st, data)
                return self._send("ok", 200)
            _trace("RESULT-GET tanpa id")
            return self._send("bad query", 400)
        if self.path.startswith("/call"):
            # Kontrol lokal tanpa klien MCP: /call?tool=game_snapshot&args=<json>
            from urllib.parse import parse_qs, urlparse

            q = parse_qs(urlparse(self.path).query)
            name = (q.get("tool") or [""])[0]
            fn = CONTROL_TOOLS.get(name)
            if not fn:
                return self._send("tool tidak dikenal: " + name, 404)
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
                # klien lama/tanpa id: serahkan ke perintah yang masih menunggu
                _trace(f"RESULT-TANPA-ID {parts[0]} ({len(parts[1])} B)")
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
        # Port sudah dipakai. Kalau pemiliknya instance gt-mcp (punya /health),
        # jangan mati: mode attached supaya tool MCP tetap tersedia.
        if _bridge_alive():
            BRIDGE_MODE = "attached"
            print(
                f"[gt-mcp] port {BRIDGE_PORT} dipegang instance gt-mcp lain; "
                f"mode attached (perintah Lua diteruskan ke sana)",
                file=sys.stderr,
                flush=True,
            )
            return BRIDGE_PORT
        raise RuntimeError(
            f"port {BRIDGE_PORT} dipakai proses lain yang bukan gt-mcp: {e}. "
            f"Cek `ss -ltnp | grep {BRIDGE_PORT}`, atau set GT_BRIDGE_PORT."
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


# ----------------------------------------------------------------- tools: adb

@mcp.tool()
@_safe
def device_info() -> str:
    """Info perangkat ADB, status game, dan status bridge Lua."""
    info = {}
    try:
        info["serial"] = device_serial()
        # Satu round-trip untuk 4 properti (dulu 4 panggilan adb terpisah;
        # tiap panggilan bisa 1-2 detik di device nirkabel).
        props = adb_shell(
            "getprop ro.build.version.release; getprop ro.build.version.sdk; "
            "getprop ro.product.cpu.abi; getprop ro.product.model"
        ).splitlines()
        for key, val in zip(("android", "sdk", "abi", "model"), props):
            info[key] = val.strip()
        # pid + fokus jendela dalam satu panggilan juga
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
    """Ambil screenshot dan kembalikan gambarnya (agar bisa dilihat langsung)."""
    return Image(path=_screencap(save_to or _tmp_png("gt_shot")))


@mcp.tool()
@_safe
def screenshot_crop(x0: int, y0: int, x1: int, y1: int, save_to: str = ""):
    """
    Ambil screenshot lalu potong ke area tertentu dan kembalikan gambarnya.
    Berguna untuk memperbesar panel mod sehingga widget kecil (checkbox,
    slider, field) terbaca jelas sebelum menentukan koordinat tap.
    Koordinat dalam piksel layar; (0,0) kiri-atas.
    """
    src = _screencap(_tmp_png("gt_full"))
    dst = save_to or _tmp_png("gt_crop")

    import pngio
    try:
        pngio.crop(src, dst, x0, y0, x1, y1)
    except Exception as e:  # noqa: BLE001
        return f"ERROR: crop gagal: {e}"
    return Image(path=dst)


@mcp.tool()
@_safe
def panel_crop(x0: int = 0, y0: int = 0, x1: int = 1100, y1: int = 950):
    """
    Potong area panel mod (default kiri-atas) supaya terbaca jelas.
    Setara screenshot_crop dengan default yang cocok untuk menu BINTERNAL.
    """
    return screenshot_crop(x0, y0, x1, y1)


@mcp.tool()
@_safe
def tap(x: int, y: int) -> str:
    """Ketuk koordinat layar."""
    adb("shell", f"input tap {x} {y}")
    return f"tap {x},{y}"


@mcp.tool()
@_safe
def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Geser dari (x1,y1) ke (x2,y2)."""
    adb("shell", f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
    return f"swipe {x1},{y1} -> {x2},{y2} ({duration_ms}ms)"


@mcp.tool()
@_safe
def key(code: str) -> str:
    """Kirim keyevent, mis. 'KEYCODE_BACK', 'KEYCODE_ENTER'."""
    adb("shell", f"input keyevent {code}")
    return f"key {code}"


@mcp.tool()
@_safe
def type_text(text: str) -> str:
    """Ketik teks ASCII. Spasi aman, karakter shell di-escape, kutip dipertahankan.

    Non-ASCII ditolak dengan pesan jelas: `input text` bawaan Android hanya
    menerima ASCII, dan sebelumnya teks seperti itu terkirim rusak tanpa error.
    """
    try:
        cmd = _input_text_command(text)
    except ValueError as e:
        return f"ERROR: {e}"
    p = adb("shell", cmd)
    if p.returncode != 0:
        return f"ERROR: input text gagal: {(p.stderr or p.stdout).strip()[:200]}"
    return f"typed {len(text)} chars"


@mcp.tool()
@_safe
def launch_game() -> str:
    """Jalankan Growtopia dan tunggu activity-nya fokus."""
    p = adb("shell", f"am start -W -n {ACTIVITY}", timeout=60)
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0 or "Error" in out:
        return f"ERROR: am start gagal: {out[:200]}"
    time.sleep(2)
    pid = game_pid()
    return f"launched, pid={pid}" if pid else "launched tapi proses belum terlihat"


@mcp.tool()
@_safe
def stop_game() -> str:
    """Force-stop Growtopia, lalu pastikan prosesnya benar-benar hilang."""
    p = adb("shell", f"am force-stop {PACKAGE}")
    if p.returncode != 0:
        return f"ERROR: force-stop gagal: {(p.stderr or p.stdout).strip()[:200]}"
    time.sleep(0.5)
    pid = game_pid()
    return "stopped" if pid is None else f"masih berjalan, pid={pid}"


@mcp.tool()
@_safe
def logcat(lines: int = 60, grep: str = "") -> str:
    """Baris logcat terakhir, opsional difilter.

    Saat memfilter, sampel diambil lebih banyak dulu (10x) supaya hasil tidak
    kosong hanya karena `lines` baris terakhir kebetulan tak memuat kata kunci.
    """
    fetch = max(lines * 10, 400) if grep else lines
    out = adb("logcat", "-d", "-t", str(fetch)).stdout
    if grep:
        kept = [l for l in out.splitlines() if grep.lower() in l.lower()]
        out = "\n".join(kept[-lines:])
    return out.strip() or "(kosong)"


@mcp.tool()
@_safe
def install_apk(apk_path: str) -> str:
    """Install APK (replace). Melaporkan kegagalan, bukan hanya output adb."""
    if not Path(apk_path).expanduser().exists():
        return f"ERROR: file tidak ada: {apk_path}"
    p = adb("install", "-r", str(Path(apk_path).expanduser()), timeout=600)
    text = (p.stdout + p.stderr).strip()
    if p.returncode != 0 or "Failure" in text:
        return f"ERROR: install gagal: {text[:300]}"
    return text


# -------------------------------------------------------------- tools: script

@mcp.tool()
@_safe
def push_script(local_path: str, name: str = "") -> str:
    """Salin file .lua ke folder script game di perangkat."""
    src = Path(local_path).expanduser()
    if not src.exists():
        return f"ERROR: file tidak ada: {local_path}"
    name = name or src.name
    adb_shell(f"mkdir -p {SCRIPT_DIR}")
    p = adb("push", str(src), f"{SCRIPT_DIR}/{name}")
    text = (p.stdout or p.stderr).strip()
    if p.returncode != 0:
        return f"ERROR: push gagal: {text[:200]}"
    return text or f"pushed {name}"


@mcp.tool()
@_safe
def list_scripts() -> str:
    """Daftar script di folder game."""
    out = adb_shell(f"ls -l {SCRIPT_DIR}")
    return out or "(folder kosong / belum ada)"


@mcp.tool()
@_safe
def install_bridge() -> str:
    """Push bridge.lua ke perangkat dan pasang adb reverse untuk kanal kontrol."""
    local = Path(__file__).with_name("bridge.lua")
    if not local.exists():
        return f"ERROR: {local} tidak ada"
    adb_shell(f"mkdir -p {SCRIPT_DIR}")
    push = adb("push", str(local), f"{SCRIPT_DIR}/bridge.lua")
    if push.returncode != 0:
        return f"ERROR: push bridge.lua gagal: {(push.stderr or push.stdout).strip()[:200]}"
    rev = adb("reverse", f"tcp:{BRIDGE_PORT}", f"tcp:{BRIDGE_PORT}")
    # Jangan percaya returncode saja: adb reverse bisa diam-diam tidak terpasang.
    listing = adb("reverse", "--list").stdout
    terpasang = f"tcp:{BRIDGE_PORT}" in listing
    if not terpasang:
        return (
            f"ERROR: adb reverse gagal dipasang (rc={rev.returncode}): "
            f"{(rev.stderr or rev.stdout).strip()[:200]}"
        )
    return (
        f"bridge.lua -> {SCRIPT_DIR}/bridge.lua\n"
        f"adb reverse tcp:{BRIDGE_PORT} -> terpasang\n"
        f"jalankan bridge.lua sekali dari menu executor game"
    )


# -------------------------------------------------------------- tools: bridge

@mcp.tool()
@_safe
def bridge_status() -> str:
    """Apakah bridge.lua sedang polling dari dalam game."""
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
    """Pulihkan transport adb yang drop (khas adb nirkabel / emulator).

    `address` opsional, mis. "192.168.240.112:5555" untuk menyambung ulang
    perangkat jaringan. Tanpa itu, hanya transport "offline" yang di-reconnect.
    """
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
        notes.append(f"devices gagal: {e}")
    if off:
        notes.append(adb("reconnect", timeout=25).stdout.strip() or "reconnect offline")
    devs = adb("devices", timeout=10).stdout.splitlines()[1:]
    ringkas = "; ".join(l.strip() for l in devs if l.strip()) or "(tidak ada device)"
    return "\n".join([*notes, f"device sekarang: {ringkas}"])


@mcp.tool()
@_safe
def bridge_doctor(auto_fix: bool = True) -> str:
    """Diagnosa seluruh rantai kontrol dan perbaiki yang aman diperbaiki.

    Diperiksa berurutan: biner adb, device online, proses game, mapping
    `adb reverse`, port bridge di host, lalu apakah bridge.lua polling. Kalau
    `auto_fix=True`, mapping reverse yang hilang dipasang ulang. Hasilnya
    berisi langkah mana yang gagal plus satu tindakan berikutnya.
    """
    steps: list[dict] = []
    fixes: list[str] = []

    def add(name: str, ok: bool, detail) -> None:
        steps.append({"cek": name, "ok": bool(ok), "detail": detail})

    add("biner adb", bool(shutil.which(ADB) or Path(ADB).exists()), ADB)

    devs: list[str] = []
    try:
        devs = [l.strip() for l in adb("devices", timeout=10).stdout.splitlines()[1:] if l.strip()]
    except Exception as e:  # noqa: BLE001
        add("adb devices", False, str(e))
    online = [l.split()[0] for l in devs if l.split()[1:2] == ["device"]]
    offline = [l.split()[0] for l in devs if l.split()[1:2] in (["offline"], ["unauthorized"])]
    add("device online", bool(online), online or (offline and [f"{s} (offline/unauthorized)" for s in offline]) or "tidak ada")

    pid = None
    if online:
        try:
            pid = game_pid()
            add("game berjalan", pid is not None, f"pid={pid}" if pid else "Growtopia tidak jalan")
        except Exception as e:  # noqa: BLE001
            add("game berjalan", False, str(e))
        try:
            listing = adb("reverse", "--list", timeout=10).stdout
            mapped = f"tcp:{BRIDGE_PORT}" in listing
            if not mapped and auto_fix:
                adb("reverse", f"tcp:{BRIDGE_PORT}", f"tcp:{BRIDGE_PORT}", timeout=10)
                listing = adb("reverse", "--list", timeout=10).stdout
                mapped = f"tcp:{BRIDGE_PORT}" in listing
                if mapped:
                    fixes.append(f"adb reverse tcp:{BRIDGE_PORT} dipasang ulang")
            add("adb reverse", mapped, listing.strip() or "(belum ada mapping)")
        except Exception as e:  # noqa: BLE001
            add("adb reverse", False, str(e))

    port_ok = _port_open("127.0.0.1", BRIDGE_PORT)
    add("port bridge host", port_ok, f"127.0.0.1:{BRIDGE_PORT}")

    st = BRIDGE.status()
    polling = bool(st.get("polling"))
    add("bridge polling", polling, st)
    diag = st.get("last_diag")
    if diag:
        add("diag terakhir", True, diag)

    if not port_ok:
        verdict = (
            "belum ada server bridge di port ini; jalankan `python server.py "
            "(--http-only untuk bridge saja)` atau aktifkan MCP-nya"
        )
    elif not online:
        verdict = (
            "device tidak online: sambungkan USB atau `adb_reconnect('ip:5555')`; "
            "kalau masih `unauthorized`, terima dialog debugging di perangkat"
        )
    elif pid is None:
        verdict = "device siap tapi Growtopia belum jalan → launch_game()"
    elif not polling:
        verdict = (
            "port + reverse siap, tapi bridge.lua belum polling. Jalankan "
            "bridge.lua dari executor DAN pastikan daftar API di setting "
            "executor dicentang (tanpa itu MakeRequest gagal sebelum keluar "
            "dari game). Cek baris 'PROBE /health' di konsol mod."
        )
    else:
        verdict = "rantai lengkap: ADB → adb reverse → bridge.lua aktif"

    return json.dumps(
        {"langkah": steps, "perbaikan": fixes, "kesimpulan": verdict}, indent=2
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
    """Cari jalur di grid dengan model gerak Growtopia sederhana.

    Tepi yang diizinkan: jalan datar, jatuh ke bawah, turun satu petak ke
    samping, dan lompat naik 1 petak (butuh ruang kepala). Lompat 2 petak tidak
    dimodelkan karena tinggi lompat di game ±1,5 petak.
    """
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
        # jalan datar / turun tebing
        for dx in (-1, 1):
            side = (x + dx, y)
            if free(side):
                if supported(side):
                    push(cur, side, 1, "jalan")
                else:
                    # melangkah ke ruang kosong: jatuh sampai ada pijakan
                    ny = y
                    while ny + 1 <= y1 and free((x + dx, ny + 1)):
                        ny += 1
                    push(cur, (x + dx, ny), 1 + (ny - y), "jatuh")
            diag = (x + dx, y + 1)
            if free(diag) and supported(diag):
                push(cur, diag, 1, "turun")
        # lompat naik 1 petak (ruang kepala 2 petak harus kosong)
        for dx in (-1, 0, 1):
            up = (x + dx, y - 1)
            if free(up) and free((x + dx, y - 2)):
                push(cur, up, 2, "lompat")
        # jatuh lurus ke bawah
        down = (x, y + 1)
        if free(down):
            ny = y
            while ny + 1 <= y1 and free((x, ny + 1)):
                ny += 1
            push(cur, (x, ny), 1 + (ny - y), "jatuh")

    target = goal
    if target not in dist:
        # boleh berhenti di petak sebelah pintu kalau pintunya solid
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
        how = entry[1] if entry else "mulai"
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
  return string.format('BLOCKED dari=%d,%d tile=%d,%d',
    math.floor(p0.x / 32), math.floor(p0.y / 32), tx, ty)
end
local okf, errf = pcall(FindPath, tx, ty)
-- FindPath kadang butuh waktu lebih dari satu tick: tunggu sampai posisi
-- berubah (maks ~1,5 s) sebelum menyimpulkan gagal.
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
return string.format('chk=true ok=%s err=%s dari=%d,%d ke=%d,%d pos=%.0f,%.0f tries=%d',
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
    """Pindahkan avatar dengan FindPath bawaan game (instan), lalu verifikasi posisi."""
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
    """Pindahkan avatar ke tile tertentu memakai `FindPath` bawaan game.

    Alurnya: `CheckPath(tilex,tiley)` dulu (tile padat tidak dipaksa), lalu
    `FindPath`, lalu posisi dibaca ulang untuk memastikan avatar benar pindah.
    Catatan: ini fitur teleport/jalan cepat milik klien, bukan langkah-per-langkah.
    """
    r = _move_to_tile(tilex, tiley)
    if "error" in r:
        return r["error"]
    if r.get("blocked"):
        return json.dumps(
            {
                "bergerak": False,
                "alasan": f"CheckPath({tilex},{tiley}) = false (tile padat / tidak bisa dilalui)",
                "dari": r.get("dari"),
            },
            indent=2,
        )
    return json.dumps(
        {
            "bergerak": r.get("dari") != r.get("ke"),
            "dari": r.get("dari"),
            "ke": r.get("ke"),
            "target": [int(tilex), int(tiley)],
            "pos_dunia": r.get("pos"),
            "findpath_ok": r.get("ok") == "true",
            "tunggu_tick": r.get("tries"),
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
return string.format('objek_awal=%d dikirim=%d objek_sisa=%d delta_inv=%s daftar=%s',
  total, sent, sisa, table.concat(delta, ','), table.concat(daftar, ' '))
"""

_LIST_OBJECTS_LUA = r"""
local daftar = {}
for _, o in pairs(GetObjectList()) do
  local nm = '?'
  local ok, info = pcall(GetItemInfo, o.id)
  if ok and info and info.name then nm = tostring(info.name) end
  daftar[#daftar + 1] = string.format('oid=%s id=%s nama=%s tile=%d,%d',
    tostring(o.oid), tostring(o.id), nm,
    math.floor(o.pos.x / 32), math.floor(o.pos.y / 32))
end
table.sort(daftar)
return string.format('jumlah=%d|%s', #daftar, table.concat(daftar, '|'))
"""


_DROP_LUA = r"""
local id = {item}
local amount = {amount}
local ada = 0
for _, it in pairs(GetInventory()) do if it.id == id then ada = ada + it.amount end end
if ada <= 0 then return 'id={item} inv_awal=0 inv_akhir=0 jumlah=0 objek=0 total_amount=0 alasan=tidakada' end
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
return string.format('id=%d jumlah=%d inv_awal=%d inv_akhir=%d objek=%d total_amount=%d alasan=ok',
  id, amount, ada, sisa, objs, total)
"""


@mcp.tool()
@_safe
def drop_item(item_id: int, amount: int = 0) -> str:
    """Jatuhkan item ke tanah di tile avatar — satu paket, bukan dialog manual.

    `SendPacket(2, "action|dialog_return\\ndialog_name|drop\\nitem_drop|<id>|\\nitem_count|<n>\\n")`
    dengan pipa penutup setelah id. `amount=0` = seluruh isi stack (**drop all**).

    Hasil memuat `objek` (jumlah objek di world sesudahnya) dan `total_amount`
    (jumlah unit item itu yang benar-benar jadi objek) — satu objek bisa membawa
    beberapa unit, jadi jangan samakan jumlah barang dengan jumlah objek.
    """
    code = _DROP_LUA.format(item=int(item_id), amount=int(amount)).strip()
    raw = BRIDGE.submit(code, 20)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    meta = _kv_parse(_unescape_lua(raw))
    if not meta:
        return raw
    hasil = {}
    for k, v in meta.items():
        try:
            hasil[k] = int(v)
        except ValueError:
            hasil[k] = v
    return json.dumps(hasil, indent=2)


@mcp.tool()
@_safe
def collect_objects(item_id: int = 0, radius: float = 0, delay_ms: int = 60) -> str:
    """Pungut objek jatuh (drop) di world dengan paket `type=11`.

    Mekanismenya terbukti live: `SendPacketRaw(false, {type=11, state=0,
    value=<oid objek>, px=<pos.x objek>, py=<pos.y objek>, x/y=pos avatar})`.
    `value` harus **oid objek** (field `WorldObject.oid`), bukan item id —
    inilah bedanya dengan paket place/break yang memakai item id.

    `item_id=0` memungut semua objek; `radius>0` membatasi jarak dalam petak
    dari avatar. Tanpa perintah gerak: avatar tidak berpindah tile.
    """
    delay = max(0, min(int(delay_ms), 1000))
    code = _COLLECT_LUA.format(item=int(item_id), radius=float(radius), delay=delay).strip()
    raw = BRIDGE.submit(code, 30)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    raw = _unescape_lua(raw)
    meta = _kv_parse(raw)
    if not meta:
        return json.dumps({"mentah": raw}, indent=2)
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
            "target": int(item_id) if item_id else "semua",
            "objek_awal": int(meta.get("objek_awal", 0) or 0),
            "dikirim": int(meta.get("dikirim", 0) or 0),
            "objek_sisa": int(meta.get("objek_sisa", 0) or 0),
            "inventori_berubah": delta,
            "daftar": (meta.get("daftar") or "").split(),
        },
        indent=2,
    )


@mcp.tool()
@_safe
def list_objects() -> str:
    """Daftar objek/drop yang sedang ada di world (oid, item id, nama, tile)."""
    raw = BRIDGE.submit(_LIST_OBJECTS_LUA.strip(), 20)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    raw = _unescape_lua(raw)
    judul, _, isi = raw.partition("|")
    items = [b for b in isi.split("|") if b.strip()]
    return json.dumps({"jumlah": len(items), "objek": items}, indent=2)


@mcp.tool()
@_safe
def find_path(target: str = "door", margin: int = 10, move: bool = False) -> str:
    """Cari jalur jalan dari avatar ke objek terdekat yang namanya cocok.

    `target` dicocokkan ke nama item (tanpa peduli huruf besar/kecil), mis.
    "door", "white door", "chest", "portal". Grid dibaca langsung dari game
    (GetTiles/GetTile), lalu BFS dengan model gerak: jalan, turun, jatuh, dan
    lompat naik 1 petak. Hasil: daftar waypoint petak + piksel + peta ASCII
    dengan jalur ditandai '*'.

    `move=True` langsung memindahkan avatar ke target memakai `FindPath`
    bawaan game (CheckPath dulu; kalau target padat, ke waypoint terdekat).
    """
    code = _FIND_PATH_LUA.format(target=_lua_literal(target), margin=int(margin))
    raw = BRIDGE.submit(code.strip(), 25)
    if raw.startswith("ERROR") or raw.startswith("TIMEOUT"):
        return raw
    # hasil string di-quote dan newline-nya di-escape oleh enc() di bridge.lua
    raw = _unescape_lua(raw)
    if raw.strip() == "NOTFOUND" or "NOTFOUND" in raw[:40]:
        return f"tidak ada tile dengan nama mengandung '{target}' di world ini"

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
    # pintu sendiri bukan penghalang
    solids.discard((tx, ty))

    steps = _bfs_path(solids, (px, py), (tx, ty), (x0, y0, x1, y1))
    if steps is None:
        return json.dumps(
            {
                "target": {"tile": [tx, ty], "name": meta.get("name")},
                "dari": [px, py],
                "kesimpulan": "tidak ada jalur dengan model gerak ini (terhalang / perlu item)",
            },
            indent=2,
        )

    moves = [s[2] for s in steps if s[2] != "mulai"]
    ringkas: dict[str, int] = {}
    for m in moves:
        ringkas[m] = ringkas.get(m, 0) + 1

    # peta ASCII dengan jalur
    marks = {(s[0], s[1]): "*" for s in steps}
    marks[(px, py)] = "A"
    marks[(tx, ty)] = "D"
    peta = []
    for row in grid:
        y = int(row[:2])
        body = list(row[2:])
        for i, ch in enumerate(body):
            p = (x0 + i, y)
            if p in marks:
                body[i] = marks[p]
        peta.append(f"{y:02d} {''.join(body)}")

    waypoints = [
        {
            "tile": [x, y],
            # koordinat dunia (sama seperti GetLocal().pos), bukan koordinat layar
            "pos_dunia": [x * 32 + 16, y * 32 + 32],
            "aksi": how,
        }
        for x, y, how in steps
    ]
    hasil = {
        "target": {"tile": [tx, ty], "fg": meta.get("fg"), "name": meta.get("name")},
        "dari": [px, py],
        "langkah": len(steps) - 1,
        "rincian_gerak": ringkas,
        "waypoints": waypoints,
        "peta": peta,
    }

    if move:
        # FindPath bawaan game memindahkan avatar secara instan; CheckPath
        # menentukan apakah tile tujuan boleh dipakai. Kalau target padat,
        # pindah ke waypoint terakhir yang bisa dilalui.
        r = _move_to_tile(tx, ty)
        if r.get("blocked") or "error" in r:
            dicoba = 0
            for sx, sy, _how in reversed(steps):
                if dicoba >= 3:
                    break
                dicoba += 1
                r2 = _move_to_tile(sx, sy)
                if not r2.get("blocked") and "error" not in r2:
                    hasil["catatan"] = (
                        f"tile target ({tx},{ty}) tidak bisa dilalui; "
                        f"avatar dipindah ke waypoint ({sx},{sy})"
                    )
                    r = r2
                    break
        if "error" in r:
            hasil["pindah"] = {"bergerak": False, "error": r["error"]}
        elif r.get("blocked"):
            hasil["pindah"] = {
                "bergerak": False,
                "alasan": "CheckPath menolak semua kandidat tile (jalur terhalang)",
            }
        else:
            hasil["pindah"] = {
                "bergerak": r.get("dari") != r.get("ke"),
                "dari": r.get("dari"),
                "ke": r.get("ke"),
                "pos_dunia": r.get("pos"),
            }

    return json.dumps(hasil, indent=2)


@mcp.tool()
@_safe
def lua_eval(code: str, timeout_s: float = RESULT_TIMEOUT) -> str:
    """
    Eksekusi kode Lua di dalam proses game dan kembalikan hasilnya.

    Contoh: lua_eval("return GetLocal().name")
            lua_eval("local w = GetWorld(); return w.name")
    """
    return BRIDGE.submit(code, timeout_s)


@mcp.tool()
@_safe
def game_snapshot() -> str:
    """Ringkasan state game: pemain lokal, dunia, inventori, jumlah objek."""
    code = """
local out = {}
local ok, local_p = pcall(function() return GetLocal() end)
if ok and local_p then
  out.name = local_p.name
  out.userid = local_p.userid
  if local_p.pos then
    -- pos dalam pixel; 32 px = 1 petak (lihat docs/structures/Vec2.md)
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
    """
    Mulai menangkap lalu lintas paket di dalam game lewat hook
    OnSendPacket / OnSendPacketRaw / OnVariant / OnProcessTankUpdate.
    Paket tetap diteruskan; capturer hanya membaca.
    """
    return BRIDGE.submit(f"return _TRAFFIC_START({int(max)})", 10)


@mcp.tool()
@_safe
def traffic_stop() -> str:
    """Hentikan penangkapan lalu lintas paket."""
    return BRIDGE.submit("return _TRAFFIC_STOP()", 10)


@mcp.tool()
@_safe
def traffic_dump(lines: int = 50, contains: str = "") -> str:
    """
    Ambil n kejadian lalu lintas terakhir (terbaru di bawah).
    `contains` memfilter baris, mis. 'VARIANT', 'SENDRAW', 'OnConsoleMessage'.
    """
    raw = BRIDGE.submit(f"return _TRAFFIC_TEXT({int(lines)})", 10)
    # hasil dari Lua berupa satu string dengan pemisah 0x1e, lalu di-quote oleh enc()
    text = "\n".join(p for p in _unescape_lua(raw).split("\x1e") if p.strip()) or "(buffer kosong)"
    if not contains:
        return text
    kept = [l for l in text.splitlines() if contains.lower() in l.lower()]
    return "\n".join(kept) if kept else f"(tidak ada baris mengandung '{contains}'; total {len(text.splitlines())} baris)"


@mcp.tool()
@_safe
def traffic_stats() -> str:
    """Statistik capturer: aktif, total kejadian, isi buffer, jumlah per jenis."""
    return BRIDGE.submit("return _TRAFFIC_STATS()", 10)


@mcp.tool()
@_safe
def traffic_clear() -> str:
    """Kosongkan buffer lalu lintas tanpa menghentikan capturer."""
    return BRIDGE.submit("return _TRAFFIC_CLEAR()", 10)


@mcp.tool()
@_safe
def debug_log(lines: int = 40) -> str:
    """
    Log internal dari dalam game: setiap perintah yang masuk, hasilnya, error,
    dan semua output LogToConsole milik script lain. Diambil dari buffer
    _BRIDGE_LOG di bridge.lua (maks 300 baris).
    """
    return BRIDGE.submit(f"return _BRIDGE_LOG({int(lines)})", 8)


@mcp.tool()
@_safe
def debug_state() -> str:
    """Ringkasan diagnostik: proses game, bridge, error logcat, dan log bridge."""
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
    """Daftar dokumentasi API (fungsi) dan struktur data yang tersedia lokal."""
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
    """
    Baca dokumentasi resmi sebuah fungsi/struktur/contoh (mis. 'GetTile',
    'GameUpdatePacket', '02_hooks.lua').
    """
    root = Path(__file__).with_name("docs")
    for cand in (
        root / "functions" / f"{name}.md",
        root / "structures" / f"{name}.md",
        root / name,
        root / f"{name}.lua",
    ):
        if cand.exists():
            return cand.read_text(encoding="utf-8")
    return f"tidak ada doc bernama '{name}'. Panggil api_list() untuk daftar."


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
                f"port {port} sudah dipegang instance gt-mcp lain; "
                f"proses --http-only ini tidak diperlukan (keluar)",
                file=sys.stderr,
                flush=True,
            )
            raise SystemExit(3)
        print(f"bridge + kontrol HTTP siap di 127.0.0.1:{port}", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return
    mcp.run()


if __name__ == "__main__":
    main()
