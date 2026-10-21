# LoadEncrypt(encryptedText: string)

Runs encrypted text as a Lua script. The partner of `Encrypt`, which lets you ship code
without exposing its source.

Parameters
- `encryptedText: string`: encrypted script text.

Returns
- Nothing; the script runs inside the call.

Example (Lua)
```lua
local script = Encrypt("LogToConsole('hello world!')")
LoadEncrypt(script)
```

Related
- [Encrypt](Encrypt.md)
- [LoadEncryptedFile](LoadEncryptedFile.md)
