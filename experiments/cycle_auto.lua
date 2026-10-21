-- Place + break Pot O' Gems dengan '[A] Auto collect' aktif.
-- Hasil: drop dari break sendiri tersedot, objek lama di tanah tidak.
local tx, ty = 72, 24
local ITEM = 16706
local function inv(id)
  local n = 0
  for _, it in pairs(GetInventory()) do
    if tonumber(it.id) == id then n = n + (tonumber(it.amount) or 0) end
  end
  return n
end
local function objs()
  local n, list = 0, {}
  for _, o in pairs(GetObjectList()) do
    n = n + 1; list[#list + 1] = tostring(o.id) .. 'x' .. tostring(o.amount)
  end
  return n, table.concat(list, ',')
end
local function gems()
  local ok, pi = pcall(GetPlayerInfo)
  if ok and type(pi) == 'table' then return tostring(pi.gems) end
  return '?'
end
ChangeValue('[A] Auto collect', true)
local flag = tostring(GetValue('[A] Auto collect'))
local p0 = GetLocal().pos
local inv0, gem0, n0, l0 = inv(ITEM), gems(), objs()
local p = GetLocal().pos
SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = ITEM,
  x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = tx, py = ty, extrasize = 0})
Sleep(400)
local function fg() local t = GetTile(tx, ty); return t and tonumber(t.fg) or 0 end
if fg() ~= ITEM then return 'PLACE_GAGAL fg=' .. tostring(fg()) end
local hits = 0
while hits < 12 and fg() == ITEM do
  SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = 18,
    x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = tx, py = ty, extrasize = 0})
  hits = hits + 1
  Sleep(400)
end
Sleep(1200)
local p1 = GetLocal().pos
local inv1, gem1, n1, l1 = inv(ITEM), gems(), objs()
return string.format(
  'auto_collect=%s | inv %d->%d | gems %s->%s | objs %d->%d [%s] -> [%s] | pos %d,%d -> %d,%d | hits=%d fg=%d',
  flag, inv0, inv1, gem0, gem1, n0, n1, l0, l1,
  math.floor(p0.x / 32), math.floor(p0.y / 32), math.floor(p1.x / 32), math.floor(p1.y / 32),
  hits, fg())
