# World (name:string, width:int, height:int)

The world currently loaded. Width and height are in tiles and change when you move worlds.

Fields
- `name: string`: world name.
- `width: int`: width in tiles.
- `height: int`: height in tiles.
- `tilecount: int`: total tiles.
- `objectcount: int`: active world objects.
- `lastoid: int`: last object id handed out.

Example (Lua)
```lua
local w = GetWorld()
LogToConsole(('world %s (%dx%d)'):format(w.name, w.width, w.height))
```

Related
- [GetWorld](../functions/GetWorld.md)
