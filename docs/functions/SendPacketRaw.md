# SendPacketRaw(to_client: boolean, packet: GameUpdatePacket)

Sends a raw packet to the client (`true`) or to the server (`false`). The table must follow
`GameUpdatePacket`; a wrong `type` or `value` can disconnect you, so test on a throwaway
world first.

Parameters
- `to_client: boolean`: `true` for the client, `false` for the server.
- `packet: GameUpdatePacket`: packet fields.

Returns
- Nothing.

Example (Lua)
```lua
local packet = { type = 10, value = 1796 }
SendPacketRaw(false, packet)
```

Related
- [GameUpdatePacket](../structures/GameUpdatePacket.md)
