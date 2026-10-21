# CheckPath(tilex: int, tiley: int) -> boolean

Ringkasan
- `CheckPath(tilex: int, tiley: int) -> boolean`
- Mengecek apakah tile bisa dilalui.

Penjelasan
- Berguna sebelum melakukan `FindPath` agar tidak melompat ke tile yang terhalang.

Parameter
- `tilex: int` — Koordinat tile X.
- `tiley: int` — Koordinat tile Y.

Nilai kembali
- `true` jika jalur dapat dilalui, selain itu `false`.

Contoh (Lua)
```lua
if CheckPath(0, 0) then
  FindPath(0, 0)
end
```

Terkait
- [FindPath](FindPath.md)
