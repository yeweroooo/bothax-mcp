# TileExtra (type:int, label:string, owner:int, color:uint, ...)

Extra data attached to a tile: labels, owner, colour, progress, and similar. It is often
absent, so test `if t.extra then` before reading a field.

Fields
- `type: int`
- `progress: float`
- `label: string`
- `label2: string`
- `label3: string`
- `owner: int`
- `flags: int`
- `admin: int[]`
- `lastupdate: int`
- `alttype: int`
- `growth: int`
- `fruitcount: int`
- `volume: int`
- `color: uint`

Example (Lua)
```lua
local t = GetTile(10, 10)
if t.extra and t.extra.owner then
  LogToConsole(('tile owned by UID %d'):format(t.extra.owner))
end
```

Related
- [Tile](../structures/Tile.md)
