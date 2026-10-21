# Encrypt(text: string[, key: int]) -> string

Encrypts text into an encrypted string. Handy for hiding script bodies or sensitive
strings before you embed or send them.

Parameters
- `text: string`: the text to encrypt.
- `key: int (optional)`: encryption key.

Returns
- `string`: the encrypted text.

Example (Lua)
```lua
local secret = Encrypt('hello there')
LogToConsole(secret)

local withKey = Encrypt('hello there', 123)
LogToConsole(withKey)
```

Related
- [LoadEncrypt](LoadEncrypt.md)
- [EncryptFile](EncryptFile.md)
