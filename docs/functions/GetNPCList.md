# GetNPCList() -> ClientNPC[]

Returns every NPC currently loaded in the world. Use it to scan positions or to find out
whether a given NPC type is present.

Returns
- `ClientNPC[]`

Example (Lua)
```lua
for _, npc in pairs(GetNPCList()) do
  LogToConsole('found NPC id: ' .. npc.id)
end
```

Related
- [ClientNPC](../structures/ClientNPC.md)
- [GetNPC](GetNPC.md)
