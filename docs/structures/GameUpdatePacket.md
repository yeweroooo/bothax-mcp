# GameUpdatePacket (raw packet struct)

The structure behind raw packets. Several fields carry two names, and which one applies
depends on `type`. A wrong combination is ignored at best and disconnects you at worst, so
change one field at a time.

Fields
- `type: int`: packet type.
- `dropped: int`
- `netid | player_flags: int`
- `snetid | secondnetid: int`
- `state | characterstate: int`
- `value | int_data: int`
- `x | pos_x: float`
- `xspeed: float`
- `yspeed: float`
- `px | tx | int_x: int`
- `py | ty | int_y: int`
- `padding1: int`
- `padding2: int`
- `padding4: float`
- `extrasize: int`

Notes
- Tile actions use `type = 3` with `value` set to the item id (place) or `18` (Fist,
  break). Collecting uses `type = 11` with `value` set to the object oid and `px`/`py` set
  to the object position.
- `px` and `py` are tile coordinates, `x` and `y` are pixels. Sending the wrong pair is the
  usual reason a packet does nothing.

Example (Lua)
```lua
local pkt = { type = 10, value = 1796 }
SendPacketRaw(false, pkt)
```

Related
- [SendPacketRaw](../functions/SendPacketRaw.md)
