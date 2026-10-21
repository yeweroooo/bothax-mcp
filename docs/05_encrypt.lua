-- Encrypt text and run it, then encrypt a file from the script folder.

local enc = Encrypt("LogToConsole('hello world!')")
LoadEncrypt(enc)

EncryptFile('script.lua')        -- writes script.lua_enc
EncryptFile('script.lua', 123)   -- same, with a key
LoadEncryptedFile('script.lua_enc')
