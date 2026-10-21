# Encrypt(text: string[, key: int]) -> string

Ringkasan
- `Encrypt(text: string[, key: int]) -> string`
- Mengenkripsi teks menjadi string terenkripsi.

Penjelasan
- Cocok untuk menyembunyikan isi script atau data sensitif sebelum dikirim/di-embed.

Parameter
- `text: string` — Teks yang akan dienkripsi.
- `key: int (opsional)` — Kunci enkripsi.

Nilai kembali
- `string` — Hasil teks terenkripsi.

Contoh (Lua)
```lua
local secret = Encrypt('assalamualaikum')
LogToConsole(secret)

local withKey = Encrypt('assalamualaikum', 123)
LogToConsole(withKey)
```

Terkait
- [LoadEncrypt](LoadEncrypt.md)
- [EncryptFile](EncryptFile.md)
