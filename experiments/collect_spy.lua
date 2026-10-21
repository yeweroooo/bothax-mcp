-- Two-way packet spy, used to hunt the "collect" packet.
-- Run once from the executor; it stops itself after 120 seconds.
-- Output: /sdcard/Android/media/com.rtsoft.growtopia/spy_<epoch>.txt
local DIR = '/sdcard/Android/media/com.rtsoft.growtopia/'
local path = DIR .. 'spy_' .. tostring(os.time()) .. '.txt'
local f = io.open(path, 'w')
local n, MAX = 0, 5000

local function w(s)
  if not f or n >= MAX then return end
  n = n + 1
  f:write(tostring(os.time()) .. ' ' .. s .. '\n')
  f:flush()
end

local function pk(p)
  return string.format(
    'type=%s state=%s value=%s netid=%s snetid=%s x=%s y=%s px=%s py=%s extra=%s',
    tostring(p.type), tostring(p.state), tostring(p.value), tostring(p.netid),
    tostring(p.snetid), tostring(p.x), tostring(p.y), tostring(p.px), tostring(p.py),
    tostring(p.extrasize))
end

AddHook('OnSendPacketRaw', 9001, function(p)
  pcall(function() w('SEND ' .. pk(p)) end)
end)
AddHook('OnProcessTankUpdate', 9002, function(p)
  pcall(function() w('RECV ' .. pk(p)) end)
end)
AddHook('OnVariant', 9003, function(v, netid, delay)
  pcall(function()
    local head = (type(v) == 'table' and tostring(v[0])) or tostring(v)
    w('VAR ' .. head .. ' netid=' .. tostring(netid) .. ' delay=' .. tostring(delay))
  end)
end)

AddHook('OnWorldTouch', 9004, function(pos, start)
  pcall(function()
    w(string.format('TOUCH x=%s y=%s start=%s', tostring(pos and pos.x), tostring(pos and pos.y),
      tostring(start)))
  end)
end)

RunThread(function()
  local t0 = os.time()
  while os.time() - t0 < 120 do
    local nobj, gems = 0, '?'
    for _ in pairs(GetObjectList()) do nobj = nobj + 1 end
    local ok, pi = pcall(GetPlayerInfo)
    if ok and type(pi) == 'table' then gems = tostring(pi.gems) end
    pcall(function() w('TICK objs=' .. nobj .. ' gems=' .. gems) end)
    Sleep(400)
  end
  if f then f:close() end
end)

return 'spy active for 120s: ' .. path
