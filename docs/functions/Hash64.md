# Hash64(text: string[, seed: uint64]) -> number

Returns a 64-bit FNV-1a hash. Same idea as `Hash32` with a wider space, which lowers
collision odds on large datasets.

Parameters
- `text: string`: input string.
- `seed: uint64 (optional)`: extra seed.

Returns
- `number`: 64-bit hash.

Example (Lua)
```lua
local h = Hash64('bothax')
LogToConsole('hash64 : ' .. tostring(h))
local hs = Hash64('bothax', 987654321)
LogToConsole('hash64 with seed : ' .. tostring(hs))
```
