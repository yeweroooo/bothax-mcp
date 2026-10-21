# EncryptFile(filename: string[, key: int])

Encrypts a file from the script folder. The result is written next to it with an `_enc`
suffix, and runs through `LoadEncryptedFile`. Useful for handing a script to someone
without exposing its source.

Parameters
- `filename: string`: file name inside the script folder.
- `key: int (optional)`: encryption key.

Returns
- Nothing.

Example (Lua)
```lua
EncryptFile('script.lua')
EncryptFile('script.lua', 123)
```

Related
- [LoadEncryptedFile](LoadEncryptedFile.md)
- [Encrypt](Encrypt.md)
