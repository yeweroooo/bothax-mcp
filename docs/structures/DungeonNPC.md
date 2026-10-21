# DungeonNPC (x:int, y:int, state:int, flags:int, flags2:int)

Deskripsi singkat
- Data NPC khusus area/dungeon. Berisi status dan flag tambahan.

Penjelasan
- Tidak selalu tersedia di semua world. Gunakan API yang relevan untuk mendapatkan daftar/objek DungeonNPC jika didukung oleh executor Anda.

Bidang
- `x: int` — Koordinat tile X.
- `y: int` — Koordinat tile Y.
- `state: int` — Status NPC saat ini.
- `flags: int` — Bitmask status.
- `flags2: int` — Bitmask tambahan.

Contoh penggunaan (Lua)
```lua
-- Membaca state NPC dungeon di tile (x, y) jika tersedia via API terkait
-- (Tergantung fungsi yang memaparkan DungeonNPC dalam executor Anda)
```
