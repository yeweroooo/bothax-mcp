# GetPlayer(netid: int) -> NetAvatar | nil

Mengambil info pemain lain berdasarkan netid. Mengembalikan `nil` bila netid tidak ditemukan (tidak terload/di luar jarak).

Parameter
- `netid: int`: Net ID pemain.

Nilai kembali
- `NetAvatar` jika ditemukan, `nil` jika tidak.

Contoh (Lua)
```lua
local p = GetPlayer(2)
if p then LogToConsole(p.name) end
```

Terkait
- [GetPlayerList](GetPlayerList.md)
- [NetAvatar](../structures/NetAvatar.md)
