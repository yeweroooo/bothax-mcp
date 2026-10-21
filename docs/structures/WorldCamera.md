# WorldCamera (pos:Vec2, center:Vec2, scale:float, resolution:Vec2)

The client's world camera. Needed to put an overlay, label, or ESP marker where the player
actually sees it.

Fields
- `pos: Vec2`: camera position in pixels.
- `center: Vec2`: centre of the view.
- `scale: float`: zoom.
- `resolution: Vec2`: view resolution.

Example (Lua)
```lua
local cam = GetCamera()
LogToConsole(('camera pos: %.1f, %.1f')
  :format(cam.pos.x, cam.pos.y))
```

Related
- [GetCamera](../functions/GetCamera.md)
