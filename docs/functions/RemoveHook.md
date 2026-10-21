# RemoveHook(hook_id: int|string)

Removes one hook by the label used in `AddHook`, without touching the others.

Parameters
- `hook_id: int|string`: the same label you passed to `AddHook`.

Returns
- Nothing.

Example (Lua)
```lua
AddHook('OnSendPacket', 123, function(_, str) LogToConsole(str) end)
RemoveHook(123)
```

Related
- [AddHook](AddHook.md)
- [RemoveHooks](RemoveHooks.md)
