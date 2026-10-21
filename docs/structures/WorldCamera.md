# WorldCamera (pos:Vec2, center:Vec2, scale:float, resolution:Vec2)

Deskripsi singkat
- Informasi kamera dunia di klien.

Penjelasan
- Berguna untuk menempatkan overlay/UI (ImGui) atau fitur ESP pada posisi yang tepat.

Bidang
- `pos: Vec2` — Posisi kamera (pixel).
- `center: Vec2` — Titik tengah tampilan.
- `scale: float` — Skala zoom.
- `resolution: Vec2` — Resolusi tampilan.

Contoh penggunaan (Lua)
```lua
local cam = GetCamera()
LogToConsole(('Camera pos: %.1f, %.1f')
  :format(cam.pos.x, cam.pos.y))
```

Terkait
- [GetCamera](../functions/GetCamera.md)
