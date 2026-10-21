# GetItemByName(name: string) -> ItemInfo

Looks an item up by exact name. Matching is case sensitive, so use
`GetItemsByPartialName` when you only know part of the name.

Parameters
- `name: string`: item name.

Returns
- `ItemInfo`

Example (Lua)
```lua
LogToConsole(GetItemByName('Dirt').id)
```

Related
- [ItemInfo](../structures/ItemInfo.md)
- [GetItemsByPartialName](GetItemsByPartialName.md)
