# GetTile(x: int, y: int) -> Tile

Returns one tile, which is how you read `fg`, `bg`, `flags`, and `extra`. Reading a tile
does not modify it.

Parameters
- `x: int`: tile X.
- `y: int`: tile Y.

Returns
- `Tile`

Example (Lua)
```lua
local tile = GetTile(12, 12)
if tile.fg == 242 then
  LogToConsole('world lock found')
end
```

Related
- [GetTiles](GetTiles.md)
- [Tile](../structures/Tile.md)
