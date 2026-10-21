-- Scan world: cari World Lock dan objek WL yang jatuh

for _, tile in pairs(GetTiles()) do
  if tile.fg == 242 then
    LogToConsole(('WL tile at %d,%d'):format(tile.x, tile.y))
  end
end

for _, obj in pairs(GetObjectList()) do
  if obj.id == 242 then
    LogToConsole(('WL drop at %d,%d amount %d')
      :format(obj.pos.x // 32, obj.pos.y // 32, obj.amount))
  end
end

