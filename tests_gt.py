#!/usr/bin/env python3
"""
Regression suite for bothax-mcp, server side only (no game, no device).

Covers the bugs that were already proven by reading the code:
  1. type_text: shell escaping leaked (&;|$() broke the command, apostrophes were
     dropped, so data disappeared).
  2. reap(): a slow command ran TWICE because it was re-queued after 6 seconds
     while the same instance was still working on it.
  3. reap(): a command stolen by a zombie instance MUST be re-sent; that behaviour
     has to stay.
  4. attached mode: /status must report the port owner, not an empty local queue.
  5. traffic_dump: Lua string unescaping ran in the wrong order.

Run: .venv/bin/python -m unittest -v tests_gt.py
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

import server as srv


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TypeTextEscaping(unittest.TestCase):
    def test_spaces_become_percent_s(self):
        self.assertEqual(srv._input_text_payload("hello world"), "hello%sworld")

    def test_apostrophe_preserved(self):
        # dulu: replace("'", "") -> data hilang diam-diam
        self.assertIn("it", srv._input_text_payload("it's ok"))

    def test_shell_metachars_quoted(self):
        cmd = srv._input_text_command("a&b;c|d$(e)")
        # seluruh payload harus berada dalam satu kutip tunggal
        self.assertTrue(cmd.endswith("'"), cmd)
        body = cmd.rsplit(" ", 1)[-1]
        self.assertTrue(body.startswith("'") and body.endswith("'"), cmd)
        inner = body[1:-1]
        self.assertEqual(inner, "a&b;c|d$(e)")

    def test_embedded_single_quote_escaped(self):
        cmd = srv._input_text_command("it's")
        # pola standar: '...'\''...'
        self.assertIn("'\\''", cmd, cmd)

    def test_non_ascii_rejected_loudly(self):
        out = srv.type_text("halo dunia ✓")
        self.assertTrue(out.startswith("ERROR"), out)


class ReapSemantics(unittest.TestCase):
    """reap() must not duplicate a command that is still running."""

    def setUp(self):
        self.bridge = srv._Bridge()
        self.bridge.last_poll = time.time()

    def _register(self, cid: str, code: str):
        """Mirror what submit() does: a pending box plus a queued command."""
        box = {"event": threading.Event(), "status": None, "text": None}
        self.bridge.pending[cid] = box
        self.bridge.cmds.put((cid, code))
        return box

    def test_slow_command_is_not_requeued(self):
        b = self.bridge
        self._register("cid-slow", "return 1")
        got = []

        def fake_game():
            cmd = b.next_cmd()  # take it the way /poll does
            got.append(cmd[0])
            time.sleep(0.2)
            # a "slow" command: no result for longer than retry_after
            for _ in range(4):
                b.reap(retry_after=0.05)
                time.sleep(0.05)

        t = threading.Thread(target=fake_game)
        t.start()
        t.join(5)
        extra = b.next_cmd()
        self.assertIsNone(extra, f"command re-sent while still running: {extra}")
        self.assertEqual(len(got), 1)

    def test_requeue_when_another_instance_takes_over(self):
        b = self.bridge
        b.active = "sid-old"
        self._register("cid1", "return 1")
        received = b.next_cmd()
        self.assertEqual(received[0], "cid1")
        # a new instance (/hello) takes over: the old sid's command is gone
        b.active = "sid-baru"
        b.reap(retry_after=0.0)
        again = b.next_cmd()
        self.assertIsNotNone(again, "a command stolen by a zombie instance was not re-sent")
        self.assertEqual(again[0], "cid1")

    def test_stale_command_discarded_after_timeout(self):
        """A command that already timed out must not run later."""
        b = self.bridge
        out = b.submit("return hapus()", 0.2)
        self.assertIn("TIMEOUT", out)
        self.assertIsNone(
            b.next_cmd(),
            "a stale command still ran after its caller gave up",
        )


class BridgeClaim(unittest.TestCase):
    """A stale sid must not block a new instance forever."""

    def setUp(self):
        self.bridge = srv._Bridge()

    def test_first_instance_is_active(self):
        self.assertTrue(self.bridge.claim("sid-a"))
        self.assertEqual(self.bridge.active, "sid-a")

    def test_other_sid_rejected_while_holder_polls(self):
        b = self.bridge
        b.claim("sid-a")
        b.last_poll = time.time()          # still alive
        self.assertFalse(b.claim("sid-b"), "a new sid took over a live instance")
        self.assertEqual(b.active, "sid-a")

    def test_stale_sid_taken_over_after_ttl(self):
        b = self.bridge
        b.claim("sid-a")
        b.last_poll = time.time() - (srv.ACTIVE_TTL + 5)
        self.assertTrue(b.claim("sid-b"), "sid basi memblokir instance baru (bug poll 'none' terus)")
        self.assertEqual(b.active, "sid-b")

    def test_empty_sid_always_served(self):
        b = self.bridge
        b.claim("sid-a")
        b.last_poll = time.time()
        self.assertTrue(b.claim(""))


class TrafficUnescape(unittest.TestCase):
    def test_roundtrip_escapes(self):
        # enc() Lua meng-escape \\ , \n dan " ; unescape harus kebalikannya
        lua_out = '"satu\\ntwo \\\\ quote \\"x\\""'
        self.assertEqual(srv._unescape_lua(lua_out), 'satu\ntwo \\ quote "x"')

    def test_not_double_unescaped(self):
        # \\" is backslash plus quote, not an escaped quote
        self.assertEqual(srv._unescape_lua('"a\\\\\\"b"'), 'a\\"b')


class FindPathLua(unittest.TestCase):
    def test_parses_escaped_result_string(self):
        """find_path returns a quoted Lua string, so newlines are unescaped before parsing."""
        raw = '"target=69,24\\nfg=6\\nname=main door\\nplayer=72,24\\nbbox=60,16,80,32\\ngrid\\n24....D..."'
        text = srv._unescape_lua(raw)
        lines = text.splitlines()
        self.assertEqual(lines[0], "target=69,24")
        self.assertEqual(lines[2], "name=main door")
        self.assertEqual(lines[5], "grid")
        self.assertTrue(lines[6].startswith("24"))

    def test_findpath_template_compiles(self):
        """Catch Lua syntax errors before the template reaches the game."""
        from lupa import LuaRuntime

        L = LuaRuntime(unpack_returned_tuples=True)
        code = srv._FIND_PATH_LUA.format(target=srv._lua_literal('door "x"'), margin=8)
        loader = L.eval("function(s) return load(s, '=findpath') end")
        res = loader(code)
        chunk, err = res if isinstance(res, tuple) else (res, None)
        self.assertIsNotNone(chunk, f"invalid Lua template: {err}")

    def test_lua_literal_escape(self):
        self.assertEqual(srv._lua_literal('a"b\\c'), '"a\\"b\\\\c"')

    def test_move_template_compiles(self):
        from lupa import LuaRuntime

        L = LuaRuntime(unpack_returned_tuples=True)
        code = srv._MOVE_LUA.format(tx=12, ty=34)
        loader = L.eval("function(s) return load(s, '=move') end")
        res = loader(code)
        chunk, err = res if isinstance(res, tuple) else (res, None)
        self.assertIsNotNone(chunk, f"invalid move template: {err}")
        self.assertNotIn("{tx}", code)

    def test_kv_parse(self):
        d = srv._kv_parse("chk=true ok=true err=true from=72,24 to=69,24 pos=2214,770")
        self.assertEqual(d["from"], "72,24")
        self.assertEqual(d["to"], "69,24")


class CollectLua(unittest.TestCase):
    """The collect template (type=11) must be valid Lua and use the object oid."""

    def _compile(self, code, name):
        from lupa import LuaRuntime

        L = LuaRuntime(unpack_returned_tuples=True)
        loader = L.eval("function(s) return load(s, '=" + name + "') end")
        res = loader(code)
        return res if isinstance(res, tuple) else (res, None)

    def test_collect_template_compiles(self):
        code = srv._COLLECT_LUA.format(item=0, radius=0.0, delay=60)
        chunk, err = self._compile(code, "collect")
        self.assertIsNotNone(chunk, f"invalid collect template: {err}")
        self.assertNotIn("{item}", code)

    def test_collect_template_uses_oid_and_type_11(self):
        code = srv._COLLECT_LUA.format(item=5026, radius=3.5, delay=10)
        self.assertIn("type = 11", code)
        self.assertIn("value = o.oid", code)
        self.assertIn("local item = 5026", code)
        self.assertIn("local radius = 3.5", code)

    def test_list_objects_template_compiles(self):
        chunk, err = self._compile(srv._LIST_OBJECTS_LUA, "listobj")
        self.assertIsNotNone(chunk, f"invalid list_objects template: {err}")

    def test_raw_template_has_no_double_brace(self):
        """A template without .format() must not contain `{{}}`.

        `{{}}` belongs to formatted templates only; left in a raw template, Lua reads it as a
        table holding an empty table, so `list[1]` is a table and `table.concat` fails at
        runtime."""
        self.assertNotIn("{{", srv._LIST_OBJECTS_LUA)

    def test_drop_template_compiles(self):
        code = srv._DROP_LUA.format(item=5026, amount=0)
        chunk, err = self._compile(code, "drop")
        self.assertIsNotNone(chunk, f"invalid drop template: {err}")

    def test_drop_template_has_trailing_pipe(self):
        """`item_drop|<id>|` needs the trailing pipe; without it the server ignores the drop."""
        code = srv._DROP_LUA.format(item=5026, amount=3)
        self.assertIn("dialog_name|drop", code)
        self.assertIn("item_drop|", code)
        self.assertIn("|' .. id .. '|", code)
        self.assertIn("local amount = 3", code)


class Pathfinding(unittest.TestCase):
    def _floor(self, y=26, x0=0, x1=20):
        return {(x, y) for x in range(x0, x1 + 1)}

    def test_flat_walk(self):
        solids = self._floor()
        p = srv._bfs_path(solids, (10, 25), (5, 25), (0, 20, 20, 30))
        self.assertIsNotNone(p)
        self.assertEqual((p[0][0], p[0][1]), (10, 25))
        self.assertEqual((p[-1][0], p[-1][1]), (5, 25))
        self.assertEqual({s[2] for s in p[1:]}, {"walk"})

    def test_jump_over_avatar_high_wall(self):
        solids = self._floor()
        solids.add((8, 25))  # a single block on a flat path
        p = srv._bfs_path(solids, (10, 25), (5, 25), (0, 20, 20, 30))
        self.assertIsNotNone(p, "a one-block obstacle must be cleared with a jump")
        self.assertIn("jump", [s[2] for s in p])

    def test_wall_too_high_has_no_route(self):
        solids = self._floor()
        solids |= {(8, 25), (8, 24), (8, 23), (8, 22), (8, 21), (8, 20)}
        p = srv._bfs_path(solids, (10, 25), (5, 25), (0, 20, 20, 30))
        self.assertIsNone(p)

    def test_fall_to_lower_floor(self):
        # high floor on the left, low floor on the right
        solids = {(x, 26) for x in range(0, 11)} | {(x, 29) for x in range(11, 21)}
        p = srv._bfs_path(solids, (5, 25), (15, 28), (0, 20, 20, 30))
        self.assertIsNotNone(p)
        self.assertIn("fall", [s[2] for s in p])


class Portability(unittest.TestCase):
    def test_find_adb_dari_path(self):
        import os as _os
        d = tempfile.mkdtemp()
        exe = Path(d) / ("adb.exe" if _os.name == "nt" else "adb")
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        old = _os.environ.get("PATH", "")
        _os.environ["PATH"] = d + _os.pathsep + old
        try:
            self.assertEqual(srv._find_adb(), str(exe))
        finally:
            _os.environ["PATH"] = old

    def test_tmp_path_not_hardcoded(self):
        import tempfile as _tf
        p = srv._tmp_png("unit")
        self.assertTrue(p.startswith(_tf.gettempdir()), p)
        self.assertNotIn("/tmp/", p.replace(_tf.gettempdir(), ""), p)

    def test_doctor_output_shape(self):
        data = json.loads(srv.bridge_doctor(auto_fix=False))
        self.assertIn("steps", data)
        self.assertIn("conclusion", data)
        self.assertTrue(any(s["check"] == "bridge port on host" for s in data["steps"]))


class AttachedMode(unittest.TestCase):
    """A second instance must serve /status and /enqueue through the port owner."""

    def test_attached_status_and_enqueue(self):
        port = free_port()
        owner = subprocess.Popen(
            [sys.executable, "server.py", "--http-only"],
            env={**os.environ, "GT_BRIDGE_PORT": str(port)},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.time() + 15
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/health", timeout=1
                    ) as r:
                        if r.read().strip() == b"ok":
                            break
                except Exception:
                    time.sleep(0.1)
            else:
                self.fail("owner is not ready")

            # instance kedua: harus masuk mode attached, bukan mati
            code = (
                "import json, server as s\n"
                "print(json.dumps(s.start_bridge_server()))\n"
                "print(json.dumps(s.BRIDGE.status()))\n"
            )
            out = subprocess.run(
                [sys.executable, "-c", code],
                env={**os.environ, "GT_BRIDGE_PORT": str(port)},
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            lines = [l for l in out.stdout.strip().splitlines() if l.startswith("{")]
            status = json.loads(lines[-1])
            self.assertEqual(status["mode"], "attached")
            self.assertEqual(status["port"], port)

            # the fake "game" client greets the owner and polls: only the owner knows
            # this state, so attached status has to reflect it.
            urllib.request.urlopen(f"http://127.0.0.1:{port}/hello?sid=test", timeout=3).read()
            threading.Thread(
                target=lambda: urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/poll?sid=uji", timeout=5
                ).read(),
                daemon=True,
            ).start()
            time.sleep(1.5)
            out2 = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import json, server as s; s.start_bridge_server(); "
                    "print(json.dumps(s.BRIDGE.status()))",
                ],
                env={**os.environ, "GT_BRIDGE_PORT": str(port)},
                capture_output=True,
                text=True,
                timeout=30,
            )
            st2 = json.loads(out2.stdout.strip().splitlines()[-1])
            self.assertEqual(st2["mode"], "attached", st2)
            self.assertIsNotNone(
                st2.get("last_poll_ago_s"),
                f"attached status did not read the owner state: {st2}",
            )

            # /enqueue on the owner: with no polling client it must time out
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/enqueue",
                data=json.dumps({"code": "return 1", "timeout": 1}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode()
            self.assertIn("TIMEOUT", body, body)
        finally:
            owner.terminate()
            try:
                owner.wait(5)
            except subprocess.TimeoutExpired:
                owner.kill()


if __name__ == "__main__":
    unittest.main(verbosity=2)
