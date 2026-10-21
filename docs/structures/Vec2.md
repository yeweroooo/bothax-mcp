# Vec2 (x:float, y:float)

Deskripsi singkat
- Vektor 2D sederhana.

Penjelasan
- Umumnya dipakai untuk `pos` dalam pixel di berbagai struktur (avatar, kamera, objek).

Bidang
- `x: float` — Sumbu X.
- `y: float` — Sumbu Y.

Contoh penggunaan (Lua)
```lua
local me = GetLocal()
local pos = me.pos -- Vec2
LogToConsole(('(%d,%d)'):format(pos.x // 32, pos.y // 32))
```

Terkait
- [NetAvatar](../structures/NetAvatar.md)
- [WorldCamera](../structures/WorldCamera.md)
- [WorldObject](../structures/WorldObject.md)
