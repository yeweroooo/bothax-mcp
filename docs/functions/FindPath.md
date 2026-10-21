# FindPath(tilex: int, tiley: int)

Moves the avatar to a tile using the game's own pathing. Check the tile with `CheckPath`
first; a solid target leaves the avatar where it was.

The move is the client's fast walk, not step-by-step animation, and it can take more than
one tick to land. Read `GetLocal().pos` afterwards instead of assuming it worked.

Parameters
- `tilex: int`: tile X.
- `tiley: int`: tile Y.

Returns
- Nothing.

Example (Lua)
```lua
if CheckPath(0, 0) then
  FindPath(0, 0)
end
```

Related
- [CheckPath](CheckPath.md)
- [GetLocal](GetLocal.md)
