# NetAvatar (name:string, netid:int, pos:Vec2, userid:int, country:string, invisible:boolean)

An avatar in the world, yours or someone else's. `GetLocal()` returns yours,
`GetPlayer(netid)` one other, and `GetPlayerList()` the rest.

Fields
- `pos: Vec2`: position in pixels.
- `name: string`: display name.
- `isleft: boolean`: facing left.
- `netid: int`: session-unique net id.
- `userid: int`: account id.
- `country: string`: country code.
- `invisible: boolean`: hidden.
- `mstate: boolean`: movement state; meaning depends on the build.
- `smstate: boolean`: secondary movement state.

Example (Lua)
```lua
local me = GetLocal()
LogToConsole(('hello %s at (%d,%d)')
  :format(me.name, me.pos.x // 32, me.pos.y // 32))
```

Related
- [GetLocal](../functions/GetLocal.md)
- [GetPlayer](../functions/GetPlayer.md)
- [GetPlayerList](../functions/GetPlayerList.md)
