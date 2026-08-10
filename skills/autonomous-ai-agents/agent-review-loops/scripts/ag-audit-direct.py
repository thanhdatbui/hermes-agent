#!/usr/bin/env python3
"""Direct 9router AG-audit call — workaround khi invoke-ag-audit.ps1 treo ở Invoke-RestMethod.

Read-only (chỉ POST /v1/chat/completions). Ép tools:[] + tool_choice:"none"
(chặn Claude tự phát minh <tool_call> giả / hallucinate) và in verdict từ
dòng đầu non-empty của response.

Usage:
    python ag-audit-direct.py <prompt_file> [model] [out_file] [timeout_s]

    model    mặc định ag/claude-sonnet-4-6; chuẩn policy dùng ag/claude-opus-4-6-thinking
    out_file ghi content response (findings) để đọc sau
    timeout  mặc định 600; sonnet/opus thinking high thường 60-120s

Exit: 0 = có response (xem AG_AUDIT_VERDICT dòng cuối), 1 = fail.
Yêu cầu env NINEROUTER_API_KEY. Prompt lớn: nên NHÚNG diff inline
(git show <commit> -- <files>) vì model qua 9router không đọc được file.
"""
import json, os, sys, time, urllib.request, urllib.error

PROMPT_FILE = sys.argv[1]
MODEL = sys.argv[2] if len(sys.argv) > 2 else "ag/claude-sonnet-4-6"
OUT = sys.argv[3] if len(sys.argv) > 3 else None
TIMEOUT = int(sys.argv[4]) if len(sys.argv) > 4 else 600

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt = f.read()

body = {
    "model": MODEL,
    "reasoning_effort": "high",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 6000,
    "stream": False,
    "tools": [],
    "tool_choice": "none",
}

req = urllib.request.Request(
    "http://127.0.0.1:20128/v1/chat/completions",
    data=json.dumps(body).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {os.environ['NINEROUTER_API_KEY']}",
        "Content-Type": "application/json",
    },
    method="POST",
)

start = time.time()
try:
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    err = e.read().decode("utf-8", "replace")
    print(f"AG_AUDIT_FAILED: HTTP {e.code}: {err[:500]}", flush=True)
    sys.exit(1)
except Exception as e:
    print(f"AG_AUDIT_FAILED: {type(e).__name__}: {e}", flush=True)
    sys.exit(1)

elapsed = time.time() - start
content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
if not content:
    print("AG_AUDIT_FAILED: empty response content", flush=True)
    sys.exit(1)

print(f"AG_AUDIT_ELAPSED={elapsed:.1f}s", flush=True)
print(content, flush=True)

# verdict = first non-empty line (wrapper Get-AgVerdict semantics)
first = next((l.strip() for l in content.splitlines() if l.strip()), "")
verdict = None
for w in ("APPROVED", "MINOR_FIXES", "REJECT"):
    if first.upper().startswith(w) or f"VERDICT: {w}" in first.upper():
        verdict = w
        break
print(f"AG_AUDIT_VERDICT={verdict or 'UNPARSEABLE'}", flush=True)
if OUT:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(content)