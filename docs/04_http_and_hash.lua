-- HTTP and hash examples.

local res = MakeRequest('https://growtopiagame.com/detail', 'GET')
-- This build reports status 0 on success, so judge by error and content.
if not res.error and res.content then
  local online = tonumber(res.content:match('"online_user":"(%d+)"'))
  if online then LogToConsole('users online: ' .. online) end
end

local h32 = Hash32('bothax', 123)
local h64 = Hash64('bothax', 987)
LogToConsole('h32=' .. tostring(h32) .. ' h64=' .. tostring(h64))
