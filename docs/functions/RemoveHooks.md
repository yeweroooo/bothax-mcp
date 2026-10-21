# RemoveHooks

Ringkasan
- `RemoveHooks()`
- Menghapus semua hook yang terdaftar.

Penjelasan
- Berguna untuk reset cepat saat pengembangan atau ketika ingin menonaktifkan semua event listener.

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
AddHook('OnSendPacket', 1, function(_, s) LogToConsole(s) end)
AddHook('OnSendPacketRaw', '1', function(p) LogToConsole(p.type) end)
RemoveHooks()
```

Terkait
- [RemoveHook](RemoveHook.md)
- [AddHook](AddHook.md)
