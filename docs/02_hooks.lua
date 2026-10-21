-- Contoh semua hook umum

AddHook('OnVariant', 'demo_var', function(var, netid, delay)
  if var[0] == 'OnDialogRequest' then
    LogToConsole('OnVariant: dialog terdeteksi (netid=' .. tostring(netid) .. ')')
  end
end)

AddHook('OnSendPacket', 'demo_sp', function(typ, pkt)
  LogToConsole('OnSendPacket: type=' .. tostring(typ) .. ' text=' .. pkt)
end)

AddHook('OnSendPacketRaw', 'demo_raw', function(pkt)
  LogToConsole('OnSendPacketRaw: type=' .. tostring(pkt.type))
end)

AddHook('OnProcessTankUpdate', 'demo_tank', function(pkt)
  if pkt.type == 34 then
    LogToConsole('NPC bergerak terdeteksi')
  end
end)

AddHook('OnWorldTouch', 'demo_touch', function(pos, start)
  if start then
    LogToConsole(('Tile touched: (%d, %d)'):format(pos.x // 32, pos.y // 32))
  end
end)

AddHook('OnDraw', 'demo_draw', function(dt)
  if ImGui.Begin('Demo OnDraw') then
    ImGui.Text('Delta Time: ' .. tostring(dt))
  end
  ImGui.End()
end)

-- Windows-only
AddHook('OnInput', 'demo_input', function(key)
  LogToConsole('Key Pressed: ' .. string.char(key))
end)

