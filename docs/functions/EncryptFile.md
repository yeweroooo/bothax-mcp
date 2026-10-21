# EncryptFile

Ringkasan
- `EncryptFile(filename: string[, key: int])`
- Mengenkripsi file dari folder script. Hasil disimpan sebagai `(filename)_enc`.

Penjelasan
- Gunakan untuk mengamankan isi script sebelum dibagikan. File hasil dapat dieksekusi dengan `LoadEncryptedFile`.

Parameter
- `filename: string` — Nama file di folder script.
- `key: int (opsional)` — Kunci enkripsi.

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
EncryptFile('script.lua')
EncryptFile('script.lua', 123)
```

Terkait
- [LoadEncryptedFile](LoadEncryptedFile.md)
- [Encrypt](Encrypt.md)
