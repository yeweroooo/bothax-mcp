# TileFlags (value:int, locked:boolean, public:boolean, water:boolean, ...)

Special conditions on a tile, readable as named booleans or as one bitmask in `value`. Write
them with `SetTileFlags`.

Fields
- `value: int`: the whole bitmask.
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

Example (Lua)
```lua
SetTileFlags(10, 5, 16384)
SetTileFlags(15, 8, {
  locked = true,
  public = true,
  water = true
})
```

Related
- [SetTileFlags](../functions/SetTileFlags.md)
- [Tile](../structures/Tile.md)
