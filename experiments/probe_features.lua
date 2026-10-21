-- Probe feature names through GetValue (unknown names return nil).
-- Result: '[A] Auto collect' and '[A] Farm: Break delay' exist in this build.
local candidates = {
  '[A] Farm: Break delay',
  '[A] Auto collect', '[A] Farm: Auto collect', '[A] Farm: Collect', '[A] Collect',
  '[A] Pickup', '[A] Farm: Pickup', '[M] Auto collect', '[A] Gem collect',
  '[A] Farm: Auto pickup', '[A] Auto pickup', '[A] Vacuum', '[A] Magnet',
}
local out = {}
for _, k in ipairs(candidates) do
  local ok, v = pcall(GetValue, k)
  out[#out + 1] = k .. ' => ' .. (ok and tostring(v) or ('ERROR ' .. tostring(v)))
end
return out
