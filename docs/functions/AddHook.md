# AddHook(event: string, label: int|string, callback: function)

Registers a callback for one BothaxHook event. Give `label` a unique value so
`RemoveHook` can find it again. Returning `true` from the callback blocks that event.

Parameters
- `event: string`: event name, such as `OnVariant` or `OnSendPacket`.
- `label: int|string`: hook id used by `RemoveHook`. Use a number: string labels have been
  observed to register no callback at all.
- `callback: function`: called whenever the event fires.

Returns
- Nothing. The hook is identified by the label you passed in.

Notes
- Returning `true` from the callback swallows the event.
- A failed string-label attempt can leave existing hooks dead until the game restarts.

Example (Lua)
```lua
AddHook('OnSendPacket', 101, function(type, text)
  if text:find('/hi') then
    LogToConsole('hello!')
    return true
  end
end)
```

Related
- [BothaxHook](BothaxHook.md)
- [RemoveHook](RemoveHook.md) / [RemoveHooks](RemoveHooks.md)
