# SendVariantList(var: VariantList[, netid: int][, delay: int])

Ringkasan
- `SendVariantList(var: VariantList[, netid: int][, delay: int])`
- Mengirim VariantList.

Penjelasan
- Elemen `[0]` biasanya berisi nama event (mis. `OnTextOverlay`). Elemen berikutnya adalah argumen event. `netid` dan `delay` opsional sesuai kebutuhan.

Parameter
- `var: VariantList` — Isi varian (tabel numerik berindeks 0..n).
- `netid: int (opsional)` — NetID target.
- `delay: int (opsional)` — Delay pengiriman (ms).

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
SendVariantList({
  [0] = 'OnTextOverlay',
  [1] = 'BothaxYT!'
}, -1, 1000)
```
