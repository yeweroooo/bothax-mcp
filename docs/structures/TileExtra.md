# TileExtra (type:int, label:string, owner:int, color:uint, ...)

Deskripsi singkat
- Data tambahan sebuah tile (label, owner, warna, progres, dsb.).

Penjelasan
- `extra` tidak selalu ada. Cek dulu `if t.extra then ... end` sebelum mengakses field-nya.

Bidang
- `type: int`
- `progress: float`
- `label: string`
- `label2: string`
- `label3: string`
- `owner: int`
- `flags: int`
- `admin: int[]`
- `lastupdate: int`
- `alttype: int`
- `growth: int`
- `fruitcount: int`
- `volume: int`
- `color: uint`

Contoh penggunaan (Lua)
```lua
local t = GetTile(10, 10)
if t.extra and t.extra.owner then
  LogToConsole(('Tile dimiliki UID: %d'):format(t.extra.owner))
end
```

Terkait
- [Tile](../structures/Tile.md)
