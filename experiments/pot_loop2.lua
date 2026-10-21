-- Place and break loop with self-heal inside RunThread.
-- Result: 245 Pot O' Gems used up, gems 3,867 -> 13,901, avatar did not move.
local ITEM = 16706
local TX, TY = 72, 24
local function inv(id)
  local n = 0
  for _, it in pairs(GetInventory()) do
    if tonumber(it.id) == id then n = n + (tonumber(it.amount) or 0) end
  end
  return n
end
local function fg()
  local t = GetTile(TX, TY)
  if t == nil then return -1 end
  return tonumber(t.fg) or 0
end
local function punch(n)
  local p = GetLocal().pos
  for _ = 1, n do
    SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = 18,
      x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = TX, py = TY, extrasize = 0})
    _POTLOOP.hits = _POTLOOP.hits + 1
    Sleep(300)
  end
end
if type(_POTLOOP) == 'table' and _POTLOOP.active then
  return 'ALREADY_RUNNING cycles=' .. tostring(_POTLOOP.cycles)
end
ChangeValue('[A] Auto collect', true)
_POTLOOP = {
  active = true, finished = false, cycles = 0, hits = 0, recovered = 0,
  start_inv = inv(ITEM), inv_now = inv(ITEM), started = GetTick(), note = '',
}
RunThread(function()
  while _POTLOOP and not _POTLOOP.stop do
    local n = inv(ITEM)
    _POTLOOP.inv_now = n
    if n <= 0 then break end
    -- self-heal: clear whatever still sits on the tile before the next cycle
    if fg() ~= 0 then
      _POTLOOP.recovered = _POTLOOP.recovered + 1
      _POTLOOP.note = 'recovering: tile fg=' .. tostring(fg())
      punch(12)
      Sleep(200)
    else
      local p = GetLocal().pos
      SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = ITEM,
        x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = TX, py = TY, extrasize = 0})
      Sleep(320)
      if fg() ~= ITEM then
        _POTLOOP.note = 'place failed fg=' .. tostring(fg())
        Sleep(200)
      else
        local hits = 0
        while hits < 12 and fg() == ITEM do
          punch(1)
          hits = hits + 1
        end
        if fg() == ITEM then
          _POTLOOP.note = 'block did not break after ' .. hits .. ' hits'
        else
          _POTLOOP.cycles = _POTLOOP.cycles + 1
          _POTLOOP.note = ''
        end
        Sleep(200)
      end
    end
  end
  _POTLOOP.active = false
  _POTLOOP.finished = true
  _POTLOOP.inv_now = inv(ITEM)
end)
return 'START start_inv=' .. tostring(_POTLOOP.start_inv)
