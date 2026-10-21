# BothaxHook (event names)

The event names `AddHook` accepts. Use them to observe game behaviour, and return `true`
from the callback when you want to block the event.

Events and callback parameters
- `OnVariant(var, netid, delay)`: text or game variant, for example `OnDialogRequest`.
- `OnSendPacket(type, packet)`: text packet before it is sent.
- `OnSendPacketRaw(packet)`: `GameUpdatePacket` before it is sent.
- `OnProcessTankUpdate(packet)`: update packet processed by the client.
- `OnWorldTouch(pos, start)`: world touch or tap, `pos` in pixels.
- `OnDraw(deltatime)`: render frame, used for ImGui overlays.
- `OnInput(key)`: Windows only, a key was pressed.

Notes
- Only numeric labels produced events in our tests; see [AddHook](AddHook.md).
- Blocking `OnProcessTankUpdate` hides state the client needs, so prefer reading packets
  and acting elsewhere.

Example (Lua)
```lua
AddHook('OnVariant', 7, function(var)
  if var[0] == 'OnDialogRequest' then
    LogToConsole('dialog blocked')
    return true
  end
end)
```

Related
- [AddHook](AddHook.md)
- [RemoveHook](RemoveHook.md) / [RemoveHooks](RemoveHooks.md)
