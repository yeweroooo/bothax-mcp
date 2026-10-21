# GetPlayer(netid: int) -> NetAvatar | nil

Returns another player by netid, or `nil` when that player is not loaded, for example when
they are out of range.

Parameters
- `netid: int`: the player's net id.

Returns
- `NetAvatar` when found, otherwise `nil`.

Example (Lua)
```lua
local p = GetPlayer(2)
if p then LogToConsole(p.name) end
```

Related
- [GetPlayerList](GetPlayerList.md)
- [NetAvatar](../structures/NetAvatar.md)
