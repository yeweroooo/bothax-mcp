# ENetClient (address:string, port:int, ping:int)

The ENet connection to the server. Useful for showing latency or logging which server a
session landed on.

Fields
- `address: string`: server address.
- `port: int`: server port.
- `ping: int`: current ping in milliseconds.

Example (Lua)
```lua
local cli = GetClient()
LogToConsole(('connected to %s:%d (ping %d ms)')
  :format(cli.address, cli.port, cli.ping))
```

Related
- [GetClient](../functions/GetClient.md)
