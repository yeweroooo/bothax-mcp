# RemoveHooks()

Removes every registered hook. Useful when iterating on a script, or when you want all
listeners gone before installing a fresh set.

Returns
- Nothing.

Example (Lua)
```lua
AddHook('OnSendPacket', 1, function(_, s) LogToConsole(s) end)
AddHook('OnSendPacketRaw', 2, function(p) LogToConsole(p.type) end)
RemoveHooks()
```

Related
- [RemoveHook](RemoveHook.md)
- [AddHook](AddHook.md)
