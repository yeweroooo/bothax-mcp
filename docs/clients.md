# Using bothax-mcp from other MCP clients

The server speaks plain stdio MCP, so any client that supports stdio can run it.

Values every client needs:

- command: `<repo>/.venv/bin/python` (Windows: `<repo>\.venv\Scripts\python.exe`)
- args: `["<repo>/server.py"]`
- env: `GT_BRIDGE_PORT` (default 8770), and `PATH` must include the `platform-tools` folder

One server writes to one bridge port. If another process already holds that port, the
second instance starts in `attached` mode and forwards commands through `/enqueue`.

Config keys differ between clients and change between versions. If a snippet below is
rejected, check that client's `--help`; the shape stays the same: command, args, env.

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

## Notes across clients

- **Image tools**: `screenshot`, `screenshot_crop`, and `panel_crop` return `image`
  content (base64 PNG). A client that cannot render images can still call them, but it
  only sees the metadata.
- **Two clients, one port**: they share the command queue. One process owns the port and
  the other rides along.
- **Windows**: put `adb.exe` on `PATH` or set `ANDROID_SDK_ROOT`. Temp files use
  `tempfile.gettempdir()`, not `/tmp`.
- **macOS**: `brew install android-platform-tools`, or point `ANDROID_SDK_ROOT` at the
  Android Studio SDK.
