# GameUpdatePacket (struct paket raw)

Deskripsi singkat
- Struktur paket mentah yang digunakan untuk event/pengiriman paket level rendah.
- Banyak bidang memiliki alias/nama alternatif tergantung konteks.

Penjelasan
- Gunakan dengan hati-hati. Pastikan field yang dipakai sesuai tipe event agar tidak menimbulkan perilaku tak terduga.

Bidang (sesuai README)
- `type: int`
- `dropped: int`
- `netid | player_flags: int`
- `snetid | secondnetid: int`
- `state | characterstate: int`
- `value | int_data: int`
- `x | pos_x: float`
- `xspeed: float`
- `yspeed: float`
- `px | tx | int_x: int`
- `py | ty | int_y: int`
- `padding1: int`
- `padding2: int`
- `padding4: float`
- `extrasize: int`

Contoh penggunaan (Lua)
```lua
-- Mengirim paket raw (contoh sederhana)
local pkt = { type = 10, value = 1796 }
SendPacketRaw(false, pkt)
```

Terkait
- [SendPacketRaw](../functions/SendPacketRaw.md)
