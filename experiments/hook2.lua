-- Numeric versus string hook labels, second attempt.
-- Result: a string label registers no callback at all. Kept as-is on purpose.
_PKT2 = {}
local function one(p)
  if type(_PKT2) ~= 'table' or #_PKT2 >= 300 then return end
  _PKT2[#_PKT2 + 1] = string.format(
    'type=%s state=%s value=%s netid=%s snetid=%s x=%s y=%s px=%s py=%s extra=%s',
    tostring(p.type), tostring(p.state), tostring(p.value or p.int_data),
    tostring(p.netid), tostring(p.snetid), tostring(p.x), tostring(p.y),
    tostring(p.px), tostring(p.py), tostring(p.extrasize))
end
AddHook('OnSendPacketRaw', 'rec2', function(p) pcall(one, p) end)
Sleep(7000)
RemoveHook('rec2')
local counts, ordered = {}, {}
for _, s in ipairs(_PKT2) do
  if not counts[s] then counts[s] = 0; ordered[#ordered + 1] = s end
  counts[s] = counts[s] + 1
end
local out = { 'total=' .. #_PKT2 }
for _, s in ipairs(ordered) do out[#out + 1] = counts[s] .. 'x ' .. s end
return out
