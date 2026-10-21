# SetTileFlags(tileX: int, tileY: int, flags: int | TileFlags)

Ringkasan
- `SetTileFlags(tileX: int, tileY: int, flags: int | TileFlags)`
- Mengatur flag tile pada koordinat tertentu.

Penjelasan
- Bisa menggunakan bitmask `int` atau tabel `TileFlags`. Pastikan koordinat tile sesuai target yang diinginkan.

Parameter
- `tileX: int` — Koordinat X tile.
- `tileY: int` — Koordinat Y tile.
- `flags: int | TileFlags` — Bitmask integer atau tabel `TileFlags`.

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
-- Dengan bitmask
SetTileFlags(10, 5, 16384)

-- Dengan tabel flag
SetTileFlags(15, 8, {
  locked = true,
  public = true,
  water = true
})
```

Terkait
- [TileFlags](../structures/TileFlags.md)
- [GetTile](GetTile.md)
