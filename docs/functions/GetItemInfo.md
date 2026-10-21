# GetItemInfo(item: int|string) -> ItemInfo

Mengambil data item berdasarkan ID atau nama. Lebih fleksibel karena menerima ID maupun nama. Cocok untuk lookup cepat sebelum menampilkan info item.

Parameter
- `item: int|string`: ID atau nama item.

Nilai kembali
- `ItemInfo`

Contoh (Lua)
```lua
LogToConsole(GetItemInfo(242).name)
LogToConsole(GetItemInfo('World Lock').id)
```

Terkait
- [ItemInfo](../structures/ItemInfo.md)
- [GetItemByIDSafe](GetItemByIDSafe.md)
- [GetItemByName](GetItemByName.md)
