# GetItemByName(name: string) -> ItemInfo

Mengambil data item berdasarkan nama. Nama pencarian sensitif pada ejaan. Jika ingin pencarian bebas sebagian, gunakan `GetItemsByPartialName`.

Parameter
- `name: string`: Nama item.

Nilai kembali
- `ItemInfo`

Contoh (Lua)
```lua
LogToConsole(GetItemByName('Dirt').id)
```

Terkait
- [ItemInfo](../structures/ItemInfo.md)
- [GetItemInfo](GetItemInfo.md)
