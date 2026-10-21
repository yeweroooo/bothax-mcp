# GetNPCList() -> ClientNPC[]

Ringkasan
- `GetNPCList() -> ClientNPC[]`
- Mengambil daftar semua NPC aktif di world.

Penjelasan
- Gunakan untuk scanning posisi NPC, atau mendeteksi keberadaan tipe NPC tertentu.

Nilai kembali
- Array `ClientNPC`

Contoh (Lua)
```lua
for _, npc in pairs(GetNPCList()) do
  LogToConsole('Found NPC id: ' .. npc.id)
end
```

Terkait
- [ClientNPC](../structures/ClientNPC.md)
- [GetNPC](GetNPC.md)
