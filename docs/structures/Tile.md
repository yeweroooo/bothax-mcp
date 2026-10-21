# Tile (fg:int, bg:int, flags:TileFlags, extra:TileExtra|nil, x:int, y:int)

A block in the world. `fg` is the foreground block and `bg` the background wall. `flags`
carries special conditions such as locked or public, and `extra` holds extra data when the
tile has any.

`fg = 0` means an empty tile, which is how you confirm a block was broken.

Fields
- `fg: int`: foreground item id.
- `bg: int`: background item id.
- `collidable: boolean`: whether it blocks movement.
- `x: int`: tile X.
- `y: int`: tile Y.
- `coltype: int`: collision type.
- `locktile: int`: lock info, when present.
- `flags: TileFlags`: tile flags.
- `extra: TileExtra | nil`: extra data, often `nil`.

Notes
- Some examples in the wild use `tile.pos.x`. If the table has no `pos`, read `x` and `y`
  directly.

Example (Lua)
```lua
local t = GetTile(12, 12)
if t.fg == 242 then
  LogToConsole('world lock found')
end
```

Related
- [GetTile](../functions/GetTile.md)
- [GetTiles](../functions/GetTiles.md)
- [TileFlags](../structures/TileFlags.md)
- [TileExtra](../structures/TileExtra.md)
