# TileFlags (value:int, locked:boolean, public:boolean, water:boolean, ...)

Flag/penanda kondisi khusus pada tile. Representasi kondisi tile dalam bentuk boolean/bitmask. Ubah nilai flag dengan fungsi `SetTileFlags`.

Bidang
- `value: int`: Nilai bitmask keseluruhan.
- `locked: boolean`
- `spliced: boolean`
- `dropseed: boolean`
- `tree: boolean`
- `flipped: boolean`
- `enabled: boolean`
- `public: boolean`
- `silenced: boolean`
- `water: boolean`
- `glue: boolean`
- `burn: boolean`
- `red: boolean`
- `green: boolean`
- `blue: boolean`

Contoh penggunaan (Lua)
```lua
SetTileFlags(10, 5, 16384)
SetTileFlags(15, 8, {
  locked = true,
  public = true,
  water = true
})
```

Terkait
- [SetTileFlags](../functions/SetTileFlags.md)
- [Tile](../structures/Tile.md)
