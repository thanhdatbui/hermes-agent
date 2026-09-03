#!/usr/bin/env python3
"""Probe xem 1 system prompt có dính denylist Antigravity không (verify 17/08).

Cách dùng:
  python ag-identity-probe.py "You are Hermes Agent, ..."     # nội dung trực tiếp
  python ag-identity-probe.py @file.txt                       # đọc từ file

POST ag/gemini-3.7-flash-high (2 account AG rotate). Exit:
  0 = 200 (không dính denylist)
  1 = 429 (dính denylist / bucket đang lock — chạy lại sau ~30s để phân biệt)
  2 = lỗi khác
"""
import json, os, sys, urllib.request, urllib.error

arg = sys.argv[1] if len(sys.argv) > 1 else "You are a helpful assistant."
if arg.startswith("@"):
    with open(arg[1:], encoding="utf-8") as f:
        sys_content = f.read()
else:
    sys_content = arg

body = {
    "model": "ag/gemini-3.7-flash-high",
    "messages": [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": "hi"},
    ],
    "max_tokens": 20,
    "stream": False,
}
req = urllib.request.Request(
    "http://127.0.0.1:20128/v1/chat/completions",
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": f"Bearer {os.environ['NINEROUTER_API_KEY']}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=90) as r:
        print(f"200 OK — {len(sys_content)} chars system content")
        sys.exit(0)
except urllib.error.HTTPError as e:
    err = e.read().decode("utf-8", "replace")
    print(f"HTTP {e.code} — {err[:200]}")
    sys.exit(1 if e.code == 429 else 2)
except Exception as e:
    print(f"EXC {type(e).__name__}: {e}")
    sys.exit(2)
