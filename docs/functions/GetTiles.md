# GetTiles() -> Tile[]

Ringkasan
- `GetTiles() -> Tile[]`
- Mengambil semua tile di world saat ini.

Penjelasan
- Mengembalikan seluruh grid tile. Iterasi pada world besar bisa memakan waktu; filter kondisi seperlunya.

Nilai kembali
- Array `Tile`

Contoh (Lua)
```lua
for _, tile in pairs(GetTiles()) do
  if tile.fg == 242 then
    LogToConsole('Found WL at '.. tile.x .. ', ' .. tile.y)
  end
end
```

Terkait
- [GetTile](GetTile.md)
- [Tile](../structures/Tile.md)
