-- Scan the world: locks in the tile grid, locks lying on the ground as drops.

for _, tile in pairs(GetTiles()) do
  if tile.fg == 242 then
    LogToConsole(('lock tile at %d,%d'):format(tile.x, tile.y))
  end
end

for _, obj in pairs(GetObjectList()) do
  if obj.id == 242 then
    LogToConsole(('lock drop at %d,%d amount %d')
      :format(obj.pos.x // 32, obj.pos.y // 32, obj.amount))
  end
end
