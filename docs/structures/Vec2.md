# Vec2 (x:float, y:float)

A 2D vector, used for pixel positions in avatar, camera, and object structures. One tile is
32 pixels.

Fields
- `x: float`: X axis.
- `y: float`: Y axis.

Example (Lua)
```lua
local me = GetLocal()
local pos = me.pos -- Vec2
LogToConsole(('(%d,%d)'):format(pos.x // 32, pos.y // 32))
```

Related
- [NetAvatar](../structures/NetAvatar.md)
- [WorldCamera](../structures/WorldCamera.md)
- [WorldObject](../structures/WorldObject.md)
