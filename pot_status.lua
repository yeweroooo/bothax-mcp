local ok, pi = pcall(GetPlayerInfo)
local gems = (ok and type(pi) == 'table') and tostring(pi.gems) or '?'
local nobj = 0
for _ in pairs(GetObjectList()) do nobj = nobj + 1 end
local L = _POTLOOP or {}
local pos = GetLocal().pos
return string.format('aktif=%s selesai=%s siklus=%d inv=%s/%s hits=%d lewat=%d gems=%s objs=%d pos=%d,%d catatan=%s',
  tostring(L.aktif), tostring(L.selesai), tonumber(L.siklus) or 0,
  tostring(L.sekarang), tostring(L.awal), tonumber(L.hits) or 0, tonumber(L.lewat) or 0,
  gems, nobj, math.floor(pos.x / 32), math.floor(pos.y / 32), tostring(L.catatan))
