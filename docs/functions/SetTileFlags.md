# SetTileFlags(tileX: int, tileY: int, flags: int | TileFlags)

Sets tile flags at a coordinate, either as an integer bitmask or as a `TileFlags` table.

Parameters
- `tileX: int`: tile X.
- `tileY: int`: tile Y.
- `flags: int | TileFlags`: bitmask or flag table.

Returns
- Nothing.

Example (Lua)
```lua
-- bitmask
SetTileFlags(10, 5, 16384)

-- flag table
SetTileFlags(15, 8, {
  locked = true,
  public = true,
  water = true
})
```

Related
- [TileFlags](../structures/TileFlags.md)
- [GetTile](GetTile.md)
