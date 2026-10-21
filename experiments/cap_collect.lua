-- Percobaan menangkap paket collect lewat 4 hook.
-- Hasil: 0 event, hook OnSendPacketRaw sudah mati di sesi itu.
_PKT4 = {}
local function fg()
  local t = GetTile(72, 24)
  return t and tonumber(t.fg) or 0
end
AddHook('OnSendPacketRaw', 777001, function(p)
  if type(_PKT4) ~= 'table' or #_PKT4 >= 400 then return end
  _PKT4[#_PKT4 + 1] = string.format(
    '%s|type=%s|state=%s|value=%s|netid=%s|snetid=%s|x=%s|y=%s|px=%s|py=%s',
    tostring(GetTick()), tostring(p.type), tostring(p.state), tostring(p.value),
    tostring(p.netid), tostring(p.snetid), tostring(p.x), tostring(p.y),
    tostring(p.px), tostring(p.py))
end)
local ITEM = 5034
local info = GetItemInfo(ITEM)
local obj0 = 0
for _ in pairs(GetObjectList()) do obj0 = obj0 + 1 end
local p = GetLocal().pos
SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = ITEM,
  x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = 72, py = 24, extrasize = 0})
Sleep(450)
local placed = fg()
local hits = 0
if placed == ITEM then
  while hits < 15 and fg() == ITEM do
    SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = 18,
      x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = 72, py = 24, extrasize = 0})
    hits = hits + 1
    Sleep(300)
  end
end
Sleep(1500)
RemoveHook(777001)
local obj1, list = 0, {}
for _, o in pairs(GetObjectList()) do
  obj1 = obj1 + 1
  list[#list + 1] = tostring(o.id) .. 'x' .. tostring(o.amount)
end
local out = {
  string.format('item=%s breakhit=%s placed=%s hits=%d objs %d->%d [%s] paket=%d',
    tostring(info and info.name), tostring(info and info.breakhit), tostring(placed),
    hits, obj0, obj1, table.concat(list, ','), #_PKT4),
}
for _, s in ipairs(_PKT4) do out[#out + 1] = s end
return out
