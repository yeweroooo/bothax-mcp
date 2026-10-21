# GetTiles() -> Tile[]

Returns every tile in the loaded world. Large worlds take a moment to walk, so filter as you
iterate rather than copying the grid.

Returns
- `Tile[]`

Example (Lua)
```lua
for _, tile in pairs(GetTiles()) do
  if tile.fg == 242 then
    LogToConsole('found a lock at '.. tile.x .. ', ' .. tile.y)
  end
end
```

Related
- [GetTile](GetTile.md)
- [Tile](../structures/Tile.md)
