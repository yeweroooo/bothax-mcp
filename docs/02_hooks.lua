-- Every common hook in one file.
-- Numeric labels, because string labels register nothing in this build.

AddHook('OnVariant', 1, function(var, netid, delay)
  if var[0] == 'OnDialogRequest' then
    LogToConsole('OnVariant: dialog seen (netid=' .. tostring(netid) .. ')')
  end
end)

AddHook('OnSendPacket', 2, function(typ, pkt)
  LogToConsole('OnSendPacket: type=' .. tostring(typ) .. ' text=' .. pkt)
end)

AddHook('OnSendPacketRaw', 3, function(pkt)
  LogToConsole('OnSendPacketRaw: type=' .. tostring(pkt.type))
end)

AddHook('OnProcessTankUpdate', 4, function(pkt)
  if pkt.type == 34 then
    LogToConsole('NPC movement packet')
  end
end)

AddHook('OnWorldTouch', 5, function(pos, start)
  if start then
    LogToConsole(('tile touched: (%d, %d)'):format(pos.x // 32, pos.y // 32))
  end
end)

AddHook('OnDraw', 6, function(dt)
  if ImGui.Begin('Demo OnDraw') then
    ImGui.Text('delta time: ' .. tostring(dt))
  end
  ImGui.End()
end)

-- Windows only
AddHook('OnInput', 7, function(key)
  LogToConsole('key pressed: ' .. string.char(key))
end)
