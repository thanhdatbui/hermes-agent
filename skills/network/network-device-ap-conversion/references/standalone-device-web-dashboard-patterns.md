# Standalone Device Web Dashboard — Python Patterns

## The ThreadingHTTPServer Requirement (Critical Pitfall)

Python's `http.server.HTTPServer` is **single-threaded by default**. When your
API handlers make blocking external calls (device APIs, network requests), the
server blocks all concurrent HTTP requests until the call returns.

**Symptom:** Browser requests queue up and timeout (10s+) when the page auto-refreshes
or fires concurrent AJAX calls. The server logs show requests arriving but no response.

**Fix:** Always use `ThreadingHTTPServer` for any device proxy dashboard:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True  # Don't block process exit on hung threads
```

Use `ThreadingHTTPServer(...)` instead of `HTTPServer(...)`.

## Embedded HTML Pattern

For lightweight single-file dashboards (no external dependencies, no build step):

```python
HTML_PAGE = r"""<!DOCTYPE html>
<html>
<head>...</head>
<body>...</body>
</html>"""

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/api/data":
            self._json_response(fetch_device_data())

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
```

## Defensive API Proxy Pattern

Wrap all device API calls in try/except to prevent server crashes:

```python
def safe_handler(self):
    try:
        data = mt_api("/endpoint")
        self._json_response(data)
    except Exception as e:
        self._json_response({"error": str(e)}, 502)
```

## Frontend Auto-Refresh Pattern

```javascript
// Fetch parallel data, don't block on one endpoint
async function loadData() {
    const [data, status] = await Promise.all([
        fetch('/api/proxies').then(r => r.json()),
        fetch('/api/status').then(r => r.json())
    ]);
    renderTable(data);
}
// Refresh every 30s, not faster (avoids hammering device API)
setInterval(loadData, 30000);
```

## Launcher Batch File

```batch
@echo off
title Device Web Manager
cd /d "%~dp0"
python server.py
pause
```

## Verified Architecture

- **MikroTik Web Manager** at `D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py`
  - Port 8090, proxies to MikroTik REST API at 192.168.110.2:9090
  - 60 PPPoE interfaces, 1-click IP change per interface
  - Auto-refresh every 30s, search/filter, modal progress UI
