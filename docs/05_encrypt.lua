-- Encrypt & Load encrypted script

local enc = Encrypt("LogToConsole('hello world!')")
LoadEncrypt(enc)

EncryptFile('script.lua')
-- Jika ingin, bisa pakai kunci
EncryptFile('script.lua', 123)
-- Jalankan file terenkripsi
LoadEncryptedFile('script.lua')

