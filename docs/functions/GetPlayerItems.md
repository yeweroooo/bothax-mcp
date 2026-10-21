# GetPlayerItems() -> PlayerItems

Alias for `GetPlayerInfo()`. Returns the same `gems` and backpack data.

Returns
- `PlayerItems`

Example (Lua)
```lua
local p = GetPlayerItems()
LogToConsole('Gems: ' .. p.gems)
```

Related
- [GetPlayerInfo](GetPlayerInfo.md)
- [PlayerItems](../structures/PlayerItems.md)
