# GetItemByIDSafe(itemid: int) -> ItemInfo

Looks an item up by id and returns the full record. Prefer it over `GetItemInfo` when you
already have a numeric id.

Parameters
- `itemid: int`: item id.

Returns
- `ItemInfo`

Example (Lua)
```lua
LogToConsole(GetItemByIDSafe(242).name)
```

Related
- [ItemInfo](../structures/ItemInfo.md)
- [GetItemInfo](GetItemInfo.md)
