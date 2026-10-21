# GetPlayerList() -> NetAvatar[]

Returns the other players loaded around you. Your own avatar is not included.

Returns
- `NetAvatar[]`

Example (Lua)
```lua
for _, plr in pairs(GetPlayerList()) do
  LogToConsole(('player %s at %d,%d')
    :format(plr.name, plr.pos.x // 32, plr.pos.y // 32))
end
```

Related
- [NetAvatar](../structures/NetAvatar.md)
- [GetPlayer](GetPlayer.md)
