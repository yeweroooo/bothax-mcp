# GetItemInfo(item: int|string) -> ItemInfo

Looks an item up by id or by name. The flexible version of the two typed lookups.

Parameters
- `item: int|string`: item id or item name.

Returns
- `ItemInfo`

Example (Lua)
```lua
LogToConsole(GetItemInfo(242).name)
LogToConsole(GetItemInfo('World Lock').id)
```

Related
- [ItemInfo](../structures/ItemInfo.md)
- [GetItemByIDSafe](GetItemByIDSafe.md)
- [GetItemByName](GetItemByName.md)
