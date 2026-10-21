# FindPath(tilex: int, tiley: int)

Ringkasan
- `FindPath(tilex: int, tiley: int)`
- Teleport/jalan cepat ke tile tujuan.

Penjelasan
- Pastikan tile dapat dilalui (lihat `CheckPath`) untuk menghindari stuck pada blok padat.

Parameter
- `tilex: int` — Koordinat tile X.
- `tiley: int` — Koordinat tile Y.

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
FindPath(0, 0)
```

Terkait
- [CheckPath](CheckPath.md)
