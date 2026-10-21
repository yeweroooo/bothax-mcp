# Sleep(milliseconds: int)

Ringkasan
- `Sleep(milliseconds: int)`
- Menghentikan eksekusi thread saat ini sementara (blocking) selama ms.

Penjelasan
- Bersifat blocking pada thread berjalan. Jangan dipakai di callback yang sensitif frame (mis. `OnDraw`), gunakan `RunDelayed`/`RunThread` bila perlu non-blocking.

Parameter
- `milliseconds: int`

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
LogToConsole('Hai')
Sleep(1000)
LogToConsole('Hai Juga')
```
