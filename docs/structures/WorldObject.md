# WorldObject (id:int, pos:Vec2, amount:int, oid:int)

Deskripsi singkat
- Objek terjatuh/tersebar di dunia (drop, dll.).

Penjelasan
- `id` adalah item id dari objek yang jatuh; `amount` adalah jumlahnya. Posisi dalam pixel.

Bidang
- `id: int` — Item ID objek.
- `pos: Vec2` — Posisi (pixel).
- `amount: int` — Jumlah.
- `flags: int` — Flag objek.
- `oid: int` — Object ID unik.

Contoh penggunaan (Lua)
```lua
for _, obj in pairs(GetObjectList()) do
  if obj.id == 242 then
    LogToConsole(('Wolok di (%d,%d), jumlah %d')
      :format(obj.pos.x // 32, obj.pos.y // 32, obj.amount))
  end
end
```

Terkait
- [GetObjectList](../functions/GetObjectList.md)
