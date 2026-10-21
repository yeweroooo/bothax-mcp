# AddHook(event: string, label: int|string, callback: function)

Ringkasan
- `AddHook(event: string, label: int|string, callback: function)`
- Mendaftarkan callback untuk sebuah event BothaxHook.

Penjelasan
- Lengkapi `label` unik agar mudah dihapus dengan `RemoveHook`. Kembalikan `true` di callback untuk memblokir event tertentu.

Parameter
- `event: string` — Nama event, mis. `OnVariant`, `OnSendPacket`, dll.
- `label: int|string` — Label/ID hook (dipakai untuk `RemoveHook`).
- `callback: function` — Fungsi yang dipanggil saat event terjadi.

Nilai kembali
- Tidak mengembalikan nilai. Identitas hook ditentukan dari `label` yang Anda berikan.

Catatan
- Mengembalikan `true` di callback biasanya akan memblokir/menelan event.

Contoh (Lua)
```lua
AddHook('OnSendPacket', 101, function(type, text)
  if text:find('/hi') then
    LogToConsole('Halo!')
    return true
  end
end)
```

Terkait
- [BothaxHook](BothaxHook.md)
- [RemoveHook](RemoveHook.md) / [RemoveHooks](RemoveHooks.md)
