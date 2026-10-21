# RunThread(callback: function, ...)

Ringkasan
- `RunThread(callback: function, ...)`
- Menjalankan fungsi secara asynchronous (thread terpisah), tidak memblokir thread utama.

Penjelasan
- Hindari operasi UI langsung di thread terpisah. Gunakan untuk tugas I/O, perhitungan, atau loop yang lama.

Parameter
- `callback: function` — Fungsi yang dieksekusi di thread baru.
- `...: any` — Argumen tambahan (opsional).

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
RunThread(function(id)
  LogToConsole('Running Thread For ID : ' .. id)
  Sleep(2000)
  LogToConsole('Finished Thread For ID : ' .. id)
end, 1)
```
