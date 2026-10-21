# gt-mcp — MCP server untuk Growtopia + BINTERNAL (Bothax)

Memberi AI kendali penuh atas game lewat dua jalur: **ADB** (layar/sentuh/proses)
dan **bridge Lua** (memanggil 65 API executor langsung di dalam proses game).

Bukan bot jadi — ini lapisan kendali. Apa yang dilakukan AI ditentukan oleh
perintah Lua yang dikirimnya, memakai dokumentasi resmi Bothax yang dibundel di
`docs/`.

---

## Arsitektur

```
            ┌──────────────┐   stdio (JSON-RPC)   ┌────────────────────────┐
            │  AI / klien  │ ───────────────────► │  gt-mcp server.py      │
            └──────────────┘                      │  - 18 tool MCP         │
                                                  │  - HTTP :8770          │
                                                  └───────┬────────┬───────┘
                                                          │        │
                                        adb shell/exec-out│        │adb reverse tcp:8770
                                                          ▼        ▼
                                                  ┌──────────────────────────┐
                                                  │  Perangkat Android       │
                                                  │  Growtopia + libbot      │
                                                  │   └ bridge.lua (loop)    │
                                                  │      MakeRequest /poll   │
                                                  │      load(code) + pcall  │
                                                  │      POST /result        │
                                                  └──────────────────────────┘
```

Kenapa begini: `libbot.so` tidak bisa berdiri sendiri (tidak punya context GL,
tidak punya client jaringan Growtopia). Ia menumpang di proses game. Jadi satu-
satunya cara memakai API-nya adalah menjalankan Lua **di dalam** proses itu —
dan `bridge.lua` adalah kabelnya.

---

## Instalasi

```bash
cd gt-mcp
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python "mcp[cli]" lupa
```

`lupa` hanya untuk menjalankan uji Lua lokal; tidak dibutuhkan saat operasi.

## Menyiapkan perangkat (sekali per boot)

```bash
adb devices                         # pastikan perangkat "device"
adb reverse tcp:8770 tcp:8770       # kanal balik: 127.0.0.1:8770 di HP -> PC
```

Lalu, dari sesi MCP:

1. `install_bridge()` — push `bridge.lua` ke
   `/sdcard/Android/media/com.rtsoft.growtopia/scripts/` dan pasang `adb reverse`.
2. Di game, buka menu BINTERNAL → executor → jalankan `bridge.lua` sekali.
3. `bridge_status()` — harus `"polling": true`.

Setelah itu `lua_eval` dan `game_snapshot` hidup.

## Menghubungkan ke klien MCP

Hermes (`~/.hermes/config.yaml`):

```yaml
mcp_servers:
  growtopia:
    command: /home/adit/Documents/botex/gt-mcp/.venv/bin/python
    args: ["/home/adit/Documents/botex/gt-mcp/server.py"]
    env:
      PATH: "/home/adit/Android/Sdk/platform-tools:/usr/bin:/bin"
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "growtopia": {
      "command": "/home/adit/Documents/botex/gt-mcp/.venv/bin/python",
      "args": ["/home/adit/Documents/botex/gt-mcp/server.py"]
    }
  }
}
```

---

## Tool

| Tool | Fungsi |
|---|---|
| `device_info` | perangkat, status game, status bridge |
| `screenshot` | kembalikan gambar layar |
| `screenshot_crop` / `panel_crop` | potong area (mis. panel mod) agar terbaca jelas |
| `tap` / `swipe` / `key` / `type_text` | input layar |
| `launch_game` / `stop_game` | kendali proses |
| `logcat` | log terakhir, bisa difilter |
| `install_apk` | install/replace APK |
| `push_script` / `list_scripts` | kelola script di perangkat |
| `install_bridge` | setup kanal + `adb reverse` |
| `bridge_status` | apakah Lua sedang polling |
| `bridge_doctor` | diagnosa rantai ADB → reverse → bridge, perbaiki mapping yang hilang |
| `adb_reconnect` | pulihkan transport adb yang drop (khas nirkabel/emulator) |
| `lua_eval` | **eksekusi kode Lua di proses game, hasil dikembalikan** |
| `find_path` | jalur dari avatar ke objek terdekat (`target` = potongan nama item), BFS dengan jalan/turun/jatuh/lompat 1 petak + peta ASCII; `move=true` langsung memindahkan avatar |
| `go_to` | pindahkan avatar ke tile (`CheckPath` → `FindPath` → verifikasi posisi) |
| `collect_objects` | pungut objek jatuh dengan paket `type=11` (`value` = **`oid` objek**, `px/py` = piksel objek); `item_id=0` = semua, `radius` dalam petak, avatar tidak bergerak |
| `list_objects` | daftar objek/drop aktif: `oid`, item id, nama, tile |
| `drop_item` | jatuhkan item ke tanah satu paket (`item_drop\|<id>\|` + `item_count`); `amount=0` = seluruh stack (drop all) |
| `game_snapshot` | pemain, dunia, inventori, jumlah objek; `pos` (pixel) + `pos_tile` (`pos/32`) + petak di bawah kaki |
| `traffic_start` / `traffic_dump` / `traffic_stats` / `traffic_stop` / `traffic_clear` | tangkap lalu lintas paket dalam game |
| `debug_log` | log internal bridge: tiap perintah, durasi, error, output `LogToConsole` |
| `debug_state` | diagnostik gabungan: pid, fokus, bridge, error logcat, ekor log bridge |
| `api_list` / `api_doc` | dokumentasi 43 fungsi + 16 struktur |

`lua_eval` adalah inti: semua yang bisa dilakukan executor bisa dilakukan AI.

```python
lua_eval("return GetLocal().name")
lua_eval("local w=GetWorld(); return {w.name, w.width, w.height}")
lua_eval("SetTileFlags(10, 20, {dropseed=true})")
lua_eval("AddHook('OnVariant', 'ai', function(v) LogToConsole(v[0]) end)")
```

---

## Debug

Empat lapis, dari yang paling dalam:

| Lapis | Tool | Isi |
|---|---|---|
| Lalu lintas paket | `traffic_start` / `traffic_dump` / `traffic_stats` / `traffic_stop` / `traffic_clear` | setiap `OnSendPacket`, `OnSendPacketRaw`, `OnVariant`, `OnProcessTankUpdate` — tipe, koordinat, value, netid, extrasize |
| Dalam game | `debug_log(n)` | buffer `_BRIDGE_LOG` di `bridge.lua`: setiap perintah masuk, durasi ms, potongan hasil, error, dan **semua output `LogToConsole` script lain** (maks 300 baris) |
| Proses | `debug_state()` | pid, activity fokus, status polling bridge, 5 error `FATAL`/`AndroidRuntime` terakhir |
| Sistem | `logcat(n, grep)` | logcat Android mentah |

Contoh:

```python
traffic_start(400)        # pasang 4 hook, paket tetap mengalir
# ... main / join world / buka dialog ...
traffic_dump(30)          # lihat 30 kejadian terakhir
traffic_stats()           # {total=..., per_jenis={SENDRAW=..., VARIANT=...}}
traffic_stop()
```

Bentuk keluaran:

```
0 SENDRAW            type=10  x=12.50    y=34.25    value=1796   netid=7   extra=0
0 SENDPACKET         type=3 len=19 action|join_request
0 VARIANT            OnConsoleMessage netid=99 delay=0
0 TANKUPDATE         type=0   x=0.00     y=0.00     value=nil    netid=7   extra=nil
```

Catatan penting: callback hook **tidak** mengembalikan `true`, jadi capturer hanya
membaca dan tidak memblokir/mengubah paket apa pun.

### Soal debug di dalam UI (RML/ImGui)

Halaman debug milik mod — baris `Hook[%s]: %d`, `MEM usage: %f KB`,
`Thread running: %llu` — **tidak** bisa dibaca lewat API. Teks itu digambar
langsung oleh ImGui di dalam menu, tidak pernah dikirim ke konsol, tidak ditulis
ke logcat, dan tidak ada fungsi Lua untuk membacanya. Tiga cara yang tersedia:

1. `screenshot()` — mengembalikan gambarnya, lalu model membacanya secara visual.
2. `tap(x, y)` — klik tab/pages debug di panel (koordinat didapat dari screenshot).
3. Toggle `RML::Log::Message hook` di tab Setting juga hanya bisa diklik lewat
   `tap()`, karena tidak ada API untuk mengubah setting mod dari Lua.

Pesan konsol RML yang **memang** lewat `LogToConsole` tetap tertangkap oleh
`debug_log`, karena `bridge.lua` membungkus fungsi itu.


### Menggerakkan avatar dan bicara (terverifikasi)

Gerak **tidak** bisa lewat paket. `SendPacketRaw(false, {type=0, x=.., y=..})` diterima
tanpa error tapi tidak berefek: klien mengirim ulang posisinya sendiri tiap ~200 ms,
jadi server mengabaikan posisi buatan kita. Tap ke tanah juga tidak menggerakkan.
Yang bekerja adalah **press-and-hold tombol panah bawaan**:

```
panah kanan : x=289 y=606   panah kiri : x=117 y=606
input swipe x y x y <ms>    ->  kecepatan ≈ 500 px/s ≈ 15,6 petak/s
1 petak = 32 px
```

Contoh presisi yang terukur: hold 220 ms berulang sampai target → `+5,03` petak lalu
`−10,22` petak. Selalu verifikasi dengan `GetLocal().pos` setiap langkah; jangan
mengandalkan durasi.

Bicara dan emote lewat paket teks (newline harus karakter asli, bukan `\n` literal):

```lua
local nl = string.char(10)
pcall(SendPacket, 2, 'action|input' .. nl .. 'text|MCP Keren')   -- chat
pcall(SendPacket, 2, 'action|input' .. nl .. 'text|/dab')        -- emote
pcall(SendPacket, 2, 'action|wrench' .. nl .. '|netid|' .. tostring(GetLocal().netid) .. nl)
```

Bentuk umum paket aksi: `action|<nama>\n|<field>|<nilai>\n`, newline = `string.char(10)`
(bukan `\n` literal — Lua gagal kompilasi). `action|wrench` membuka dialog profil dan
server membalas `OnDialogRequest`; dialog profil sendiri berisi `Level`, `XP`, `Card
Battle Level`, dan `Achievements` — satu-satunya cara membaca level, karena API tidak
mengeksposnya (`GetLocal()`/`GetPlayerInfo()` tidak punya field level).

Bukti keberhasilan tidak lewat screenshot, tapi echo server di capturer:
`OnTalkBubble` untuk chat, `OnAction` untuk emote (`netid=5`).

### Drop item (terverifikasi)

Drop berjalan dua langkah, dan langkah kedua yang benar-benar mengeksekusi:

```
picu    : action|drop\n|itemID|15\n|amount|1\n
          -> klien membuka dialog "Drop <nama item> (you have N)" + kotak angka
konfirmasi: action|dialog_return\ndialog_name|drop\nitem_drop|15|\nitem_count|1\n
          -> stok 15 turun 1->0, sprite item muncul di tanah dekat avatar
```

Perhatikan `item_drop|15|` punya `|` tambahan sebelum newline. Untuk otomasi tanpa
UI, cukup kirim paket `dialog_return` itu langsung; dialog konfirmasi tidak wajib —
sudah diuji: stok 1 -> 0 tanpa dialog muncul.

### Ambil item dari tanah (pickup)

Tidak ada paket pickup. Server memberi item berdasarkan posisi: cukup berjalan
melewati tile tempat item berada, lalu `GetItemCount(id)` berubah. Yang terlihat di
capturer hanya `SENDRAW type=0` (posisi).

Item tidak selalu jatuh tepat di tile avatar — drop dari tile 24 mendarat di sekitar
tile 25-26. Jadi sapu beberapa petak kiri-kanan, bukan satu langkah, dan periksa
`GetItemCount` setiap kali.

Catatan penting: **paket yang dikirim dari Lua lewat `SendPacket` tidak terlihat oleh
hook `OnSendPacket` kita** (buffer capturer tetap kosong). Capturer hanya merekam
paket asli klien; jangan pakai capturer untuk memverifikasi injeksi sendiri —
verifikasi lewat perubahan state (`GetItemCount`, `GetLocal`, `OnDialogRequest`).
Dialog apa pun yang sedang terbuka menelan aksi lain — tutup dulu (Back) sebelum
mengirim perintah berikutnya, dan cek `OnDialogRequest` di capturer untuk tahu
apakah masih ada dialog aktif.

Format paket yang terlihat saat bermain manual:

```
SENDRAW    type=0  x=<px> y=<px>          posisi (tiap ~200 ms saat berjalan)
SENDPACKET type=2  action|input\ntext|<pesan>
SENDPACKET type=2  action|enter_game\n
SENDRAW    type=18 netid=<id>             aksi terhadap entitas
SENDRAW    type=24 / type=26              handshake saat masuk
```

### Otomasi UI: apa yang bisa dan tidak

Panel BINTERNAL adalah **ImGui**, bukan RML. RML adalah UI milik game
(`assets/interface/*.rml`); menu mod digambar Dear ImGui langsung ke konteks GL
game. Konsekuensinya:

- ImGui tidak punya DOM, tidak punya accessibility node, dan tidak menyimpan label
  widget — yang disimpan hanya hash ID. Jadi "enumerasi checkbox/slider/field"
  secara terprogram **tidak tersedia**.
- Tidak ada fungsi di 65 API untuk menyalakan fitur panel. Fitur digerakkan lewat
  `triggerBoolean` / `triggerInt` / `triggerClick` di sisi Java (JNI), yang tidak
  bisa dipanggil dari Lua.

Percobaan yang sudah dilakukan: detektor panel berbasis warna (densitas piksel
gelap + bingkai sian) untuk mendapat bounding box otomatis. Hasilnya tidak stabil
— mengembalikan 110x66 untuk panel yang sebenarnya ~960x900 — jadi kode itu
**dibuang**, tidak dikirim sebagai fitur.

Pola yang bekerja, dan sudah terbukti di sesi ini (tap pada tab `Setting`
berhasil memakai koordinat dari pembacaan gambar):

```
panel_crop()            -> gambar panel yang tajam (tool baru)
   model membaca        -> "checkbox RML::Log::Message hook ada di (x, y)"
tap(x, y)               -> klik
swipe(x1,y1,x2,y2,ms)   -> geser slider
type_text("...")        -> isi field
```

`panel_crop` memotong area kiri-atas layar; crop 1100x950 terbukti membuat
slider, checkbox, dan field terbaca jelas (diuji pada tangkapan layar nyata).

Kalau suatu saat ada akses root: `ImGuiContext` menyimpan daftar window beserta
rect tiap item, jadi posisi widget bisa diekstrak presisi lewat Frida. Labelnya
tetap tidak ada (hanya hash), jadi pemetaan nama tetap butuh pembacaan gambar.

Hentikan bridge dari dalam game: `lua_eval("_BRIDGE_STOP()")`.

---

## Protokol bridge

Plain text, bukan JSON, supaya sisi Lua tidak butuh parser:

```
GET  /hello?sid=...   ->  "ok"          daftarkan instance (hanya instance terbaru dilayani)
GET  /poll?sid=...    ->  "<cmd_id>|<kode lua>"   atau "none"
GET  /ack?sid=&id=    ->  "ok"          klien konfirmasi perintah diterima & diparse
POST /result          ->  "<cmd_id>|<ok|err>|<teks hasil>"
GET  /result?id=&st=&d=   jalur cadangan bila POST ditolak
GET  /diag?msg=...    ->  "ok"          laporan diagnostik dari dalam game
GET  /health          ->  "ok"          penanda "port ini milik gt-mcp"
GET  /status          ->  JSON          status antrean (dipakai mode attached)
POST /enqueue         ->  teks hasil    {"code":...,"timeout":...} dari proses lain
```

`/status` dan `/enqueue` ada supaya proses MCP kedua (port 8770 sudah dipegang
instance lain) tetap berfungsi: dia masuk mode **attached**, membaca status dari
pemilik port, dan meneruskan perintah Lua ke sana alih-alih mati saat bind.

### Jebakan `MakeRequest` di build ini (penting)

`MakeRequest` **tidak** mengembalikan status HTTP. Respons sukses berbentuk:

```lua
{ status = 0, error = false, content = "..." }
```

Artinya:

- jangan cek `res.status == 200` — nilainya selalu `0`, sehingga setiap respons sah
  dianggap gagal dan bridge berhenti diam-diam
- sukses ditentukan oleh `res.error == false` dan `res.content ~= nil`
- `content` bisa berupa string; `"none"` adalah balasan sah (tidak ada perintah)
- `io` dan `os` tidak ada di sandbox, jadi jangan andalkan tulis file

Gejala kalau syarat ini salah: game mencetak "server tidak terjangkau" berkali-kali
padahal request-nya sampai ke server. Gunakan `/diag` untuk melihat bentuk respons
aslinya sebelum menebak.

### Instance ganda

Setiap `Execute` meninggalkan thread yang tetap polling. `bridge.lua` mengirim
`/hello?sid=<acak>` saat mulai; server hanya memberi perintah ke `sid` terbaru dan
menjawab `none` untuk yang lain. Tanpa ini, perintah bisa "dicuri" instance zombie
yang sudah tidak mengeksekusi apa pun.

Giliran itu **kedaluwarsa** (`ACTIVE_TTL`, 20 detik): `_Bridge.claim()` mengambil alih
sid kalau pemegang sebelumnya sudah sunyi lebih dari TTL. Tanpa batas waktu, sid basi
(game di-restart, script dijalankan ulang) membuat instance baru dijawab `none`
selamanya — gejalanya `polling: false`, log bridge tanpa baris `POLL`, tapi `/diag`
dari client tetap masuk.

Pengiriman ulang (`reap`) hanya terjadi kalau instance yang menerima perintah
sudah **digantikan** sid lain — bukan sekadar karena belum ada hasil. Aturan lama
(6 detik tanpa hasil → kirim ulang) mengeksekusi perintah dua kali setiap kali Lua
butuh lebih dari 6 detik, mis. `Sleep(8000)`. Perintah yang pemanggilnya sudah
menyerah (TIMEOUT) juga dibuang dari antrean, jadi tidak dieksekusi belakangan
saat bridge baru muncul.

Hasil diserialisasi oleh `bridge.lua` (`enc()`): table, string, number, boolean,
dengan batas kedalaman 5 dan 120 entri per tabel, plus penanda `<cycle>`.

---

## Jebakan: script jalan tapi server tidak menerima apa pun

Gejala: konsol mod menampilkan `aktif, menunggu perintah dari MCP` lalu diam,
`bridge_status` tetap `polling: false`, dan log bridge (`bridge_http.log`, lihat
`log_path` di `bridge_status`) kosong — padahal
`adb reverse` aktif dan `curl http://127.0.0.1:8770/health` dari dalam container
menjawab `ok`.

Penyebab paling sering: **daftar API di setting script executor belum dicentang**
("package api list" pada BINTERNAL). Tanpa itu `MakeRequest`/`GetLocal` tidak
tersedia, jadi setiap request gagal sebelum keluar dari proses game — server tidak
pernah melihat koneksi apa pun, dan ini tidak bisa dibedakan dari "script tidak
dijalankan" tanpa penanda.

Dua penyebab lain yang gejalanya mirip, dan cara membedakannya:

| gejala di log server | penyebab | perbaikan |
|---|---|---|
| tidak ada baris `POLL` sama sekali, tapi `/diag` masuk | `adb reverse` hilang setelah transport putus | `adb reverse tcp:8770 tcp:8770` (atau `bridge_doctor(auto_fix=True)`) |
| `/diag` masuk berulang dengan `peek=none`, `polling: false`, nol baris `POLL` | sid basi masih memegang giliran (`BRIDGE.active`) | versi ini sudah memakai `ACTIVE_TTL` 20 s; kalau masih terjadi, restart server |

Cara memastikan: centang daftar API itu, Execute ulang `bridge.lua`, lalu lihat
konsol. Baris yang benar:

```
PROBE /health: status=0 error=false content(string)=ok
```

Kalau muncul `status=0 error=false` maka jalur HTTP sehat (ingat: build ini selalu
melaporkan `status=0`, sukses ditentukan `error=false` + `content` terisi). Kalau
masih gagal, baris `poll GAGAL: ...` akan menyebut alasannya.

---

## Perilaku tool (kontrak)

- **Tidak ada tool yang meledak.** Semua tool dibungkus `_safe`: kegagalan adb
  (device offline, timeout) kembali sebagai teks `ERROR: ...`, bukan traceback
  `UnexpectedToolError` yang menyembunyikan penyebab.
- **`adb` timeout 20 detik** (dulu 60): device nirkabel yang mati bisa membuat
  `adb shell` menggantung semenit lebih, dan itu membekukan seluruh tool call.
- **`type_text` hanya ASCII.** Spasi dikirim sebagai `%s`, seluruh payload
  dikutip untuk sh perangkat, jadi `& ; | $ ( ) * ' "` aman dan apostrof tidak
  lagi dibuang. Teks non-ASCII ditolak dengan pesan jelas — `input text` bawaan
  Android memang tidak mendukungnya.
- **Operasi tulis diverifikasi.** `install_bridge` memeriksa `adb reverse --list`
  (bukan hanya returncode), `launch_game`/`stop_game` melaporkan kegagalan dan
  memastikan proses benar-benar hilang, `push_script`/`install_apk` menolak path
  yang tidak ada.

---

## Tanpa root, OS lain, dan klien lain

### Root tidak diperlukan

Jalur ADB berjalan sebagai user `shell` (uid 2000) dan itu cukup untuk `input
tap/swipe/text`, `screencap`, `am start`, `logcat`, `install`, `push`, dan
`adb reverse`. Di setup tes ini (`adb shell id` → `uid=2000(shell)`, sementara
`adb root` menjawab "not available in Waydroid") semua tool ADB berfungsi tanpa
root.

Yang butuh lebih dari ADB hanya jalur Lua, dan syaratnya bukan root melainkan
**klien Growtopia yang punya executor** (APK yang dipatch) plus daftar API di
setting executor dicentang. Di perangkat nyata itu berarti memasang klien mod,
bukan rooting; di emulator cukup emulator yang bisa memasang APK tersebut.

### USB atau nirkabel

Dua-duanya. USB: colok, `adb devices`, lalu `install_bridge()`. Nirkabel:
`adb connect <ip>:5555` atau `adb_reconnect("<ip>:5555")`. `adb reverse` bekerja
sama di keduanya, tapi mapping-nya **hilang setiap transport adb putus** —
`bridge_doctor()` memeriksa dan memasangnya ulang otomatis.

### OS

Linux, macOS, Windows. Kebutuhan: Python 3.10+, `adb`, dan paket `mcp`. Tidak ada
dependensi Linux-only: `pngio.py` murni `struct`+`zlib`, path sementara memakai
`tempfile.gettempdir()`, dan `adb` dicari lewat `PATH` → `ANDROID_SDK_ROOT`/
`ANDROID_HOME` → lokasi bawaan tiap OS (`platform-tools/adb.exe` di Windows,
`~/Library/Android/sdk/...` di macOS).

### Klien MCP lain

Server ini MCP stdio biasa, jadi bisa dipakai Claude Code, Codex CLI, opencode,
Gemini CLI, Cursor, Zed, Cline, Continue, dan Hermes sendiri. Potongan config per
klien ada di [`docs/clients.md`](docs/clients.md).

---

## Status verifikasi

| Bagian | Status | Bukti |
|---|---|---|
| `bridge.lua` sintaks | LULUS | `load()` di Lua 5.4 (lupa) |
| `bridge.lua` fungsional | LULUS | `test_bridge_lua.py` — stub `MakeRequest`, satu perintah, hasil `{name="TestUser",...}` |
| buffer `_BRIDGE_LOG` | LULUS | `test_bridge_lua.py` — 2 entri: start bridge + `0 ms, 88 char -> {...}` |
| Protokol dua arah | LULUS | `test_server.py` — submit → poll → POST → hasil diterima |
| Traffic capture | LULUS | `test_bridge_lua.py` — 4 hook palsu, dump 4 kejadian, stats, stop |
| MCP stdio + list tools | LULUS | 27 tool terdaftar lewat `ClientSession` |
| Escaping `type_text` | LULUS | `tests_gt.py` — metakarakter sh, apostrof, non-ASCII |
| Reap tanpa duplikasi | LULUS | `tests_gt.py` — perintah 200 ms tak dikirim ulang; requeue saat sid berganti |
| Perintah basi dibuang | LULUS | `tests_gt.py` — submit TIMEOUT → `next_cmd()` kosong |
| Mode attached | LULUS | `tests_gt.py` — instance kedua baca `/status` owner, `/enqueue` diteruskan |
| Unescape hasil Lua | LULUS | `tests_gt.py` — `\\`, `\n`, `\"` bolak-balik |
| Tool gagal tanpa crash | LULUS | `logcat` tanpa device → `ERROR: RuntimeError: adb logcat -d timeout 20s` |
| `bridge_doctor` | LULUS | live: menemukan `adb reverse` hilang setelah transport putus, memasangnya ulang, polling pulih |
| `find_path` | LULUS | live: `door` → Main Door (69,24), 3 langkah, peta ASCII |
| `go_to` / `find_path(move)` | LULUS | live: `go_to(76,24)` memindah 83,24→76,24; `find_path(move=true)` memindah 76,24→69,24 (pos akhir diverifikasi) |
| `collect_objects` | LULUS | live: Water Essence dijatuhkan (`oid=1199`, tile 70,24) → `dikirim=1`, `objek_sisa=0`, inventori 5026 `+1`, avatar tetap 71,24 |
| `list_objects` | LULUS | live: `oid=1199 id=5026 nama=Water Essence tile=70,24`, lalu `jumlah=0` setelah dipungut |
| `_Bridge.claim()` TTL | LULUS | `tests_gt.py` — sid basi diambil alih setelah `ACTIVE_TTL`; sid yang masih mem-poll tidak diserobot |
| `drop_item` (drop all) | LULUS | live: 7 Water Essence → `inv_akhir=0`, `objek=1`, `total_amount=7` (satu objek membawa 7 unit) |
| Siklus drop→collect | LULUS | live: `drop_item(5026)` → `list_objects` 1 objek `oid=1204` → `collect_objects(5026)` → `inventori_berubah {5026:+7}`, `objek_sisa=0` |
| Template Lua path | LULUS | `tests_gt.py` — dikompilasi di Lua 5.5 (lupa) sebelum dikirim ke game |
| Portabilitas path | LULUS | `tests_gt.py` — `_find_adb()` dari PATH, `_tmp_png()` tidak pakai `/tmp` hardcode |
| Gambar via MCP | LULUS | `screenshot` → content `image` (PNG) lewat `ClientSession` |
| Tool ADB | teruji sebagian | `adb install/start/logcat` dipakai lebih awal di sesi ini; saat uji terakhir perangkat sudah terputus |
| Eksekusi di dalam game | LULUS | live sepanjang sesi: `lua_eval` mengembalikan `pos=2293,770`, world `GTMCP`, `objs=0`; loop farm 245 pot; `collect_objects` memungut objek nyata |

## Batasan nyata

- **Butuh executor.** Kalau menu masih `Locked!` (belum ada key), `bridge.lua`
  tidak bisa dijalankan dan seluruh jalur Lua mati. Jalur ADB tetap jalan.
- **USB harus tetap tersambung.** `adb reverse` hilang saat kabel dicabut atau
  adb server restart; jalankan ulang `install_bridge()`.
- **Game harus di foreground** agar tidak dibekukan Android. Kalau layar mati,
  Android 16 bisa menangguhkan proses — bridge akan timeout.
- **Satu perangkat, satu akun aktif.** Tidak ada isolasi multi-akun dalam satu proses.
- **Risiko ban.** Automasi + mod pada server resmi mudah dikenali. Ini alat, bukan
  pelindung. Tidak ada fitur anti-deteksi di sini dan tidak akan ditambahkan.
- **`level` tidak tersedia.** `GetLocal()`/`GetPlayer()` hanya memuat
  `name, netid, userid, country, pos, clothing, invisible, isleft, mstate, smstate`.
  `GetPlayerInfo()` hanya memberi `gems`. Tidak ada fungsi `Level`/`Exp` di 89 global
  yang diekspos build ini. `clothing` = avatar (9 slot, isi item id).
