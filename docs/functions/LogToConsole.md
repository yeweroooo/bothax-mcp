# LogToConsole(text: string)

Writes to the in-game console. Supports the game's colour codes, which start with a
backtick, for example `` `2 `` for green and `` `0 `` to return to the default. Every line
also lands in the bridge log, so `debug_log()` shows it from outside the game.

Parameters
- `text: string`: text to print. Newlines `\n` are allowed.

Returns
- Nothing.

Example (Lua)
```lua
LogToConsole('hello world!')
LogToConsole('`2green text`0 and back to normal')
```

Related
- [AddHook](AddHook.md)
- [MakeRequest](MakeRequest.md)
