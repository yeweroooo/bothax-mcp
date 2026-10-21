# HttpResponse (status:int, error:boolean, method:string, content:string)

The result of a `MakeRequest` call. This build reports `status = 0` for a successful
request, so check `error` and `content` rather than the status code.

Fields
- `status: int`: HTTP status, when the build reports one.
- `error: boolean`: whether the request failed.
- `method: string`: method used, GET or POST.
- `content: string`: response body.

Example (Lua)
```lua
local res = MakeRequest('https://growtopiagame.com/detail', 'GET')
if not res.error and res.content then
  LogToConsole('content length: ' .. #res.content)
end
```

Related
- [MakeRequest](../functions/MakeRequest.md)
