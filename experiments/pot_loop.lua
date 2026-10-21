-- First place and break loop, without self-heal.
-- Result: it stalled once the tile was filled, 121 cycles skipped without action.
local ITEM = 16706
local TX, TY = 72, 24
local function inv(id)
  local n = 0
  for _, it in pairs(GetInventory()) do
    if tonumber(it.id) == id then n = n + (tonumber(it.amount) or 0) end
  end
  return n
end
local function fg(x, y)
  local t = GetTile(x, y)
  if t == nil then return -1 end
  return tonumber(t.fg) or 0
end
if type(_POTLOOP) == 'table' and _POTLOOP.active then
  return 'ALREADY_RUNNING cycles=' .. tostring(_POTLOOP.cycles)
end
ChangeValue('[A] Auto collect', true)
_POTLOOP = {
  active = true, finished = false, cycles = 0, hits = 0, skipped = 0,
  start_inv = inv(ITEM), inv_now = inv(ITEM), started = GetTick(), note = '',
}
RunThread(function()
  while true do
    local n = inv(ITEM)
    _POTLOOP.inv_now = n
    if n <= 0 then break end
    if fg(TX, TY) ~= 0 then
      _POTLOOP.skipped = _POTLOOP.skipped + 1
      _POTLOOP.note = 'tile occupied fg=' .. tostring(fg(TX, TY))
      Sleep(400)
    else
      local p = GetLocal().pos
      SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = ITEM,
        x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = TX, py = TY, extrasize = 0})
      Sleep(320)
      local hits = 0
      while hits < 10 and fg(TX, TY) == ITEM do
        SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = 18,
          x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = TX, py = TY, extrasize = 0})
        hits = hits + 1
        _POTLOOP.hits = _POTLOOP.hits + 1
        Sleep(300)
      end
      if fg(TX, TY) == ITEM then
        _POTLOOP.note = 'block did not break after ' .. hits .. ' hits'
      else
        _POTLOOP.cycles = _POTLOOP.cycles + 1
      end
      Sleep(200)
    end
  end
  _POTLOOP.active = false
  _POTLOOP.finished = true
  _POTLOOP.inv_now = inv(ITEM)
end)
return 'START start_inv=' .. tostring(_POTLOOP.start_inv)
