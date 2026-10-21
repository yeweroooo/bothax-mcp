# ChangeValue(name: string, value: any)

Ringkasan
- `ChangeValue(name: string, value: any)`
- Mengubah/menyalakan/mematikan fitur berdasarkan nama.

Penjelasan
- Nama fitur mengikuti menu/fitur internal executor. Nilai bisa boolean, angka, atau warna hex (mis. `0xFFFFFFFF`). Jika nama tidak dikenal, tidak ada perubahan yang terjadi.

Parameter
- `name: string` — Nama fitur/setting.
- `value: any` — Nilai baru (boolean/number/string/hex).

Nilai kembali
- Tidak ada.

Contoh (Lua)
```lua
ChangeValue('[C] ModFly', true)
ChangeValue('[M] Network text color', 0xFFFFFFFF)
ChangeValue('[A] Farm: Break delay', 300)
```
