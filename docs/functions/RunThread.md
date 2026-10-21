# RunThread(callback: function, ...)

Runs a function on its own thread, so long work does not block the main one. Do not touch
the UI from inside it; hand results back with `RunDelayed` if you have to.

Parameters
- `callback: function`: function to run.
- `...: any`: extra arguments, optional.

Returns
- Nothing.

Example (Lua)
```lua
RunThread(function(id)
  LogToConsole('running thread for id : ' .. id)
  Sleep(2000)
  LogToConsole('finished thread for id : ' .. id)
end, 1)
```

Related
- [RunDelayed](RunDelayed.md)
- [Sleep](Sleep.md)
