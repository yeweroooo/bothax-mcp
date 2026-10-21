# ItemInfo (id:int, name:string, rarity:int, type:int, flags:int)

A full record from the item database. `breakhit` is the number of punches a block takes,
which is what a break loop should count to.

Fields
- `id: int`: item id.
- `name: string`: item name.
- `filename: string`: asset name.
- `rarity: int`: rarity.
- `breakhit: int`: hits needed to break the block.
- `growtime: int`: grow time for seeds and trees.
- `type: int`: item type.
- `coltype: int`: collision type.
- `clothingtype: int`: clothing type, for wearables.
- `visualstyle: int`: visual style.
- `texturex: int`: texture X.
- `texturey: int`: texture Y.
- `flags: int`: item flags.

Example (Lua)
```lua
local info = GetItemInfo('World Lock')
LogToConsole(('id %d, rarity %d'):format(info.id, info.rarity))
```

Related
- [GetItemInfo](../functions/GetItemInfo.md)
- [GetItemByIDSafe](../functions/GetItemByIDSafe.md)
- [GetItemByName](../functions/GetItemByName.md)
- [GetItemInfoList](../functions/GetItemInfoList.md)
