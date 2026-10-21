# RequestJoinWorld(worldname: string)

Asks the server to move you to a world, the same thing `/join` does when typed in chat. The
move happens asynchronously; poll `GetWorld().name` if you need to confirm it.

Parameters
- `worldname: string`: world name.

Returns
- Nothing.

Example (Lua)
```lua
RequestJoinWorld('START')
```

Related
- [GetWorld](GetWorld.md)
