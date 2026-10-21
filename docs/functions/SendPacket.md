# SendPacket(type: int, packet: string)

Ringkasan
- `SendPacket(type: int, packet: string)`
- Mengirim paket teks ke server.

Penjelasan
- Umumnya tipe `2` untuk teks/aksi (mis. `action|respawn`), tipe `3` untuk paket game tertentu (tergantung implementasi). Isi harus mengikuti protokol yang diharapkan server.

Parameter
- `type: int` — Tipe paket (mis. 2/3 umum dipakai).
- `packet: string` — Isi paket teks.

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
SendPacket(2, 'action|respawn')
```
