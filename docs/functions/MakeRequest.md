# MakeRequest(url: string[, method: string][, headers: table][, content: string][, timeout_ms: int]) -> HttpResponse

Ringkasan
- `MakeRequest(url: string[, method: string][, headers: table][, content: string][, timeout_ms: int]) -> HttpResponse`
- Melakukan permintaan HTTP dan mengembalikan `HttpResponse`.

Penjelasan
- Periksa `status` dan `error` pada hasil untuk memastikan request sukses sebelum memproses `content`.
- `headers` berupa table key->value (mis. `{ ['Content-Type'] = 'application/json' }`). `content` digunakan untuk body saat metode seperti `POST/PUT`.

Parameter
- `url: string`
- `method: string (opsional)` — Default biasanya `GET`.
- `headers: table (opsional)` — Header HTTP.
- `content: string (opsional)` — Body (untuk POST/PUT, dll.).
- `timeout_ms: int (opsional)` — Timeout milidetik.

Nilai kembali
- `HttpResponse` — berisi status, error, method, content.

Contoh (Lua)
```lua
local res = MakeRequest('https://growtopiagame.com/detail', 'GET')
if not res.error and res.status == 200 then
  local online = tonumber(res.content:match('"online_user":"(%d+)"'))
  if online then LogToConsole('Current User Online : ' .. online) end
end
```

Terkait
- [HttpResponse](../structures/HttpResponse.md)
