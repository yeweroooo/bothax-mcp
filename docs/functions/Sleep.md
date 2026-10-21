# Sleep(milliseconds: int)

Pauses the current thread for the given time. It blocks, so never call it from a
frame-sensitive callback such as `OnDraw`; use `RunDelayed` or `RunThread` there.

Parameters
- `milliseconds: int`: how long to wait.

Returns
- Nothing.

Example (Lua)
```lua
LogToConsole('hi')
Sleep(1000)
LogToConsole('hi again')
```

Related
- [RunDelayed](RunDelayed.md)
- [RunThread](RunThread.md)
