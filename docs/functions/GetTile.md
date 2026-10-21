# GetTile(x: int, y: int) -> Tile

Ringkasan
- `GetTile(x: int, y: int) -> Tile`
- Mengambil info tile pada koordinat (x, y).

Penjelasan
- Gunakan untuk membaca `fg/bg/flags/extra` pada sebuah tile tertentu. Fungsi ini tidak mengubah tile.

Parameter
- `x: int` — Tile X.
- `y: int` — Tile Y.

Nilai kembali
- `Tile`

Contoh (Lua)
```lua
local tile = GetTile(12, 12)
if tile.fg == 242 then
  LogToConsole('World Lock Found!')
end
```

Terkait
- [GetTiles](GetTiles.md)
- [Tile](../structures/Tile.md)
