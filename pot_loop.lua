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
if type(_POTLOOP) == 'table' and _POTLOOP.aktif then
  return 'SUDAH_JALAN siklus=' .. tostring(_POTLOOP.siklus)
end
ChangeValue('[A] Auto collect', true)
_POTLOOP = {
  aktif = true, selesai = false, siklus = 0, hits = 0, lewat = 0,
  awal = inv(ITEM), sekarang = inv(ITEM), mulai = GetTick(), catatan = '',
}
RunThread(function()
  while true do
    local n = inv(ITEM)
    _POTLOOP.sekarang = n
    if n <= 0 then break end
    if fg(TX, TY) ~= 0 then
      _POTLOOP.lewat = _POTLOOP.lewat + 1
      _POTLOOP.catatan = 'tile terisi fg=' .. tostring(fg(TX, TY))
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
        _POTLOOP.catatan = 'blok tidak hancur setelah ' .. hits .. ' hit'
      else
        _POTLOOP.siklus = _POTLOOP.siklus + 1
      end
      Sleep(200)
    end
  end
  _POTLOOP.aktif = false
  _POTLOOP.selesai = true
  _POTLOOP.sekarang = inv(ITEM)
end)
return 'MULAI awal=' .. tostring(_POTLOOP.awal)
