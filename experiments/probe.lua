-- Check whether the executor really runs Lua.
-- Signal 1: write a file to /sdcard (no network needed).
-- Signal 2: one request to the bridge (exercises MakeRequest).
local out = {}

local function log(s)
  out[#out + 1] = tostring(s)
end

-- sinyal 1
local ok, err = pcall(function()
  local f = io.open("/sdcard/gtprobe.txt", "w")
  if f then
    f:write("executor hidup\n")
    f:close()
    log("file: ok")
  else
    log("file: io.open nil")
  end
end)
if not ok then log("file error: " .. tostring(err)) end

-- sinyal 2
local ok2, err2 = pcall(function()
  local r = MakeRequest("http://127.0.0.1:8770/health", "GET", nil, nil, 4000)
  if r then
    log("http: status=" .. tostring(r.status) .. " err=" .. tostring(r.error))
  else
    log("http: nil")
  end
end)
if not ok2 then log("http error: " .. tostring(err2)) end

-- tulis ringkasan
pcall(function()
  local f = io.open("/sdcard/gtprobe_result.txt", "w")
  if f then f:write(table.concat(out, "\n")); f:close() end
end)

LogToConsole("[probe] " .. table.concat(out, " | "))
