# Hash32(text: string[, seed: uint32]) -> number

Ringkasan
- `Hash32(text: string[, seed: uint32]) -> number`
- Menghasilkan hash FNV-1a 32-bit.

Penjelasan
- Hash non-kriptografis; cocok untuk pembuatan kunci cache, penandaan cepat, atau checksum ringan. Gunakan `seed` untuk variasi deterministik.

Parameter
- `text: string` — Input string.
- `seed: uint32 (opsional)` — Seed tambahan.

Nilai kembali
- `number` — Nilai hash 32-bit.

Contoh (Lua)
```lua
local h = Hash32('bothax')
LogToConsole('Hash : ' .. tostring(h))
local hs = Hash32('bothax', 12345)
LogToConsole('Hash w/seed : ' .. tostring(hs))
```
