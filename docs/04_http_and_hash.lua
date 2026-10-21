-- HTTP & Hash examples

local res = MakeRequest('https://growtopiagame.com/detail', 'GET')
if not res.error and res.status == 200 then
  local online = tonumber(res.content:match('"online_user":"(%d+)"'))
  if online then LogToConsole('Online users: ' .. online) end
end

local h32 = Hash32('bothax', 123)
local h64 = Hash64('bothax', 987)
LogToConsole('h32=' .. tostring(h32) .. ' h64=' .. tostring(h64))

