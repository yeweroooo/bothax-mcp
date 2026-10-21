-- Drop, then pick up with a type=11 packet carrying the object oid.
-- Result: object gone from the ground, inventory back to its old size.
local id = (type(DROP_ID) == 'number') and DROP_ID or 5026

local function inv(i)
  local n = 0
  for _, it in pairs(GetInventory()) do
    if it.id == i then n = n + it.amount end
  end
  return n
end

local function objs()
  local n, hit = 0, nil
  for _, o in pairs(GetObjectList()) do
    n = n + 1
    if o.id == id and not hit then hit = o end
  end
  return n, hit
end

local before = inv(id)
local log = {}

SendPacket(2, "action|drop\n|itemID|" .. id .. "\n")
Sleep(1200)
local n1, found = objs()
log[#log + 1] = string.format("drop(id=%d) inv %d->%d objs=%d found=%s",
  id, before, inv(id), n1, tostring(found ~= nil))

if not found then
  return table.concat(log, " | ") .. " || the server rejected the drop"
end

local oid, px, py = found.oid, found.pos.x, found.pos.y
local p = GetLocal().pos
SendPacketRaw(false, {type = 11, state = 0, value = oid, px = px, py = py, x = p.x, y = p.y})
Sleep(1500)
log[#log + 1] = string.format("TYPE11 oid=%s pos=%.0f,%.0f -> inv %d, objs %d",
  tostring(oid), px, py, inv(id), (objs()))
return table.concat(log, " | ")
