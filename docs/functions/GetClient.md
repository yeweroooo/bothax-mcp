# GetClient() -> ENetClient

Returns the current ENet connection. Use it when a feature depends on a stable link and
you want to show or log the server address and ping.

Returns
- `ENetClient`: address, port, ping.

Example (Lua)
```lua
local client = GetClient()
LogToConsole("Connected to: " .. client.address .. ":" .. client.port)
LogToConsole("Ping: " .. client.ping .. "ms")
```

Related
- [ENetClient](../structures/ENetClient.md)
