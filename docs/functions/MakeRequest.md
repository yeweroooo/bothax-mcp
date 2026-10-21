# MakeRequest(url: string[, method: string][, headers: table][, content: string][, timeout_ms: int]) -> HttpResponse

Performs an HTTP request. Check `error` and `content` on the result before parsing; this
build returns `status = 0` for a successful request, so the numeric status is not a
reliable success signal.

`headers` is a key to value table, for example `{ ['Content-Type'] = 'text/plain' }`.
`content` is the body for `POST` and `PUT`.

Parameters
- `url: string`: target URL.
- `method: string (optional)`: defaults to `GET`.
- `headers: table (optional)`: HTTP headers.
- `content: string (optional)`: request body.
- `timeout_ms: int (optional)`: timeout in milliseconds.

Returns
- `HttpResponse`: status, error, method, content.

Example (Lua)
```lua
local res = MakeRequest('https://growtopiagame.com/detail', 'GET')
if not res.error and res.content then
  local online = tonumber(res.content:match('"online_user":"(%d+)"'))
  if online then LogToConsole('current users online : ' .. online) end
end
```

Related
- [HttpResponse](../structures/HttpResponse.md)
