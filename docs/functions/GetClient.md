# GetClient() -> ENetClient

Mendapatkan info koneksi ENet saat ini. Bantu diagnosa jaringan (alamat server dan ping) saat fitur Anda bergantung pada koneksi stabil.

Nilai kembali
- `ENetClient`: address, port, ping.

Contoh (Lua)
```lua
local client = GetClient()
LogToConsole("Connected to: " .. client.address .. ":" .. client.port)
LogToConsole("Ping: " .. client.ping .. "ms")
```

Terkait
- [ENetClient](../structures/ENetClient.md)
