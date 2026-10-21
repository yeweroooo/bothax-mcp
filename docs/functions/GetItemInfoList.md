# GetItemInfoList() -> ItemInfo[]

Returns the whole item database. The list is large, so filter while iterating instead of
building extra copies.

Returns
- `ItemInfo[]`

Example (Lua)
```lua
for _, item in pairs(GetItemInfoList()) do
  if item.id == 2 then
    LogToConsole('Rarity ' .. item.name .. ' => ' .. item.rarity)
  end
end
```

Related
- [ItemInfo](../structures/ItemInfo.md)
