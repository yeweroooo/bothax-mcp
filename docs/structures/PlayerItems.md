# PlayerItems (gems:int, backpack:table)

Deskripsi singkat
- Data item terkait pemain: jumlah gems dan konfigurasi backpack.

Penjelasan
- Cocok untuk membaca saldo gems dan info ransel (ukuran, slot terpilih) tanpa perlu parsing paket manual.

Bidang
- `gems: int` — Saldo gems pemain.
- `backpack: table` — Info ransel:
  - `priority: int[]` — Urutan prioritas slot.
  - `size: int` — Ukuran ransel maksimal.
  - `selected: int` — Slot/item terpilih.

Contoh penggunaan (Lua)
```lua
local p = GetPlayerInfo()
LogToConsole(('Gems: %d, Backpack size: %d')
  :format(p.gems, p.backpack.size))
```

Terkait
- [GetPlayerInfo](../functions/GetPlayerInfo.md)
- [GetPlayerItems](../functions/GetPlayerItems.md)
