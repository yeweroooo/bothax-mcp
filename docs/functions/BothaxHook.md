# BothaxHook (Event)

Deskripsi singkat
- Kumpulan nama event yang bisa di-hook dengan `AddHook` untuk menangkap/periksa/override perilaku.

Penjelasan
- Pakai bersama `AddHook` untuk memasang listener. Kembalikan `true` dari callback bila ingin memblokir event tertentu.

Daftar event & parameter callback
- `OnVariant(var, netid, delay)` — Varian event teks/game (misal OnDialogRequest).
- `OnSendPacket(type, packet)` — Packet teks sebelum terkirim.
- `OnSendPacketRaw(packet)` — `GameUpdatePacket` sebelum terkirim.
- `OnProcessTankUpdate(packet)` — Paket update diproses klien.
- `OnWorldTouch(pos, start)` — Sentuhan/tap pada world (pos pixel), `start: boolean`.
- `OnDraw(deltatime)` — Frame render; gunakan untuk UI (ImGui).
- `OnInput(key)` — Windows-only; key code ditekan.

Contoh penggunaan (Lua)
```lua
AddHook('OnVariant', 'block_dialog', function(var)
  if var[0] == 'OnDialogRequest' then
    LogToConsole('Dialog diblokir')
    return true -- kembalikan true untuk memblokir
  end
end)
```

Terkait
- [AddHook](AddHook.md)
- [RemoveHook](RemoveHook.md) / [RemoveHooks](RemoveHooks.md)
