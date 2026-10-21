# SendPacketRaw(to_client: boolean, packet: GameUpdatePacket)

Ringkasan
- `SendPacketRaw(to_client: boolean, packet: GameUpdatePacket)`
- Mengirim paket raw ke klien (`true`) atau server (`false`).

Penjelasan
- Pastikan struktur `packet` sesuai dengan format `GameUpdatePacket`. Penggunaan yang salah dapat memicu disconnect.

Parameter
- `to_client: boolean` — `true` ke klien, `false` ke server.
- `packet: GameUpdatePacket` — Data paket terstruktur.

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
local packet = { type = 10, value = 1796 }
SendPacketRaw(false, packet)
```

Terkait
- [GameUpdatePacket](../structures/GameUpdatePacket.md)
