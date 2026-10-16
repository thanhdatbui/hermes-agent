# Desktop GUI MCP Integration, Stdio CWD Path Trap & Antigravity/Claude Desktop Setup

**Date:** 2026-10-16  
**Context:** Local testing of private FastMCP server (`yccmed`) inside Antigravity Desktop GUI and Claude Desktop.

---

## 1. The Stdio CWD Relative Path Trap (Agentic Runaway Bug)

### The Symptom
When testing an MCP server locally in a desktop agent (e.g. Antigravity IDE / Claude Desktop):
- The tool calls successfully (`mcp: yccmed | search_medical_tenders {"keyword": "trocar"}`).
- The tool immediately returns: `"Không tìm thấy gói thầu nào với từ khóa 'trocar'"` or `"Không tìm thấy gói thầu IB2600001 trong cache"`, despite data existing in `bidding_cache.db`.
- The desktop agent (e.g. Gemini 3.8 Flash / Claude 3.5 Sonnet) assumes the database is missing or corrupted, and triggers **agentic runaway**: spawning recursive PowerShell commands (`Get-ChildItem -Path C:\ -Recurse -Filter "*bidding*"`, `Get-CimInstance Win32_Process`), consuming reasoning turns and stalling the conversation.

### Root Cause
When a desktop GUI launches a stdio MCP server (`command: "python", args: ["D:/.../server.py"]`), the subprocess inherits the GUI's own working directory (often the user profile root or the workspace root `D:\Taadaa\`), **NOT** the directory containing `server.py`.

If `server.py` defines the database path with a bare relative string:
```python
# BUG: Resolves to CWD/bidding_cache.db (empty new DB!)
DB_PATH = os.environ.get("BID_DB_PATH", "bidding_cache.db")
conn = init_db(DB_PATH)
```
SQLite silently creates a brand-new, completely empty database file in the GUI's CWD. The seeded data in `.../mcp_server/bidding_cache.db` is never read.

### The Fix
Always anchor local SQLite/file storage to `__file__`:
```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BID_DB_PATH", os.path.join(BASE_DIR, "bidding_cache.db"))
conn = init_db(DB_PATH)
```
Ensure `server.py` ends with the stdio transport runner:
```python
if __name__ == '__main__':
    mcp.run()
```

---

## 2. Antigravity IDE GUI: Permission Allowlist vs Server Registry

### The UI Misconception
In Antigravity IDE, navigating to **Settings -> Projects -> <Project> -> MCP Tools** shows:
```text
MCP Tools
External tools the agent can call via Model Context Protocol.

[Allow ⌵] [ Enter tool name or server... ] [ Add ]
```
Users often look at this empty box and assume the MCP server was not installed or failed to load.

### Technical Reality
1. **Per-Project Permission Allowlist:** That screen is **NOT** where MCP servers are defined. It is the project's security filter (`permissionGrants` in project JSON).
2. **Global MCP Server Registry:** MCP servers in Antigravity are configured globally in:
   `~/.gemini/config/mcp_config.json`
   ```json
   {
     "mcpServers": {
       "yccmed": {
         "command": "python",
         "args": [
           "D:/Taadaa/site ban hang clone/mcp_server/server.py"
         ],
         "disabled": false
       }
     }
   }
   ```
3. **Automatic Schema Caching:** When added via `agy mcp add <name> <cmd> [args...]`, Antigravity caches the tool schemas in `~/.gemini/antigravity/mcp/<name>/` (`search_medical_tenders.json`, `evaluate_tender_yccmed.json`, etc.).
4. **Chat Invocations:** In any conversation, the agent can call the tools immediately. If the tool is not pre-allowed in the project's Settings, Antigravity prompts the user with an *"Allow / Always Allow"* confirmation bubble. Clicking "Always Allow" automatically adds the tool to that exact Settings box.

---

## 3. Claude Desktop Configuration (Windows)

To integrate a local Python FastMCP server into Claude Desktop on Windows:

1. Locate or create `%APPDATA%\Claude\claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "yccmed": {
         "command": "<PYTHON_VENV_PATH>\\python.exe",
         "args": [
           "D:/Taadaa/site ban hang clone/mcp_server/server.py"
         ]
       }
     }
   }
   ```
2. **Critical Rule for Python Binary:** Always use the full absolute path to the Python interpreter inside the virtual environment where `fastapi`, `mcp`, and dependencies are installed. Windows desktop apps do not activate virtual environments by default; using bare `"python"` often launches system Python or Windows Store stubs, failing with `ModuleNotFoundError: No module named 'mcp'`.
3. Restart Claude Desktop completely. The tools will appear under the hammer/tools icon in every new chat.
