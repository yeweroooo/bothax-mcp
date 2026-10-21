# bothax-mcp

MCP server untuk mengendalikan Growtopia di Android. Dua jalur kontrol: **ADB** untuk
sentuhan, screenshot, file, dan proses; **bridge Lua** untuk memanggil API Bothax
(BINTERNAL) yang hanya hidup di dalam proses game. Ada 34 tool.

Isi repo: `server.py` (MCP + HTTP), `bridge.lua` (skrip di dalam game), tiga berkas tes,
`experiments/` berisi skrip percobaan beserta hasilnya, dan `docs/` berisi dokumentasi API
Bothax plus catatan klien.

## Kenapa harus lewat Lua

API Bothax terikat ke proses game: tidak ada socket, CLI, atau library terpisah yang bisa
memanggil `GetLocal`, `GetTiles`, `SendPacketRaw`, atau `FindPath`. Satu-satunya jalan
adalah menjalankan Lua di dalam proses itu, lalu menyambungkannya ke PC:

    bridge.lua  --HTTP-->  127.0.0.1:8770  --adb reverse-->  server.py di PC

`adb reverse tcp:8770 tcp:8770` meneruskan port 8770 di perangkat ke port 8770 di PC.
Tanpa mapping itu, `MakeRequest` dari dalam game tidak sampai ke mana pun.

## Instalasi

    python3 -m venv .venv
    .venv/bin/pip install "mcp[cli]"
    .venv/bin/pip install lupa        # hanya untuk tes template Lua

Butuh `adb` di PATH (`ANDROID_HOME`/`ANDROID_SDK_ROOT` juga dibaca), Python 3.10 ke atas,
dan perangkat dengan USB debugging atau adb nirkabel.

## Menyiapkan perangkat (sekali per boot)

1. `adb devices` atau `adb connect <ip>:5555` sampai perangkat tampil sebagai `device`.
2. Jalankan server dari klien MCP, atau `python server.py --http-only` untuk kontrol
   manual lewat `curl`.
3. `install_bridge()`: push `bridge.lua` ke
   `/sdcard/Android/media/com.rtsoft.growtopia/scripts/` dan pasang `adb reverse`.
4. Di game, buka executor BINTERNAL, centang daftar API, jalankan `bridge.lua`.
5. `bridge_status()` harus menjawab `"polling": true`.

Kalau ada yang gagal, `bridge_doctor()` memeriksa adb, reverse, dan polling satu per satu,
lalu memperbaiki mapping yang hilang.

## Menghubungkan klien MCP

Server memakai stdio standar. Contoh JSON:

```json
{
  "mcpServers": {
    "bothax-mcp": {
      "command": "/path/ke/bothax-mcp/.venv/bin/python",
      "args": ["/path/ke/bothax-mcp/server.py"]
    }
  }
}
```

Hermes memakai kunci `mcp_servers` dengan bentuk yang sama. Potongan config untuk klien
lain ada di [docs/clients.md](docs/clients.md).

Kalau port 8770 sudah dipegang proses `--http-only`, server masuk mode `attached`: perintah
Lua diteruskan ke proses pemilik port, dan tool ADB tetap jalan di proses ini.

## Tool

| Tool | Kegunaan |
|---|---|
| `device_info` | model, versi Android, status game, status bridge |
| `screenshot` / `screenshot_crop` / `panel_crop` | tangkap layar, potong area, perbesar panel mod |
| `tap` / `swipe` / `key` / `type_text` | input layar dan teks ASCII |
| `launch_game` / `stop_game` | jalankan atau hentikan game, lalu verifikasi prosesnya |
| `logcat` | log perangkat, opsional difilter |
| `install_apk` | install APK dan laporkan kegagalan sebenarnya |
| `push_script` / `list_scripts` | kelola skrip di folder game |
| `install_bridge` | push `bridge.lua` dan pasang `adb reverse` |
| `bridge_status` | apakah skrip di game sedang polling |
| `bridge_doctor` / `adb_reconnect` | diagnosa dan pemulihan transport |
| `lua_eval` | eksekusi Lua di proses game, hasil dikembalikan |
| `game_snapshot` | pemain, dunia, inventori, jumlah objek, posisi petak |
| `go_to` | pindah avatar ke tile (`CheckPath`, `FindPath`, verifikasi posisi) |
| `find_path` | jalur BFS ke objek terdekat plus peta ASCII; `move=true` ikut memindah avatar |
| `list_objects` | objek di tanah: oid, item id, nama, tile |
| `collect_objects` | pungut objek dengan paket `type=11`, bisa difilter item dan radius |
| `drop_item` | jatuhkan item, `amount=0` untuk seluruh stack |
| `traffic_start` / `traffic_dump` / `traffic_stats` / `traffic_stop` / `traffic_clear` | tangkap paket di dalam game |
| `debug_log` | log internal bridge: perintah, hasil, error, output `LogToConsole` |
| `debug_state` | ringkasan diagnostik gabungan |
| `api_list` / `api_doc` | dokumentasi fungsi dan struktur Bothax |

`lua_eval` adalah pintu utama; apa pun yang bisa dilakukan executor bisa dikirim dari sini.

```python
lua_eval("return GetLocal().name")
lua_eval("local w=GetWorld(); return {w.name, w.width, w.height}")
lua_eval("return #GetTiles()")
```

## Paket yang sudah terverifikasi

    place   {type=3,  state=0, value=<item id>, px=x, py=y, x=pos.x, y=pos.y}
    break   {type=3,  state=0, value=18, px=x, py=y}          -- 18 = Fist
    collect {type=11, state=0, value=<oid objek>, px=obj.pos.x, py=obj.pos.y}
    drop    "action|dialog_return\ndialog_name|drop\nitem_drop|<id>|\nitem_count|<n>\n"

- `collect` memakai **oid objek**, bukan item id. Satu objek bisa membawa beberapa unit,
  jadi jumlah barang tidak sama dengan jumlah objek. Avatar tidak perlu bergerak.
- Satu paket `drop` sudah cukup. Pipa penutup setelah id (`item_drop|5026|`) wajib ada.
- `break` diulang sampai `GetTile(x,y).fg` berubah. Jumlah hit sama dengan
  `GetItemInfo(id).breakhit`.

## Protokol bridge

Plain text, bukan JSON, supaya sisi Lua tidak butuh parser.

| Endpoint | Balasan |
|---|---|
| `/health` | `ok`, penanda port ini milik server |
| `/poll?sid=` | `<id>|<kode lua>` atau `none` |
| `/result` | hasil dari game (POST), ada jalur cadangan lewat GET |
| `/ack` | konfirmasi perintah diterima |
| `/diag?msg=` | pesan debug dari dalam game, ikut masuk log |
| `/hello?sid=` | pendaftaran instance |
| `/status` / `/enqueue` | dipakai mode attached |
| `/call?tool=&args=` | kontrol manual tanpa klien MCP |

Bentuk balasan `MakeRequest` di build ini: `status = 0` (bukan 200) dan `error = false`
saat sukses. Patokan yang benar adalah `error` dan `content`, bukan status. Hasil dari Lua
diserialisasi `enc()` (kedalaman 5, 120 entri per tabel), jadi string kembali ter-escape
dan server membuka escape itu sebelum membaca isinya.

### Instance ganda

Setiap `Execute` meninggalkan thread yang tetap polling. `bridge.lua` mengirim
`/hello?sid=<acak>` saat mulai. Server hanya melayani satu sid, tapi giliran itu kedaluwarsa
(`ACTIVE_TTL` 20 detik di `_Bridge.claim()`): kalau pemegangnya sudah sunyi, instance baru
mengambil alih. Tanpa batas waktu, sid basi membuat instance baru dijawab `none` selamanya.

Pengiriman ulang (`reap`) hanya terjadi kalau instance penerima sudah digantikan sid lain,
bukan karena hasilnya lambat. Perintah yang pemanggilnya sudah menyerah (TIMEOUT) dibuang
dari antrean, jadi tidak dieksekusi belakangan.

## Gerak, chat, dan level

Gerak tidak bisa lewat paket. `SendPacketRaw(false, {type=0, x=.., y=..})` diterima tanpa
error tapi tidak berefek karena klien mengirim ulang posisinya sendiri tiap ~200 ms. Yang
bekerja: `FindPath` (jalur cepat bawaan game) lewat tool `go_to`, atau press-and-hold
tombol panah lewat `swipe`.

    panah kanan x=289 y=606, panah kiri x=117 y=606
    swipe x y x y <ms>  ->  sekitar 500 px/s, 1 petak = 32 px

Chat dan emote lewat paket teks, newline harus karakter asli (`string.char(10)`):

```lua
local nl = string.char(10)
pcall(SendPacket, 2, 'action|input' .. nl .. 'text|halo')
pcall(SendPacket, 2, 'action|input' .. nl .. 'text|/dab')
```

`level` tidak diekspos API. `GetLocal()` hanya memuat `name, netid, userid, country, pos,
clothing, invisible, isleft, mstate, smstate`, dan `GetPlayerInfo()` hanya `gems`. Angka
level hanya muncul di dialog profil (`action|wrench`).

## Jebakan yang sudah memakan waktu

1. **Daftar API belum dicentang** di setting executor. Gejalanya konsol mod diam di
   `aktif, menunggu perintah` dan server tidak melihat koneksi apa pun.
2. **`adb reverse` hilang** setiap transport adb putus. Gejalanya nol baris `POLL` di log
   server, sementara `/diag` dari perangkat tetap masuk. Perbaiki dengan
   `adb reverse tcp:8770 tcp:8770` atau `bridge_doctor(auto_fix=True)`.
3. **Sid basi memegang giliran.** Gejalanya `polling: false`, `/diag` masuk berulang dengan
   `peek=none`, dan log tanpa baris `POLL`. Sekarang ditangani `ACTIVE_TTL`.
4. **Label hook harus angka.** `AddHook('OnSendPacketRaw', 'label_string', cb)` tidak
   meregistrasi apa pun, dan percobaan label string bisa mematikan hook yang sudah ada
   sampai game dijalankan ulang.
5. **Template Lua yang memakai `.format()`** butuh `{{}}` untuk kurung literal. Template
   yang tidak di-`.format()` justru tidak boleh punya `{{}}`, karena Lua membacanya sebagai
   tabel berisi tabel kosong.
6. **Hook tidak melihat paket yang kita kirim sendiri.** `SendPacket`/`SendPacketRaw` dari
   Lua tidak muncul di capturer. Verifikasi injeksi lewat perubahan state
   (`GetTile`, `GetInventory`, `GetObjectList`), bukan lewat capturer.

## Tes

    .venv/bin/python -m unittest tests_gt.py     # 33 tes, tanpa perangkat
    .venv/bin/python test_bridge_lua.py          # harness bridge.lua dengan stub MakeRequest
    .venv/bin/python test_server.py              # smoke test stdio (butuh perangkat)

`tests_gt.py` menguji reap tanpa duplikasi, pembuangan perintah basi, mode attached,
escaping `type_text`, BFS pathfinding, pengambilalihan sid, dan template Lua
(`collect_objects`, `drop_item`, `list_objects`) yang dikompilasi dengan `lupa` sebelum
dikirim ke game.

## Struktur

    server.py           MCP server + kontrol HTTP
    bridge.lua          skrip in-game: polling, eksekusi, serialisasi, capturer
    tests_gt.py         tes regresi tanpa perangkat
    test_bridge_lua.py  harness bridge.lua
    test_server.py      smoke test stdio
    pngio.py            pemotong PNG untuk screenshot_crop
    experiments/        skrip percobaan, tiap berkas menyebut hasilnya
    docs/               dokumentasi API Bothax dan catatan klien

## Batasan

- **Butuh executor.** Kalau menu BINTERNAL masih terkunci, `bridge.lua` tidak bisa jalan
  dan seluruh jalur Lua mati. Jalur ADB tetap tersedia.
- **Game harus di foreground.** Proses latar dibekukan Android, polling ikut berhenti.
- **ADB harus tetap tersambung.** Nirkabel lebih rawan putus daripada USB, dan setiap
  putus menghapus `adb reverse`.
- **Satu perangkat, satu instance aktif.** Tidak ada isolasi multi-akun.
- **Risiko akun milik pemakai.** Otomasi di server resmi bisa berujung sanksi. Alat ini
  tidak memuat penghindaran deteksi, dan tidak dimaksudkan untuk itu.
