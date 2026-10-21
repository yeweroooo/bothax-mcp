-- Uji label hook numerik vs string, percobaan kedua.
-- Hasil: label string tidak meregistrasi callback apa pun.
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
local uniq, urut = {}, {}
for _, s in ipairs(_PKT2) do
  if not uniq[s] then uniq[s] = 0; urut[#urut + 1] = s end
  uniq[s] = uniq[s] + 1
end
local out = { 'total=' .. #_PKT2 }
for _, s in ipairs(urut) do out[#out + 1] = uniq[s] .. 'x ' .. s end
return out
