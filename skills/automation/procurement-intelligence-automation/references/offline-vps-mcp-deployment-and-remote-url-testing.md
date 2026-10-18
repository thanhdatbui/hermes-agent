# Offline Python FastMCP Deployment on Firewalled VPS & Remote URL Testing

**Date:** 2026-10-18  
**Context:** Deploying private FastMCP server (`yccmed`) to a production cloud VPS (`doravo.net` / `152.42.187.200`) with blocked outbound network, and resolving the Remote URL vs Local JSON testing dilemma.

---

## 1. The Remote URL vs Local Stdio MCP Testing Dilemma

### The Misunderstanding
Operators often become confused when asked to edit JSON files (`claude_desktop_config.json`, `mcp_config.json`) during testing, asking:
*"Why do I have to edit JSON files? The end user only has to paste a URL into ChatGPT, why can't I just test by pasting the URL like them?"*

### Architecture Breakdown: Remote HTTP/SSE vs Local stdio

| Dimension | Remote MCP Server (ChatGPT / Mobile / Production) | Local stdio MCP Server (Desktop App Testing) |
| :--- | :--- | :--- |
| **Transport** | HTTP POST + Server-Sent Events (SSE) via `/mcp` | Standard Input / Output (`stdio`) pipe |
| **Where Code Runs**| Dedicated 24/7 cloud server / VPS | Subprocess spawned on local machine's CPU/RAM |
| **Config Needed** | Just the endpoint URL (e.g. `https://doravo.net/mcp`) | Executable path (`command`) + Script path (`args`) |
| **Configuration UI** | Web / Mobile text field (Settings -> Developer Mode) | JSON configuration file or Developer CLI |

### How to Test Remote URLs Directly Without Touching JSON
1. **Antigravity CLI (Supports Remote URLs natively!):**
   The `agy mcp add` command detects `http://` or `https://` URLs automatically:
   ```bash
   # Connects directly to remote MCP server over HTTP/SSE:
   agy.exe mcp add yccmed https://doravo.net/mcp
   ```
   This gives the operator the EXACT same experience as ChatGPT: testing the remote cloud server over the internet with zero local Python subprocesses or JSON file modifications.
2. **Claude Desktop Limitation:**
   Claude Desktop natively only supports `stdio` subprocesses configured via `%APPDATA%\Claude\claude_desktop_config.json`. To connect Claude Desktop to a remote URL, an external stdio-to-SSE bridge (e.g. `mcp-proxy` or `npx -y @modelcontextprotocol/server-sse`) is required in the JSON `args`.

---

## 2. Deploying to Firewalled / Outbound-Blocked Cloud VPS

### The Symptom: PyPI Connection Timeout
When running `pip install` on hardened cloud servers (e.g. DigitalOcean droplets with restrictive outbound security groups, UFW DROP rules, or isolated network segments):
```text
TCP ... -> 151.101.64.223:https (SYN_SENT)
curl: (28) Failed to connect to pypi.org port 443: Connection timed out
```
Outbound SYN packets are dropped by the firewall or gateway, preventing direct package installation from PyPI.

### The Solution: Offline Wheel Bundle Packaging
Download Linux manylinux wheels on the local machine (which has full internet access), upload them via SFTP/Paramiko, and install completely offline (`--no-index`).

#### Step 1: Local Cross-Platform Wheel Download
```python
import subprocess, sys

# Target Python 3.10 Linux x86_64
pkgs = [
    "mcp==1.28.1", "fastapi==0.115.0", "uvicorn==0.32.0", "httpx==0.28.1",
    "starlette==0.38.6",
    "anyio", "httpx-sse", "jsonschema", "pydantic", "pydantic-settings",
    "pyjwt", "python-multipart", "sse-starlette", "typing-extensions",
    "pydantic-core", "annotated-types", "sniffio", "idna", "click", "h11", "httpcore",
    "certifi", "typing-inspection", "exceptiongroup", "attrs", "jsonschema-specifications",
    "referencing", "rpds-py", "python-dotenv"
]

cmd = [
    sys.executable, "-m", "pip", "download",
    "--platform", "manylinux2014_x86_64",
    "--python-version", "3.10",
    "--only-binary=:all:",
    "--no-deps",
    "-d", "./wheels",
] + pkgs
subprocess.run(cmd, check=True)
```

#### Step 2: Upload Wheels via Paramiko SFTP
Upload all `*.whl` files to `/opt/doravo-mcp/wheels/` on the VPS.

#### Step 3: Offline Force-Reinstall on VPS
```bash
/opt/doravo-mcp/venv/bin/pip install --no-index \
  --find-links /opt/doravo-mcp/wheels \
  --force-reinstall --no-deps /opt/doravo-mcp/wheels/*.whl
```

---

## 3. Critical Dependency Compatibility Trap: FastAPI vs Starlette

### The Error
```text
TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'
```
Or:
```text
StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated.
```

### Root Cause
`fastapi==0.115.0` is pinned to `starlette<0.39.0,>=0.38.2`. If an unpinned `pip download starlette` pulls `starlette-1.7.0` (or any 1.x / >=0.39 release), Starlette removes legacy lifecycle kwargs (`on_startup`, `on_shutdown`) from `Router.__init__()`, which instantly crashes FastAPI during application startup.

### The Invariant
Always explicitly pin `starlette==0.38.6` when bundling wheels for FastAPI 0.115.0. Delete any `starlette-1*.whl` from the wheels directory before running pip install.

---

## 4. Nginx Reverse Proxy Placement in Complex Monolith Configurations

### The Error
```text
nginx: [emerg] location "/mcp" is outside location "/cron/" in /etc/nginx/sites-enabled/doravo.net.conf:128
nginx: configuration file /etc/nginx/nginx.conf test failed
```

### Root Cause
In legacy PHP/CMS monolith configurations (e.g. CMSNT ShopClone7), configuration files often contain nested location blocks, such as:
```nginx
location ^~ /cron/ {
    access_log off;
    location ~ \.php$ { ... }
}
```
If an automated script searches for `location ~ \.php$` and inserts `location /mcp` before it, the `/mcp` block ends up nested inside `/cron/`, causing Nginx syntax validation to fail.

### Safe Placement Pattern
Always insert top-level HTTP endpoints right before `listen 443 ssl;` or immediately after the main `server {` opening brace:
```nginx
    # --- YCCMED Private MCP Server Proxy ---
    location /mcp {
        proxy_pass http://127.0.0.1:8100;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    location /.well-known/oauth-authorization-server {
        proxy_pass http://127.0.0.1:8100/.well-known/oauth-authorization-server;
        proxy_set_header Host $host;
    }

    listen 443 ssl; # managed by Certbot
```
Ensure `proxy_buffering off;` and `chunked_transfer_encoding off;` are enabled so Server-Sent Events (SSE) streams are not delayed by Nginx buffer queues.
