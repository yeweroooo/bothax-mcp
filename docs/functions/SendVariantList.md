# SendVariantList(var: VariantList[, netid: int][, delay: int])

Sends a VariantList. Index `[0]` holds the event name, for example `OnTextOverlay`, and the
following indexes are its arguments.

Parameters
- `var: VariantList`: the variant, a numeric table indexed from 0.
- `netid: int (optional)`: target net id.
- `delay: int (optional)`: send delay in milliseconds.

Returns
- Nothing.

Example (Lua)
```lua
SendVariantList({
  [0] = 'OnTextOverlay',
  [1] = 'BothaxYT!'
}, -1, 1000)
```
