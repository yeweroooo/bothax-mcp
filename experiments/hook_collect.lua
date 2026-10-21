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
local total = #_PKT
local counts, ordered = {}, {}
for _, s in ipairs(_PKT) do
  if not counts[s] then counts[s] = 0; ordered[#ordered + 1] = s end
  counts[s] = counts[s] + 1
end
local out = { 'total=' .. total .. ' unique=' .. #ordered }
for _, s in ipairs(ordered) do out[#out + 1] = counts[s] .. 'x ' .. s end
return out
