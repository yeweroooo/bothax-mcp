# GetInventory() -> Inventory[]

Returns the player's inventory. One entry per slot, so the same item can appear in several
slots; sum `amount` when you need a total.

Returns
- `Inventory[]`: each entry has `id`, `amount`, and `flags`.

Example (Lua)
```lua
for _, item in pairs(GetInventory()) do
  LogToConsole('item id '.. item.id ..', amount '.. item.amount ..', flags '.. item.flags)
end
```

Related
- [Inventory](../structures/Inventory.md)
