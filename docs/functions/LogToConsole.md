# LogToConsole(text: string)

Ringkasan
- `LogToConsole(text: string)`
- Menampilkan teks ke konsol in-game/console executor.

Penjelasan
- Mendukung teks biasa dan kode warna in-game (mis. menggunakan tanda backtick ` seperti `2 untuk warna tertentu sesuai konvensi game).
- Gunakan untuk debug, notifikasi singkat, atau menampilkan hasil operasi script.

Parameter
- `text: string` — Teks yang akan ditampilkan. Dapat berisi newline `\n`.

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
LogToConsole('Halo dunia!')
LogToConsole('`2Teks hijau`0 dan normal lagi')
```

Terkait
- [AddHook](AddHook.md)
- [MakeRequest](MakeRequest.md)

