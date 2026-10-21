# GetInventory() -> Inventory[]

Ringkasan
- `GetInventory() -> Inventory[]`
- Mengambil daftar item di inventaris pemain.

Penjelasan
- Cocok untuk mengecek kepemilikan item tertentu atau membuat statistik inventaris.

Nilai kembali
- Array `Inventory` — setiap entri berisi `id`, `amount`, `flags`.

Contoh (Lua)
```lua
for _, item in pairs(GetInventory()) do
  LogToConsole('item id '.. item.id ..', amount '.. item.amount ..', flags '.. item.flags)
end
```

Terkait
- [Inventory](../structures/Inventory.md)
