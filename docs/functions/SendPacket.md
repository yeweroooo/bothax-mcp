# SendPacket(type: int, packet: string)

Sends a text packet to the server. Type `2` carries text actions such as
`action|respawn` or `action|dialog_return`; type `3` is used by a few game packets. The body
has to match what the server expects, including the trailing newline some actions require.

Parameters
- `type: int`: packet type, `2` or `3` in practice.
- `packet: string`: packet body.

Returns
- Nothing.

Example (Lua)
```lua
SendPacket(2, 'action|respawn')

-- drop a whole stack: the pipe after the id is required
SendPacket(2, 'action|dialog_return\ndialog_name|drop\nitem_drop|5026|\nitem_count|7\n')
```

Related
- [SendPacketRaw](SendPacketRaw.md)
