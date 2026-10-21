-- First attempt: record tile action packets (type 3) through OnSendPacketRaw.
-- Result: place and break were recorded, no separate collect packet showed up.
_PKT = {}
local function rec(pkt)
  if type(_PKT) ~= 'table' or #_PKT >= 400 then return end
  local parts = {}
  for k, v in pairs(pkt) do parts[#parts + 1] = tostring(k) .. '=' .. tostring(v) end
  _PKT[#_PKT + 1] = table.concat(parts, ' ')
end
AddHook('OnSendPacketRaw', 'rec_collect', function(pkt) pcall(rec, pkt) end)
Sleep(7000)
RemoveHook('rec_collect')
local jumlah = #_PKT
local uniq, urut = {}, {}
for _, s in ipairs(_PKT) do
  if not uniq[s] then uniq[s] = 0; urut[#urut + 1] = s end
  uniq[s] = uniq[s] + 1
end
local out = { 'total=' .. jumlah .. ' unik=' .. #urut }
for _, s in ipairs(urut) do out[#out + 1] = uniq[s] .. 'x ' .. s end
return out
