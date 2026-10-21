# DungeonNPC (x:int, y:int, state:int, flags:int, flags2:int)

NPC data for dungeon areas, with its own state and flag fields. Not every world exposes it,
so treat a missing list as normal rather than as an error.

Fields
- `x: int`: tile X.
- `y: int`: tile Y.
- `state: int`: current state.
- `flags: int`: state bitmask.
- `flags2: int`: secondary bitmask.

Example (Lua)
```lua
-- Reading dungeon NPC state needs the function that exposes it in your executor
-- build; the fields above describe the table you get back.
```
