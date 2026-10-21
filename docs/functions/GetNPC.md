# GetNPC(id: int) -> ClientNPC | nil

Mengambil NPC tertentu berdasarkan ID. Kembalikan `nil` jika ID tidak valid atau NPC tidak ada di world saat ini.

Parameter
- `id: int`: ID NPC.

Nilai kembali
- `ClientNPC` jika ditemukan, jika tidak maka `nil`.

Contoh (Lua)
```lua
local npc = GetNPC(1)
if npc then
  LogToConsole('NPC tipe => ' .. npc.type)
else
  LogToConsole('Not Found!')
end
```

Terkait
- [ClientNPC](../structures/ClientNPC.md)
- [GetNPCList](GetNPCList.md)
