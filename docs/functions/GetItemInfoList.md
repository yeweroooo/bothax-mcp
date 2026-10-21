# GetItemInfoList() -> ItemInfo[]

Ringkasan
- `GetItemInfoList() -> ItemInfo[]`
- Mengambil seluruh daftar item dari database item.

Penjelasan
- Daftar bisa sangat besar. Filter dengan kondisi agar lebih efisien.

Nilai kembali
- Array `ItemInfo`

Contoh (Lua)
```lua
for _, item in pairs(GetItemInfoList()) do
  if item.id == 2 then
    LogToConsole('Rarity ' .. GetItemInfo(2).name .. ' => ' .. item.rarity)
  end
end
```

Terkait
- [ItemInfo](../structures/ItemInfo.md)
