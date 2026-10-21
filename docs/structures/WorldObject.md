# WorldObject (id:int, pos:Vec2, amount:int, oid:int)

An object lying in the world, which is what a drop looks like to the client. `id` is the item
id and `amount` the quantity inside that one object, so one object can carry several units.

`oid` identifies the object itself, and it is what a collect packet needs.

Fields
- `id: int`: item id.
- `pos: Vec2`: position in pixels.
- `amount: int`: quantity.
- `flags: int`: object flags.
- `oid: int`: unique object id.

Example (Lua)
```lua
for _, obj in pairs(GetObjectList()) do
  if obj.id == 242 then
    LogToConsole(('lock at (%d,%d), amount %d')
      :format(obj.pos.x // 32, obj.pos.y // 32, obj.amount))
  end
end
```

Related
- [GetObjectList](../functions/GetObjectList.md)
