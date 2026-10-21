# ENetClient (address:string, port:int, ping:int)

Informasi koneksi ENet ke server (alamat, port, ping). Bermanfaat untuk memantau latency/ping saat ini dan alamat server yang terhubung.

Bidang
- `address: string`: Alamat server (IP/host).
- `port: int`: Port server.
- `ping: int`: Ping saat ini (ms).

Contoh penggunaan (Lua)
```lua
local cli = GetClient()
LogToConsole(('Terhubung ke %s:%d (ping %d ms)')
  :format(cli.address, cli.port, cli.ping))
```

Terkait
- [GetClient](../functions/GetClient.md)
