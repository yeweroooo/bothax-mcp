# GetPlayerInfo() -> PlayerItems

Returns gem balance and backpack information.

Returns
- `PlayerItems`

Example (Lua)
```lua
local p = GetPlayerInfo()
LogToConsole('Gems: ' .. p.gems)
LogToConsole('Backpack size: ' .. p.backpack.size)
```

Related
- [GetPlayerItems](GetPlayerItems.md)
- [PlayerItems](../structures/PlayerItems.md)
