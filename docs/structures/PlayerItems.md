# PlayerItems (gems:int, backpack:table)

Player-owned data: gem balance and backpack configuration. Read it instead of parsing
packets when you only need the numbers.

Fields
- `gems: int`: gem balance.
- `backpack: table`: backpack info:
  - `priority: int[]`: slot priority order.
  - `size: int`: maximum backpack size.
  - `selected: int`: currently selected slot.

Example (Lua)
```lua
local p = GetPlayerInfo()
LogToConsole(('gems: %d, backpack size: %d')
  :format(p.gems, p.backpack.size))
```

Related
- [GetPlayerInfo](../functions/GetPlayerInfo.md)
- [GetPlayerItems](../functions/GetPlayerItems.md)
