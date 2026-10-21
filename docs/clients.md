# Memakai gt-mcp dari klien MCP lain

Server ini bicara **MCP stdio** biasa, jadi klien apa pun yang mendukung MCP
lewat stdio bisa memakainya: Claude Code, Codex CLI, opencode, Gemini CLI,
Cursor, Zed, Cline, Continue, dan lain-lain.

Aturan umum:

- command  : `<venv>/bin/python` (Windows: `<venv>\Scripts\python.exe`)
- args     : `["/path/ke/gt-mcp/server.py"]`
- env      : `GT_BRIDGE_PORT` (default 8770), `PATH` harus memuat folder `platform-tools`
- satu server = satu proses; kalau port bridge sudah dipegang proses lain, instance
  kedua otomatis masuk mode `attached` dan meneruskan perintah lewat `/enqueue`

> Nama kunci config beda-beda antar klien dan bisa berubah antar versi. Kalau
> potongan di bawah tidak diterima, cek `--help`/dokumentasi klien tersebut;
> yang penting isinya tetap: command + args + env seperti di atas.

## Claude Code

```bash
claude mcp add growtopia \
  -e GT_BRIDGE_PORT=8770 \
  -- /home/adit/Documents/botex/gt-mcp/.venv/bin/python \
     /home/adit/Documents/botex/gt-mcp/server.py
```

## Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.growtopia]
command = "/home/adit/Documents/botex/gt-mcp/.venv/bin/python"
args = ["/home/adit/Documents/botex/gt-mcp/server.py"]
env = { GT_BRIDGE_PORT = "8770" }
```

## opencode (`opencode.json`)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "growtopia": {
      "type": "local",
      "command": ["/home/adit/Documents/botex/gt-mcp/.venv/bin/python",
                  "/home/adit/Documents/botex/gt-mcp/server.py"],
      "enabled": true,
      "environment": { "GT_BRIDGE_PORT": "8770" }
    }
  }
}
```

## Gemini CLI (`~/.gemini/settings.json`)

```json
{
  "mcpServers": {
    "growtopia": {
      "command": "/home/adit/Documents/botex/gt-mcp/.venv/bin/python",
      "args": ["/home/adit/Documents/botex/gt-mcp/server.py"],
      "env": { "GT_BRIDGE_PORT": "8770" }
    }
  }
}
```

## Cursor (`~/.cursor/mcp.json`) / Cline / Continue

```json
{
  "mcpServers": {
    "growtopia": {
      "command": "/home/adit/Documents/botex/gt-mcp/.venv/bin/python",
      "args": ["/home/adit/Documents/botex/gt-mcp/server.py"],
      "env": { "GT_BRIDGE_PORT": "8770" }
    }
  }
}
```

## Zed (`settings.json`)

```json
{
  "context_servers": {
    "growtopia": {
      "command": {
        "path": "/home/adit/Documents/botex/gt-mcp/.venv/bin/python",
        "args": ["/home/adit/Documents/botex/gt-mcp/server.py"],
        "env": { "GT_BRIDGE_PORT": "8770" }
      }
    }
  }
}
```

## Hermes Agent (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  growtopia:
    command: /home/adit/Documents/botex/gt-mcp/.venv/bin/python
    args:
      - /home/adit/Documents/botex/gt-mcp/server.py
    env:
      PATH: /home/adit/Android/Sdk/platform-tools:/usr/bin:/bin
    connect_timeout: 30.0
    enabled: true
```

## Catatan lintas klien

- **Tool gambar**: `screenshot`, `screenshot_crop`, `panel_crop` mengembalikan
  content `image` (PNG base64), bukan teks. Klien yang tidak mendukung content
  gambar tetap bisa memanggilnya, tapi hanya akan melihat metadata.
- **Jangan dua server menulis port yang sama tanpa mode attached**: versi ini
  sudah menangani itu (`GET /status`, `POST /enqueue`), tapi klien yang berbeda
  tidak berbagi antrean perintah — satu proses jadi pemilik, yang lain menumpang.
- **Windows**: pastikan `adb.exe` ada di `PATH` atau set `ANDROID_SDK_ROOT`.
  Semua path sementara memakai `tempfile.gettempdir()`, bukan `/tmp`.
- **macOS**: `adb` dari `brew install android-platform-tools`, atau set
  `ANDROID_SDK_ROOT` ke SDK yang dipakai Android Studio.
