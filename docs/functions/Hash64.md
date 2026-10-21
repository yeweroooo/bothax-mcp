# Hash64(text: string[, seed: uint64]) -> number

Ringkasan
- `Hash64(text: string[, seed: uint64]) -> number`
- Menghasilkan hash FNV-1a 64-bit.

Penjelasan
- Sama seperti `Hash32` namun dengan ruang nilai lebih besar (64-bit), cocok untuk mengurangi kemungkinan tabrakan pada dataset besar.

Parameter
- `text: string`
- `seed: uint64 (opsional)`

Nilai kembali
- `number` — Nilai hash 64-bit.

Contoh (Lua)
```lua
local h = Hash64('bothax')
LogToConsole('hash64 : ' .. tostring(h))
local hs = Hash64('bothax', 987654321)
LogToConsole('hash64 w/seed : ' .. tostring(hs))
```
