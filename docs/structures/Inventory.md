# Inventory (id:int, amount:int, flags:int)

One inventory slot. The same item id can appear in several slots, so sum `amount` when you
need the total a player owns.

Fields
- `id: int`: item id.
- `amount: int`: quantity in this slot.
- `flags: int`: slot flags.

Example (Lua)
```lua
for _, it in pairs(GetInventory()) do
  LogToConsole(('item %d amount %d'):format(it.id, it.amount))
end
```

Related
- [GetInventory](../functions/GetInventory.md)
