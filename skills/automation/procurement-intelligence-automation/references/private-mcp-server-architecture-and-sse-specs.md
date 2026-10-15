# Private MCP Server Architecture, OAuth Specifications & SSE Streaming for ChatGPT

## 1. ChatGPT MCP Handshake & Protocol Specifications

When ChatGPT connects to an MCP Server (`chatgpt.com/plugins` / Developer Mode):
1. **Transport:** Uses HTTP Server-Sent Events (SSE) streaming for bidirectional communication:
   - `GET /sse`: ChatGPT initiates a persistent SSE stream to receive server-sent events (like endpoint discovery and notifications).
   - `POST /messages?sessionId=<id>`: ChatGPT sends JSON-RPC 2.0 requests (`initialize`, `tools/list`, `tools/call`).
2. **Reverse-Engineered Commercial Specification (Anovatech `dauthau.info` Case Study):**
   - Protected Resource Metadata: `/.well-known/oauth-protected-resource/mcp`
     ```json
     {
       "resource": "https://domain.com/mcp",
       "authorization_servers": ["https://domain.com"],
       "scopes_supported": ["bid:read"],
       "bearer_methods_supported": ["header"],
       "resource_name": "Bid Intelligence"
     }
     ```
   - Authorization Server Metadata: `/.well-known/oauth-authorization-server`
     ```json
     {
       "issuer": "https://domain.com",
       "authorization_endpoint": "https://domain.com/oauth/authorize",
       "token_endpoint": "https://domain.com/oauth/token",
       "registration_endpoint": "https://domain.com/oauth/register",
       "response_types_supported": ["code"],
       "grant_types_supported": ["authorization_code", "refresh_token"]
     }
     ```

---

## 2. Nginx Configuration for Zero-Hang SSE Streaming

Standard Nginx proxy buffering will buffer SSE chunks, causing ChatGPT to hang on the initial handshake or tool calls.

### Required Nginx Location Directive
```nginx
location /mcp/ {
    proxy_pass http://127.0.0.1:8100/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection '';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # CRITICAL: Disable buffering for real-time SSE streams
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
    chunked_transfer_encoding on;
}
```

---

## 3. FastMCP Server Implementation Pattern (Python) & Dual Transport

In modern `mcp` SDK (v1.28+), `FastMCP` does **not** have `get_asgi_app()`. The verified production pattern mounts `mcp.streamable_http_app()` inside a FastAPI application with an asynchronous lifespan managing `mcp.session_manager.run()`, while also supporting stdio transport when executed directly:

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("YCCMED Bidding Assistant", description="Private National Bidding Assistant")

@mcp.tool()
def search_medical_tenders(keyword: str = "trocar", scope: str = "", only_open: bool = True, limit: int = 15) -> str:
    """Tra cứu các gói thầu y tế đang mở nhận hồ sơ trên Mua Sắm Công."""
    # Query local SQLite cache populated by daily crawler
    return "Danh sách các gói thầu..."

@mcp.tool()
def evaluate_tender_yccmed(bid_code: str) -> str:
    """Thẩm định tiêu chuẩn kỹ thuật gói thầu với sản phẩm của công ty."""
    return "Kết quả thẩm định..."

@mcp.tool()
def get_tender_details(bid_code: str) -> str:
    """Bóc tách toàn bộ thông tin chi tiết gói thầu từ cache."""
    return "Chi tiết gói thầu..."

# 1. Lifespan for HTTP/SSE streamable session manager
@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        yield

mcp_asgi_app = mcp.streamable_http_app()
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "yccmed-mcp"}

@app.get("/.well-known/oauth-authorization-server")
def oauth(request: Request):
    return {
        "issuer": str(request.base_url).rstrip("/"),
        "authorization_endpoint": f"{request.base_url}oauth/authorize",
        "token_endpoint": f"{request.base_url}oauth/token",
    }

app.mount("/", mcp_asgi_app)

# 2. Dual-Transport support: Stdio when invoked directly (for agy CLI / local debug)
if __name__ == "__main__":
    mcp.run()
```

---

## 4. End-to-End Verification with Antigravity CLI (`agy`)

Before delivering the MCP endpoint to ChatGPT, verify the tool registration and execution using local Antigravity CLI:

```bash
# 1. Register stdio server in Antigravity CLI
agy mcp add yccmed python "D:/path/to/server.py"

# 2. Check registration status
agy mcp list

# 3. Test tool call execution
python D:/Taadaa/tools/ag_cli.py ask --profile acc_01 "Sử dụng MCP tool search_medical_tenders của server yccmed tìm kiếm gói thầu trocar"
```

---

## 5. Key Operational Insights from Field Practice

1. **Crawler Decoupling:** Never run browser-based crawling synchronously inside an MCP tool call (ChatGPT has a 30s-60s tool execution timeout). The crawler must run asynchronously via cron (e.g. daily watchdog), continuously indexing bids into SQLite. The MCP tool must read directly from the fast SQLite cache ($O(1) < 50\text{ms}$).
2. **User Experience Distinction:**
   - 1-way Push (Telegram): Best for alerting the operator to new bids at 8:00 AM.
   - 2-way Interactive (ChatGPT MCP): Best for the business owner to examine details, ask follow-up questions, and evaluate technical specifications interactively on their phone.
