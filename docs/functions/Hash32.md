# Hash32(text: string[, seed: uint32]) -> number

Returns a 32-bit FNV-1a hash. Not cryptographic; good for cache keys, quick tagging, and
light checksums. `seed` shifts the result deterministically.

Parameters
- `text: string`: input string.
- `seed: uint32 (optional)`: extra seed.

Returns
- `number`: 32-bit hash.

Example (Lua)
```lua
local h = Hash32('bothax')
LogToConsole('hash : ' .. tostring(h))
local hs = Hash32('bothax', 12345)
LogToConsole('hash with seed : ' .. tostring(hs))
```
