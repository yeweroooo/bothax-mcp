# GetPlayerItems() -> PlayerItems

Ringkasan
- `GetPlayerItems() -> PlayerItems`
- Alias dari `GetPlayerInfo()`.

Penjelasan
- Berisi `gems` dan informasi ransel. Sama dengan `GetPlayerInfo()`.

Nilai kembali
- `PlayerItems`

Contoh (Lua)
```lua
local p = GetPlayerItems()
LogToConsole('Gems: ' .. p.gems)
```

Terkait
- [GetPlayerInfo](GetPlayerInfo.md)
- [PlayerItems](../structures/PlayerItems.md)
