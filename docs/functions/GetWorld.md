# GetWorld() -> World

Returns the world currently loaded: name, size in tiles, and object counts.

Returns
- `World`

Example (Lua)
```lua
local world = GetWorld()
LogToConsole('you are in world : ' .. world.name)
LogToConsole('world size : ' .. world.width .. ' x ' .. world.height)
```

Related
- [World](../structures/World.md)
