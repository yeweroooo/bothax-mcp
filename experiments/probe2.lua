-- cari nama global API yang benar-benar tersedia.
-- Tidak memakai io, tidak mengandalkan MakeRequest.
local function t(name)
  local ok, v = pcall(function() return _G[name] end)
  return name .. "=" .. (ok and type(v) or "ERR")
end

LogToConsole("[p2] " .. table.concat({
  t("MakeRequest"), t("SendPacket"), t("LogToConsole"), t("GetLocal"),
  t("RunThread"), t("GetTick"), t("GetWorld"), t("AddHook"),
}, " "))

-- tabel yang mungkin membungkus API
local tnames = {}
for _, n in ipairs({ "game", "gt", "api", "mod", "bothax", "Native", "http", "net", "socket", "curl", "Http" }) do
  local ok, v = pcall(function() return _G[n] end)
  if ok and type(v) == "table" then
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = tostring(k) end
    table.sort(keys)
    LogToConsole("[p2] table " .. n .. " (" .. #keys .. "): " .. table.concat(keys, ",", 1, math.min(#keys, 12)))
    tnames[#tnames + 1] = n
  end
end
if #tnames == 0 then LogToConsole("[p2] tidak ada tabel API global") end

-- global fungsi yang mengandung kata kunci menarik
local hits = {}
for k, v in pairs(_G) do
  if type(v) == "function" then
    local ks = tostring(k)
    if ks:find("equest") or ks:find("ttp") or ks:find("Send") or ks:find("Url") or ks:find("URL") then
      hits[#hits + 1] = ks
    end
  end
end
table.sort(hits)
LogToConsole("[p2] fungsi cocok (" .. #hits .. "): " .. table.concat(hits, " ", 1, math.min(#hits, 20)))
