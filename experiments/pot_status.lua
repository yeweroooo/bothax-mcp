-- Status reader: gems, world object count, and the contents of the target tile.
local ok, pi = pcall(GetPlayerInfo)
local gems = (ok and type(pi) == 'table') and tostring(pi.gems) or '?'
local nobj = 0
for _ in pairs(GetObjectList()) do nobj = nobj + 1 end
local L = _POTLOOP or {}
local pos = GetLocal().pos
return string.format('active=%s finished=%s cycles=%d inv=%s/%s hits=%d skipped=%d gems=%s objs=%d pos=%d,%d note=%s',
  tostring(L.active), tostring(L.finished), tonumber(L.cycles) or 0,
  tostring(L.inv_now), tostring(L.start_inv), tonumber(L.hits) or 0, tonumber(L.skipped) or 0,
  gems, nobj, math.floor(pos.x / 32), math.floor(pos.y / 32), tostring(L.note))
