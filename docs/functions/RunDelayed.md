# RunDelayed(milliseconds: int, callback: function, ...)

Calls a function after a delay without blocking the current thread. Extra arguments are
passed through to the callback.

Parameters
- `milliseconds: int`: delay.
- `callback: function`: function to call.
- `...: any`: extra arguments, optional.

Returns
- Nothing.

Example (Lua)
```lua
RunDelayed(1000, function(name)
  LogToConsole('this is ' .. name .. '!')
end, 'Bothax')
```
