# GetCamera() -> WorldCamera

Ringkasan
- `GetCamera() -> WorldCamera`
- Mengambil informasi kamera world.

Penjelasan
- Bantu perhitungan posisi layar untuk menggambar overlay, teks, atau indikator arah.

Nilai kembali
- `WorldCamera` — Posisi, center, scale, dan resolusi.

Contoh (Lua)
```lua
local cam = GetCamera()
LogToConsole("Camera Position: " .. cam.pos.x .. ", " .. cam.pos.y)
LogToConsole("Camera Center: " .. cam.center.x .. ", " .. cam.center.y)
LogToConsole("Camera Scale: " .. cam.scale)
LogToConsole("Resolution: " .. cam.resolution.x .. "x" .. cam.resolution.y)
```

Terkait
- [WorldCamera](../structures/WorldCamera.md)
