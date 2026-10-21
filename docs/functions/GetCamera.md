# GetCamera() -> WorldCamera

Returns the world camera. Use it to convert between world pixels and screen space when you
draw overlays, labels, or direction markers.

Returns
- `WorldCamera`: position, centre, scale, and resolution.

Example (Lua)
```lua
local cam = GetCamera()
LogToConsole("Camera position: " .. cam.pos.x .. ", " .. cam.pos.y)
LogToConsole("Camera centre: " .. cam.center.x .. ", " .. cam.center.y)
LogToConsole("Camera scale: " .. cam.scale)
LogToConsole("Resolution: " .. cam.resolution.x .. "x" .. cam.resolution.y)
```

Related
- [WorldCamera](../structures/WorldCamera.md)
