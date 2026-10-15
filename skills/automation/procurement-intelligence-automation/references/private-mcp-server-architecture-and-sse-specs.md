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

## 3. FastMCP Server Implementation Pattern (Python)

```python
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Bidding Intelligence", description="Private National Bidding Assistant")

@mcp.tool()
def search_medical_tenders(keyword: str = "trocar", only_open: bool = True) -> str:
    """Tra cứu các gói thầu y tế đang mở nhận hồ sơ trên Mua Sắm Công."""
    # Query local SQLite cache populated by daily crawler
    return "Danh sách các gói thầu..."

@mcp.tool()
def evaluate_tender_compliance(bid_code: str) -> str:
    """Thẩm định tiêu chuẩn kỹ thuật gói thầu với sản phẩm của công ty."""
    return "Kết quả thẩm định..."

app = mcp.get_asgi_app()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 4. Key Operational Insights from Field Practice

1. **Crawler Decoupling:** Never run browser-based crawling synchronously inside an MCP tool call (ChatGPT has a 30s-60s tool execution timeout). The crawler must run asynchronously via cron (e.g. daily watchdog), continuously indexing bids into SQLite. The MCP tool must read directly from the fast SQLite cache ($O(1) < 50\text{ms}$).
2. **User Experience Distinction:**
   - 1-way Push (Telegram): Best for alerting the operator to new bids at 8:00 AM.
   - 2-way Interactive (ChatGPT MCP): Best for the business owner to examine details, ask follow-up questions, and evaluate technical specifications interactively on their phone.
