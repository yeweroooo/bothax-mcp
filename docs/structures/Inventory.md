# Inventory (id:int, amount:int, flags:int)

Deskripsi singkat
- Entri item di inventaris pemain.

Penjelasan
- Setiap entri mewakili 1 slot: `id` item dan `amount` jumlah item pada slot tersebut.

Bidang
- `id: int` — ID item.
- `amount: int` — Jumlah/quantity.
- `flags: int` — Flag item pada slot.

Contoh penggunaan (Lua)
```lua
for _, it in pairs(GetInventory()) do
  LogToConsole(('Item %d jumlah %d'):format(it.id, it.amount))
end
```

Terkait
- [GetInventory](../functions/GetInventory.md)
