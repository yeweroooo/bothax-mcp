# GetPlayerInfo() -> PlayerItems

Ringkasan
- `GetPlayerInfo() -> PlayerItems`
- Mengambil data gem & backpack pemain.

Penjelasan
- Gunakan bila Anda ingin menampilkan jumlah gems atau memeriksa ukuran ransel saat ini.

Nilai kembali
- `PlayerItems`

Contoh (Lua)
```lua
local p = GetPlayerInfo()
LogToConsole('Gems: ' .. p.gems)
LogToConsole('Backpack Size: ' .. p.backpack.size)
```

Terkait
- [GetPlayerItems](GetPlayerItems.md)
- [PlayerItems](../structures/PlayerItems.md)
