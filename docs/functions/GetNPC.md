# GetNPC(id: int) -> ClientNPC | nil

Returns one NPC by id, or `nil` when the id is unknown or the NPC is not loaded.

Parameters
- `id: int`: NPC id.

Returns
- `ClientNPC` when found, otherwise `nil`.

Example (Lua)
```lua
local npc = GetNPC(1)
if npc then
  LogToConsole('NPC type => ' .. npc.type)
else
  LogToConsole('not found')
end
```

Related
- [ClientNPC](../structures/ClientNPC.md)
- [GetNPCList](GetNPCList.md)
