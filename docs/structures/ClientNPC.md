# ClientNPC (id:int, type:int, pos:Vec2, target:Vec2)

An NPC as the client sees it. Read it for position, type, and the point it is walking
towards. `pos` and `target` are pixels; divide by 32 for tiles.

Fields
- `id: int`: NPC id in the current world.
- `type: int`: NPC type.
- `pos: Vec2`: current position in pixels.
- `target: Vec2`: target position in pixels.

Example (Lua)
```lua
local npc = GetNPC(1)
if npc then
  LogToConsole(('NPC %d type %d at (%d,%d)')
    :format(npc.id, npc.type, npc.pos.x // 32, npc.pos.y // 32))
else
  LogToConsole('NPC not found')
end
```

Related
- [GetNPC](../functions/GetNPC.md)
- [GetNPCList](../functions/GetNPCList.md)
- [Vec2](../structures/Vec2.md)
