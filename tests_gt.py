#!/usr/bin/env python3
"""
Regression suite untuk bothax-mcp server-side (tanpa game, tanpa perangkat).

Fokus pada bug yang sudah terbukti dari pembacaan kode:
  1. type_text: escaping shell bocor (karakter &;|$() memutus perintah,
     apostrof dibuang = data hilang).
  2. reap(): perintah yang lambat dieksekusi DUA KALI karena di-requeue
     setelah 6 detik walau instance yang sama masih mengerjakannya.
  3. reap(): perintah yang dicuri instance zombie HARUS dikirim ulang
     (perilaku yang ingin dipertahankan).
  4. mode attached: /status harus melaporkan status instance pemilik port,
     bukan antrean lokal yang kosong.
  5. traffic_dump: unescape string Lua salah urutan.

Jalankan: .venv/bin/python -m unittest -v tests_gt.py
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
    """reap() tidak boleh menduplikasi perintah yang masih dikerjakan."""

    def setUp(self):
        self.bridge = srv._Bridge()
        self.bridge.last_poll = time.time()

    def _register(self, cid: str, code: str):
        """Tiru apa yang dilakukan submit(): pending box + perintah di antrean."""
        box = {"event": threading.Event(), "status": None, "text": None}
        self.bridge.pending[cid] = box
        self.bridge.cmds.put((cid, code))
        return box

    def test_slow_command_is_not_requeued(self):
        b = self.bridge
        self._register("cid-slow", "return 1")
        got = []

        def fake_game():
            cmd = b.next_cmd()  # ambil seperti /poll
            got.append(cmd[0])
            time.sleep(0.2)
            # perintah "lambat": belum ada hasil selama > retry_after
            for _ in range(4):
                b.reap(retry_after=0.05)
                time.sleep(0.05)

        t = threading.Thread(target=fake_game)
        t.start()
        t.join(5)
        extra = b.next_cmd()
        self.assertIsNone(extra, f"perintah dikirim ulang padahal masih jalan: {extra}")
        self.assertEqual(len(got), 1)

    def test_requeue_when_another_instance_takes_over(self):
        b = self.bridge
        b.active = "sid-lama"
        self._register("cid1", "return 1")
        received = b.next_cmd()
        self.assertEqual(received[0], "cid1")
        # instance baru (/hello) mengambil alih: perintah milik sid lama hilang
        b.active = "sid-baru"
        b.reap(retry_after=0.0)
        again = b.next_cmd()
        self.assertIsNotNone(again, "perintah yang dicuri zombie tidak dikirim ulang")
        self.assertEqual(again[0], "cid1")

    def test_stale_command_discarded_after_timeout(self):
        """Perintah yang sudah TIMEOUT tidak boleh dieksekusi belakangan."""
        b = self.bridge
        out = b.submit("return hapus()", 0.2)
        self.assertIn("TIMEOUT", out)
        self.assertIsNone(
            b.next_cmd(),
            "perintah basi tetap dieksekusi setelah pemanggilnya menyerah",
        )


class BridgeClaim(unittest.TestCase):
    """sid basi tidak boleh memblokir instance baru selamanya."""

    def setUp(self):
        self.bridge = srv._Bridge()

    def test_instance_pertama_langsung_aktif(self):
        self.assertTrue(self.bridge.claim("sid-a"))
        self.assertEqual(self.bridge.active, "sid-a")

    def test_sid_lain_ditolak_selama_pemegang_masih_poll(self):
        b = self.bridge
        b.claim("sid-a")
        b.last_poll = time.time()          # masih hidup
        self.assertFalse(b.claim("sid-b"), "sid baru menyerobot instance yang masih aktif")
        self.assertEqual(b.active, "sid-a")

    def test_sid_basi_diambil_alih_setelah_ttl(self):
        b = self.bridge
        b.claim("sid-a")
        b.last_poll = time.time() - (srv.ACTIVE_TTL + 5)
        self.assertTrue(b.claim("sid-b"), "sid basi memblokir instance baru (bug poll 'none' terus)")
        self.assertEqual(b.active, "sid-b")

    def test_sid_kosong_selalu_dilayani(self):
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
        # \\" adalah backslash + kutip, bukan kutip yang di-escape
        self.assertEqual(srv._unescape_lua('"a\\\\\\"b"'), 'a\\"b')


class FindPathLua(unittest.TestCase):
    def test_parse_hasil_string_terescape(self):
        """Hasil find_path berupa string Lua ter-quote: newline harus di-unescape dulu."""
        raw = '"target=69,24\\nfg=6\\nname=main door\\nplayer=72,24\\nbbox=60,16,80,32\\ngrid\\n24....D..."'
        text = srv._unescape_lua(raw)
        lines = text.splitlines()
        self.assertEqual(lines[0], "target=69,24")
        self.assertEqual(lines[2], "name=main door")
        self.assertEqual(lines[5], "grid")
        self.assertTrue(lines[6].startswith("24"))

    def test_template_bisa_di_compile_lua(self):
        """Tangkap error sintaks Lua di template sebelum dikirim ke game."""
        from lupa import LuaRuntime

        L = LuaRuntime(unpack_returned_tuples=True)
        code = srv._FIND_PATH_LUA.format(target=srv._lua_literal('door "x"'), margin=8)
        loader = L.eval("function(s) return load(s, '=findpath') end")
        res = loader(code)
        chunk, err = res if isinstance(res, tuple) else (res, None)
        self.assertIsNotNone(chunk, f"template Lua tidak valid: {err}")

    def test_lua_literal_escape(self):
        self.assertEqual(srv._lua_literal('a"b\\c'), '"a\\"b\\\\c"')

    def test_template_move_bisa_di_compile(self):
        from lupa import LuaRuntime

        L = LuaRuntime(unpack_returned_tuples=True)
        code = srv._MOVE_LUA.format(tx=12, ty=34)
        loader = L.eval("function(s) return load(s, '=move') end")
        res = loader(code)
        chunk, err = res if isinstance(res, tuple) else (res, None)
        self.assertIsNotNone(chunk, f"template move tidak valid: {err}")
        self.assertNotIn("{tx}", code)

    def test_kv_parse(self):
        d = srv._kv_parse("chk=true ok=true err=true dari=72,24 ke=69,24 pos=2214,770")
        self.assertEqual(d["dari"], "72,24")
        self.assertEqual(d["ke"], "69,24")


class CollectLua(unittest.TestCase):
    """Template paket collect (type=11) harus valid dan memakai oid objek."""

    def _compile(self, code, name):
        from lupa import LuaRuntime

        L = LuaRuntime(unpack_returned_tuples=True)
        loader = L.eval("function(s) return load(s, '=" + name + "') end")
        res = loader(code)
        return res if isinstance(res, tuple) else (res, None)

    def test_template_collect_bisa_di_compile(self):
        code = srv._COLLECT_LUA.format(item=0, radius=0.0, delay=60)
        chunk, err = self._compile(code, "collect")
        self.assertIsNotNone(chunk, f"template collect tidak valid: {err}")
        self.assertNotIn("{item}", code)

    def test_template_collect_pakai_oid_dan_type_11(self):
        code = srv._COLLECT_LUA.format(item=5026, radius=3.5, delay=10)
        self.assertIn("type = 11", code)
        self.assertIn("value = o.oid", code)
        self.assertIn("local item = 5026", code)
        self.assertIn("local radius = 3.5", code)

    def test_template_list_objects_bisa_di_compile(self):
        chunk, err = self._compile(srv._LIST_OBJECTS_LUA, "listobj")
        self.assertIsNotNone(chunk, f"template list_objects tidak valid: {err}")

    def test_template_tanpa_brace_ganda(self):
        """Template yang tidak lewat .format() tidak boleh punya `{{}}`.

        `{{}}` hanya untuk template ber-.format(); kalau tertinggal di template
        mentah, Lua membacanya sebagai tabel berisi tabel kosong. Akibatnya
        `daftar[1]` jadi table dan `table.concat` gagal saat runtime.
        """
        self.assertNotIn("{{", srv._LIST_OBJECTS_LUA)

    def test_template_drop_bisa_di_compile(self):
        code = srv._DROP_LUA.format(item=5026, amount=0)
        chunk, err = self._compile(code, "drop")
        self.assertIsNotNone(chunk, f"template drop tidak valid: {err}")

    def test_template_drop_pakai_pipa_penutup(self):
        """`item_drop|<id>|` butuh pipa penutup; tanpa itu server tidak drop."""
        code = srv._DROP_LUA.format(item=5026, amount=3)
        self.assertIn("dialog_name|drop", code)
        self.assertIn("item_drop|", code)
        self.assertIn("|' .. id .. '|", code)
        self.assertIn("local amount = 3", code)


class Pathfinding(unittest.TestCase):
    def _floor(self, y=26, x0=0, x1=20):
        return {(x, y) for x in range(x0, x1 + 1)}

    def test_jalan_datar(self):
        solids = self._floor()
        p = srv._bfs_path(solids, (10, 25), (5, 25), (0, 20, 20, 30))
        self.assertIsNotNone(p)
        self.assertEqual((p[0][0], p[0][1]), (10, 25))
        self.assertEqual((p[-1][0], p[-1][1]), (5, 25))
        self.assertEqual({s[2] for s in p[1:]}, {"jalan"})

    def test_perlu_lompat_melewati_dinding_setinggi_avatar(self):
        solids = self._floor()
        solids.add((8, 25))  # satu blok menghalangi jalur datar
        p = srv._bfs_path(solids, (10, 25), (5, 25), (0, 20, 20, 30))
        self.assertIsNotNone(p, "harus bisa melewati rintangan 1 blok dengan lompat")
        self.assertIn("lompat", [s[2] for s in p])

    def test_dinding_terlalu_tinggi_tidak_ada_jalur(self):
        solids = self._floor()
        solids |= {(8, 25), (8, 24), (8, 23), (8, 22), (8, 21), (8, 20)}
        p = srv._bfs_path(solids, (10, 25), (5, 25), (0, 20, 20, 30))
        self.assertIsNone(p)

    def test_boleh_jatuh_ke_lantai_lebih_rendah(self):
        # lantai tinggi di kiri, lantai rendah di kanan
        solids = {(x, 26) for x in range(0, 11)} | {(x, 29) for x in range(11, 21)}
        p = srv._bfs_path(solids, (5, 25), (15, 28), (0, 20, 20, 30))
        self.assertIsNotNone(p)
        self.assertIn("jatuh", [s[2] for s in p])


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

    def test_tmp_tidak_hardcode_slash_tmp(self):
        import tempfile as _tf
        p = srv._tmp_png("unit")
        self.assertTrue(p.startswith(_tf.gettempdir()), p)
        self.assertNotIn("/tmp/", p.replace(_tf.gettempdir(), ""), p)

    def test_doctor_bentuk_keluaran(self):
        data = json.loads(srv.bridge_doctor(auto_fix=False))
        self.assertIn("langkah", data)
        self.assertIn("kesimpulan", data)
        self.assertTrue(any(s["cek"] == "port bridge host" for s in data["langkah"]))


class AttachedMode(unittest.TestCase):
    """Instance kedua harus melayani /status dan /enqueue lewat pemilik port."""

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
                self.fail("owner tidak siap")

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

            # klien palsu "game" menyapa owner + polling: hanya owner yang tahu
            # soal ini, jadi status versi attached harus mencerminkannya.
            urllib.request.urlopen(f"http://127.0.0.1:{port}/hello?sid=uji", timeout=3).read()
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
                f"status attached tidak membaca status owner: {st2}",
            )

            # /enqueue di owner: tanpa klien polling -> TIMEOUT dari owner
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
