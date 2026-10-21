# LoadEncrypt(encryptedText: string)

Menjalankan teks terenkripsi sebagai script Lua. Pasangan dari `Encrypt`. Memungkinkan mengeksekusi script tanpa mengekspose isi asli.

Parameter
- `encryptedText: string`: String terenkripsi.

Nilai kembali
- Tidak ada (eksekusi terjadi di dalam fungsi).

Contoh (Lua)
```lua
local script = Encrypt("LogToConsole('hello world!')")
LoadEncrypt(script)
```

Terkait
- [Encrypt](Encrypt.md)
- [LoadEncryptedFile](LoadEncryptedFile.md)
