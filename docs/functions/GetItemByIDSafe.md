# GetItemByIDSafe(itemid: int) -> ItemInfo

Ringkasan
- `GetItemByIDSafe(itemid: int) -> ItemInfo`
- Mengambil data item berdasarkan ID dengan aman dari database item.

Penjelasan
- Pilihan aman untuk ID yang valid; mengembalikan detail lengkap item.

Parameter
- `itemid: int` — ID item.

Nilai kembali
- `ItemInfo`

Contoh (Lua)
```lua
LogToConsole(GetItemByIDSafe(242).name)
```

Terkait
- [ItemInfo](../structures/ItemInfo.md)
- [GetItemInfo](GetItemInfo.md)
