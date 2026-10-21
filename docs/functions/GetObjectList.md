# GetObjectList() -> WorldObject[]

Returns the objects lying in the world, which is what drops look like from the client.
Each object carries an `oid`; that oid, not the item id, is what a collect packet needs.

Returns
- `WorldObject[]`

Example (Lua)
```lua
for _, obj in pairs(GetObjectList()) do
  if obj.id == 242 then
    LogToConsole(('world lock at (%d,%d), amount %d')
      :format(obj.pos.x // 32, obj.pos.y // 32, obj.amount))
  end
end
```

Related
- [WorldObject](../structures/WorldObject.md)
