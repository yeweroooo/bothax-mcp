# GetItemsByPartialName(partial: string) -> ItemInfo[]

Searches items by a name fragment, case insensitive. Built for search boxes and
auto-complete where the full name is unknown.

Parameters
- `partial: string`: part of an item name.

Returns
- `ItemInfo[]`

Example (Lua)
```lua
local items = GetItemsByPartialName('Dirt')
for _, it in pairs(items) do
  LogToConsole('item id => ' .. it.id)
end
```

Related
- [ItemInfo](../structures/ItemInfo.md)
