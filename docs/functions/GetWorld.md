# GetWorld() -> World

Ringkasan
- `GetWorld() -> World`
- Mengambil info world yang sedang dimuat.

Penjelasan
- Gunakan untuk mengetahui nama world dan ukurannya, misalnya saat menampilkan overlay info.

Nilai kembali
- `World`

Contoh (Lua)
```lua
local world = GetWorld()
LogToConsole('you are in world : ' .. world.name)
LogToConsole('world size : ' .. world.width .. ' x ' .. world.height)
```

Terkait
- [World](../structures/World.md)
