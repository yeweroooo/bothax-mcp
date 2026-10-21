# Memakai bothax-mcp dari klien MCP lain

Server ini bicara MCP stdio biasa, jadi klien apa pun yang mendukung stdio bisa memakainya.

Nilai yang perlu diisi di semua klien:

- command: `<repo>/.venv/bin/python` (Windows: `<repo>\.venv\Scripts\python.exe`)
- args: `["<repo>/server.py"]`
- env: `GT_BRIDGE_PORT` (default 8770), dan `PATH` harus memuat folder `platform-tools`

Satu server menulis ke satu port bridge. Kalau port itu sudah dipegang proses lain,
instance kedua masuk mode `attached` dan meneruskan perintah lewat `/enqueue`.

Nama kunci config berbeda antar klien dan bisa berubah antar versi. Kalau potongan di
bawah ditolak, cek `--help` klien tersebut; isinya tetap sama: command, args, env.

## Claude Code

```bash
claude mcp add bothax \
  -e GT_BRIDGE_PORT=8770 \
  -- <repo>/.venv/bin/python \
     <repo>/server.py
```

## Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.bothax]
command = "<repo>/.venv/bin/python"
args = ["<repo>/server.py"]
env = { GT_BRIDGE_PORT = "8770" }
```

## opencode (`opencode.json`)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "bothax": {
      "type": "local",
      "command": ["<repo>/.venv/bin/python", "<repo>/server.py"],
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
    "bothax": {
      "command": "<repo>/.venv/bin/python",
      "args": ["<repo>/server.py"],
      "env": { "GT_BRIDGE_PORT": "8770" }
    }
  }
}
```

## Cursor (`~/.cursor/mcp.json`), Cline, Continue

```json
{
  "mcpServers": {
    "bothax": {
      "command": "<repo>/.venv/bin/python",
      "args": ["<repo>/server.py"],
      "env": { "GT_BRIDGE_PORT": "8770" }
    }
  }
}
```

## Zed (`settings.json`)

```json
{
  "context_servers": {
    "bothax": {
      "command": {
        "path": "<repo>/.venv/bin/python",
        "args": ["<repo>/server.py"],
        "env": { "GT_BRIDGE_PORT": "8770" }
      }
    }
  }
}
```

## Hermes Agent (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  bothax:
    command: <repo>/.venv/bin/python
    args:
      - <repo>/server.py
    env:
      PATH: <sdk>/platform-tools:/usr/bin:/bin
    connect_timeout: 30.0
    enabled: true
```

## Catatan lintas klien

- **Tool gambar**: `screenshot`, `screenshot_crop`, dan `panel_crop` mengembalikan content
  `image` (PNG base64). Klien yang tidak menampilkan content gambar tetap bisa memanggilnya,
  tapi hanya melihat metadata.
- **Dua klien, satu port**: keduanya berbagi antrean perintah. Satu proses jadi pemilik,
  yang lain menumpang.
- **Windows**: taruh `adb.exe` di `PATH` atau set `ANDROID_SDK_ROOT`. Path sementara memakai
  `tempfile.gettempdir()`, bukan `/tmp`.
- **macOS**: `brew install android-platform-tools`, atau set `ANDROID_SDK_ROOT` ke SDK
  Android Studio.
