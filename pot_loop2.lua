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
if type(_POTLOOP) == 'table' and _POTLOOP.aktif then
  return 'SUDAH_JALAN siklus=' .. tostring(_POTLOOP.siklus)
end
ChangeValue('[A] Auto collect', true)
_POTLOOP = {
  aktif = true, selesai = false, siklus = 0, hits = 0, pulih = 0,
  awal = inv(ITEM), sekarang = inv(ITEM), mulai = GetTick(), catatan = '',
}
RunThread(function()
  while _POTLOOP and not _POTLOOP.stop do
    local n = inv(ITEM)
    _POTLOOP.sekarang = n
    if n <= 0 then break end
    -- pemulihan: kalau tile masih berisi sesuatu, habiskan dulu
    if fg() ~= 0 then
      _POTLOOP.pulih = _POTLOOP.pulih + 1
      _POTLOOP.catatan = 'pulih: tile fg=' .. tostring(fg())
      punch(12)
      Sleep(200)
    else
      local p = GetLocal().pos
      SendPacketRaw(false, {type = 3, netid = 0, snetid = 0, state = 0, value = ITEM,
        x = p.x, y = p.y, xspeed = 0, yspeed = 0, px = TX, py = TY, extrasize = 0})
      Sleep(320)
      if fg() ~= ITEM then
        _POTLOOP.catatan = 'place gagal fg=' .. tostring(fg())
        Sleep(200)
      else
        local hits = 0
        while hits < 12 and fg() == ITEM do
          punch(1)
          hits = hits + 1
        end
        if fg() == ITEM then
          _POTLOOP.catatan = 'blok tidak hancur setelah ' .. hits .. ' hit'
        else
          _POTLOOP.siklus = _POTLOOP.siklus + 1
          _POTLOOP.catatan = ''
        end
        Sleep(200)
      end
    end
  end
  _POTLOOP.aktif = false
  _POTLOOP.selesai = true
  _POTLOOP.sekarang = inv(ITEM)
end)
return 'MULAI ulang awal=' .. tostring(_POTLOOP.awal)
