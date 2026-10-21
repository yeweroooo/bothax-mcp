-- bridge.lua — kanal kontrol + log debug untuk gt-mcp
-- Taruh di: Android/media/com.rtsoft.growtopia/scripts/bridge.lua
-- Jalankan sekali dari menu executor BINTERNAL ("Execute RML Script").
--
-- Alur:
--   loop  : MakeRequest(BASE..'/poll')  -> "<id>|<kode lua>"
--   eksekusi kode, serialisasi hasil
--   kirim : MakeRequest(BASE..'/result', 'POST', body)
--
-- Debug dari dalam game:
--   _BRIDGE_LOG(n)   -> n entri log terakhir (perintah, hasil, error, LogToConsole)
--   _BRIDGE_STOP()   -> hentikan loop
--
-- BASE harus bisa dijangkau dari dalam game: pakai `adb reverse tcp:8770 tcp:8770`
-- supaya 127.0.0.1:8770 di perangkat mengarah ke MCP server di PC.

local BASE = 'http://127.0.0.1:8770'
local POLL_MS = 30000
local LOG_MAX = 300
local running = true

-- Penanda boot: dikirim ke server lewat /diag SEBELUM apa pun yang bisa gagal.
-- Tanpa ini, script yang mati di tengah jalan tidak meninggalkan jejak sama
-- sekali (konsol mod tidak terbaca dari luar), dan server hanya melihat diam.
local function _boot(msg)
  local q = tostring(msg):gsub('[^%w%-%._~ ]', function(c)
    return string.format('%%%02X', string.byte(c))
  end):gsub(' ', '%%20')
  pcall(MakeRequest, BASE .. '/diag?msg=' .. q, 'GET', nil, nil, 5000)
end

_boot('BOOT v2 mulai')

-- Probe sekali di awal: cetak ke konsol mod apa yang SEBENARNYA dikembalikan
-- MakeRequest untuk server lokal. Tanpa ini kegagalan jaringan hanya terlihat
-- sebagai "menunggu perintah" yang tidak menjelaskan apa pun.
local function _fmt_http(res, ok)
  if not ok then return 'pcall gagal: ' .. tostring(res) end
  if type(res) ~= 'table' then return 'bukan tabel: ' .. type(res) .. ' ' .. tostring(res) end
  return string.format('status=%s error=%s content(%s)=%s',
    tostring(res.status), tostring(res.error), type(res.content),
    tostring(res.content):sub(1, 40))
end

-------------------------------------------------------------------- log buffer

local LOG = {}

local function now_ms()
  local ok, t = pcall(GetTick)
  return ok and tonumber(t) or 0
end

local function log_add(tag, msg)
  local line = string.format('%s [%s] %s', tostring(now_ms()), tag, tostring(msg))
  LOG[#LOG + 1] = line
  if #LOG > LOG_MAX then table.remove(LOG, 1) end
  return line
end

-- Output konsol mod tetap jalan, tapi ikut terekam untuk dilihat dari MCP.
local orig_console = LogToConsole
local function blog(msg)
  log_add('bridge', msg)
  if orig_console then pcall(orig_console, msg) end
end

LogToConsole = function(s)
  log_add('console', s)
  if orig_console then pcall(orig_console, s) end
end

_BRIDGE_LOG = function(n)
  n = tonumber(n) or 40
  local out = {}
  local start = math.max(1, #LOG - n + 1)
  for i = start, #LOG do out[#out + 1] = LOG[i] end
  return out
end

_BRIDGE_STOP = function()
  running = false
end

--------------------------------------------------------------------- serialisasi

local function esc(s)
  return (s:gsub('\\', '\\\\'):gsub('\n', '\\n'):gsub('"', '\\"'))
end

local function enc(v, depth, seen)
  depth = depth or 0
  seen = seen or {}
  local t = type(v)
  if t == 'nil' then return 'nil' end
  if t == 'boolean' then return tostring(v) end
  if t == 'number' then
    if v ~= v then return 'nan' end
    return tostring(v)
  end
  if t == 'string' then return '"' .. esc(v) .. '"' end
  if t ~= 'table' then
    local ok, s = pcall(tostring, v)
    return ok and ('<' .. t .. ': ' .. tostring(s) .. '>') or ('<' .. t .. '>')
  end
  if depth >= 5 then return '{...}' end
  if seen[v] then return '<cycle>' end
  seen[v] = true

  local parts, n = {}, 0
  for k, val in pairs(v) do
    n = n + 1
    if n > 120 then parts[#parts + 1] = '...'; break end
    local key
    if type(k) == 'string' and k:match('^[%a_][%w_]*$') then
      key = k .. '='
    elseif type(k) == 'number' then
      key = '[' .. tostring(k) .. ']='
    elseif type(k) == 'string' then
      key = '["' .. esc(k) .. '"]='
    else
      key = '[' .. tostring(k) .. ']='
    end
    parts[#parts + 1] = key .. enc(val, depth + 1, seen)
  end
  seen[v] = nil
  return '{' .. table.concat(parts, ', ') .. '}'
end

----------------------------------------------------------------------- eksekusi

local function run_code(code)
  local chunk, cerr = load(code, '=mcp')
  if not chunk then return false, 'compile error: ' .. tostring(cerr) end
  local ok, res = pcall(chunk)
  if not ok then return false, 'runtime error: ' .. tostring(res) end
  return true, enc(res)
end

local function urlenc(s)
  return (tostring(s):gsub('[^%w%-%._~]', function(c)
    return string.format('%%%02X', string.byte(c))
  end))
end

local function ok_res(res)
  if type(res) ~= 'table' then return false end
  local er = res.error
  if er ~= nil and er ~= false and tostring(er) ~= '' and tostring(er) ~= 'false'
     and tostring(er) ~= 'nil' then
    return false
  end
  return true
end

local function post(path, body)
  local url = BASE .. path
  local last = '?'

  -- 1) POST tanpa header
  local ok1, res1 = pcall(MakeRequest, url, 'POST', nil, body, 15000)
  if ok1 and ok_res(res1) then return true, res1.status end
  last = tostring(not ok1 and res1 or (res1 and (res1.error or res1.status)) or 'nil')

  -- 2) POST dengan header
  local ok2, res2 = pcall(MakeRequest, url, 'POST',
    { ['Content-Type'] = 'text/plain' }, body, 15000)
  if ok2 and ok_res(res2) then return true, res2.status end
  last = tostring(not ok2 and res2 or (res2 and (res2.error or res2.status)) or 'nil')

  -- 3) GET query (cadangan; server melayani /result?id=&st=&d=)
  local id, st, data = tostring(body):match('^([^|]*)|([^|]*)|(.*)$')
  if id then
    local q = url .. '?id=' .. urlenc(id) .. '&st=' .. urlenc(st) .. '&d=' .. urlenc(data)
    local ok3, res3 = pcall(MakeRequest, q, 'GET', nil, nil, 15000)
    if ok3 and ok_res(res3) then return true, res3.status end
    last = tostring(not ok3 and res3 or (res3 and (res3.error or res3.status)) or 'nil')
  end

  LogToConsole('[bridge] kirim hasil gagal: ' .. last)
  return false, last
end

--------------------------------------------------------------------- traffic

-- Penangkap lalu lintas dalam game. Memakai hook yang sama dengan yang
-- didokumentasikan Bothax: OnSendPacket, OnSendPacketRaw, OnVariant,
-- OnProcessTankUpdate. Callback TIDAK mengembalikan true, jadi paket tetap
-- diteruskan (tidak memblokir apa pun).

_TRAFFIC = { on = false, max = 400, buf = {}, count = 0, dropped = 0 }

local function t_add(kind, detail)
  if not _TRAFFIC.on then return end
  local line = string.format('%s %-18s %s', tostring(now_ms()), kind, detail)
  if #_TRAFFIC.buf >= _TRAFFIC.max then
    table.remove(_TRAFFIC.buf, 1)
    _TRAFFIC.dropped = _TRAFFIC.dropped + 1
  end
  _TRAFFIC.buf[#_TRAFFIC.buf + 1] = line
  _TRAFFIC.count = _TRAFFIC.count + 1
end

local function pkt_str(p)
  if type(p) ~= 'table' then return tostring(p) end
  return string.format('type=%-3s state=%-5s x=%-8.2f y=%-8.2f value=%-6s netid=%-8s px=%-5s py=%-5s extra=%s',
    tostring(p.type or p.eventtype),
    tostring(p.state or p.characterstate),
    tonumber(p.x or p.pos_x) or 0,
    tonumber(p.y or p.pos_y) or 0,
    tostring(p.value or p.int_data),
    tostring(p.netid or p.player_flags),
    tostring(p.px or p.tx or p.int_x),
    tostring(p.py or p.ty or p.int_y),
    tostring(p.extrasize))
end

_TRAFFIC_START = function(max)
  if _TRAFFIC.on then return 'sudah aktif' end
  _TRAFFIC.max = tonumber(max) or 400
  _TRAFFIC.buf, _TRAFFIC.count, _TRAFFIC.dropped = {}, 0, 0

  AddHook('OnSendPacket', '_traf_s', function(t, text)
    t_add('SENDPACKET', 'type=' .. tostring(t) .. ' len=' .. tostring(text and #text or 0)
      .. ' ' .. tostring(text and text:sub(1, 240) or ''))
  end)
  AddHook('OnSendPacketRaw', '_traf_sr', function(packet)
    t_add('SENDRAW', pkt_str(packet))
  end)
  AddHook('OnVariant', '_traf_v', function(var, netid, delay)
    local head = (type(var) == 'table' and tostring(var[0])) or tostring(var)
    t_add('VARIANT', head .. ' netid=' .. tostring(netid) .. ' delay=' .. tostring(delay))
  end)
  AddHook('OnProcessTankUpdate', '_traf_p', function(packet)
    t_add('TANKUPDATE', pkt_str(packet))
  end)

  _TRAFFIC.on = true
  blog('traffic capture aktif (max ' .. tostring(_TRAFFIC.max) .. ')')
  return 'aktif'
end

_TRAFFIC_STOP = function()
  if not _TRAFFIC.on then return 'tidak aktif' end
  pcall(RemoveHook, '_traf_s')
  pcall(RemoveHook, '_traf_sr')
  pcall(RemoveHook, '_traf_v')
  pcall(RemoveHook, '_traf_p')
  _TRAFFIC.on = false
  blog('traffic capture berhenti, ' .. tostring(_TRAFFIC.count) .. ' kejadian')
  return 'berhenti'
end

_TRAFFIC_DUMP = function(n)
  n = tonumber(n) or 50
  local out = {}
  local start = math.max(1, #_TRAFFIC.buf - n + 1)
  for i = start, #_TRAFFIC.buf do out[#out + 1] = _TRAFFIC.buf[i] end
  return out
end

-- Versi teks: dipisah record-separator (0x1e) supaya bisa dipecah per baris
-- di sisi MCP tanpa tabrakan dengan isi paket.
_TRAFFIC_TEXT = function(n)
  return table.concat(_TRAFFIC_DUMP(n), '\30')
end

_TRAFFIC_STATS = function()
  local kinds = {}
  for _, line in ipairs(_TRAFFIC.buf) do
    local k = line:match('^%d+%s+(%S+)')
    if k then kinds[k] = (kinds[k] or 0) + 1 end
  end
  return { aktif = _TRAFFIC.on, total = _TRAFFIC.count, buffer = #_TRAFFIC.buf,
           dropped = _TRAFFIC.dropped, per_jenis = kinds }
end

_TRAFFIC_CLEAR = function()
  _TRAFFIC.buf, _TRAFFIC.count, _TRAFFIC.dropped = {}, 0, 0
  return 'dibersihkan'
end

--------------------------------------------------------------------- loop utama

local function body_of(res)
  -- MakeRequest di build ini mengembalikan status = 0 (bukan 200) dan
  -- error = false saat sukses; yang menentukan hanya error + content.
  if type(res) ~= 'table' then return nil, 'res bukan tabel' end
  local er = res.error
  if er ~= nil and er ~= false and tostring(er) ~= '' and tostring(er) ~= 'false'
     and tostring(er) ~= 'nil' then
    return nil, 'error=' .. tostring(er)
  end
  local c = res.content
  if type(c) == 'table' then c = c.body or c.text or c.data end
  if c == nil then return nil, 'content nil' end
  return tostring(c)
end

local function loop()
  blog('aktif, menunggu perintah dari MCP')
  local okp, resp = pcall(MakeRequest, BASE .. '/health', 'GET', nil, nil, 5000)
  blog('PROBE /health: ' .. _fmt_http(resp, okp))
  local errors = 0
  local diag = 0
  local hb = 0
  -- identitas instance: berguna saat ada lebih dari satu skrip berjalan
  local sid = string.format('%x%x', math.floor((now_ms() * 1000) % 2147483647), math.random(65535))
  pcall(MakeRequest, BASE .. '/hello?sid=' .. sid, 'GET', nil, nil, 8000)
  blog('instance ' .. sid)
  while running do
    local ok, res = pcall(MakeRequest, BASE .. '/poll?sid=' .. sid, 'GET', nil, nil, POLL_MS + 5000)
    local payload, why
    if ok then payload, why = body_of(res) else why = 'pcall: ' .. tostring(res) end
    hb = hb + 1
    if hb <= 3 or hb % 30 == 0 then
      local st = type(res) == 'table' and tostring(res.status) or type(res)
      local er = type(res) == 'table' and tostring(res.error) or '-'
      local ct = type(res) == 'table' and type(res.content) or '-'
      local peek = (type(res) == 'table' and type(res.content) == 'string')
        and res.content:sub(1, 30) or '-'
      pcall(MakeRequest, BASE .. '/diag?msg=' .. urlenc(string.format(
        'HB ok=%s why=%s st=%s err=%s ctype=%s peek=%s',
        tostring(ok), tostring(why), st, er, ct, peek)), 'GET', nil, nil, 8000)
    end
    if not payload then
      diag = diag + 1
      log_add('warn', 'poll: ' .. tostring(why))
      if diag <= 3 then
        -- tampil di konsol mod: satu-satunya kanal balik saat server belum
        -- bisa dijangkau
        blog('poll GAGAL: ' .. tostring(why))
      end
    end

    if payload and payload ~= 'none' and payload ~= '' then
      errors = 0
      -- buang hanya pembungkus kutip ganda dari enc() (jangan sentuh isi kode)
      if payload:sub(1, 1) == '"' and payload:sub(-1) == '"' then
        payload = payload:sub(2, -2)
      end
      blog('terima: ' .. payload:sub(1, 60))
      local id, code = payload:match('^([%w]+)|(.*)$')
      if not id then
        -- tanpa prefix id: perlakukan seluruh payload sebagai kode
        code, id = payload, nil
      end
      local okack = pcall(MakeRequest,
        BASE .. '/ack?sid=' .. sid .. '&id=' .. tostring(id or '-') .. '&len=' .. #tostring(code or ''),
        'GET', nil, nil, 8000)
      if not okack then
        pcall(MakeRequest, BASE .. '/diag?msg=' .. urlenc('ack gagal: ' .. payload:sub(1, 60)),
          'GET', nil, nil, 8000)
      end
      if code and code ~= '' then
        local t0 = now_ms()
        local good, out = run_code(code)
        local ms = now_ms() - t0
        log_add(good and 'ok' or 'err',
          string.format('%s ms, %d char -> %s', tostring(ms), #code, out:sub(1, 200)))
        local body = (id and (id .. '|') or '') .. (good and 'ok' or 'err') .. '|' .. out
        local sent, err = post('/result', body)
        if not sent then
          log_add('error', 'gagal kirim hasil: ' .. tostring(err))
        end
      end
    else
      errors = errors + 1
      if errors == 3 then
        blog('menunggu perintah (tidak ada perintah baru)')
      end
      Sleep(500)
    end
  end
  blog('berhenti')
end

_boot('SETUP ok, menjalankan loop')
local ok_thread, err_thread = pcall(RunThread, loop)
if not ok_thread then
  _boot('RunThread GAGAL: ' .. tostring(err_thread))
  blog('RunThread gagal: ' .. tostring(err_thread))
end

