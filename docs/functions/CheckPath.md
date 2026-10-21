# CheckPath(tilex: int, tiley: int) -> boolean

Says whether the avatar can stand on a tile. Call it before `FindPath` so you do not send
the avatar into a solid block.

Parameters
- `tilex: int`: tile X.
- `tiley: int`: tile Y.

Returns
- `true` when the tile is passable, `false` otherwise.

Example (Lua)
```lua
if CheckPath(0, 0) then
  FindPath(0, 0)
end
```

Related
- [FindPath](FindPath.md)
