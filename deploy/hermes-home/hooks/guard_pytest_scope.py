"""
[HERMES HARD GATE #2] Pre-tool hook: Chặn pytest quét toàn bộ repo.
Buộc Coordinator chỉ chạy đúng file/test cụ thể.
"""
import json, sys, re

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

args = payload.get("args") or {}
cmd = args.get("command") or ""

# Chỉ xét lệnh có pytest
if not re.search(r'\bpytest\b', cmd):
    sys.exit(0)

# Cho phép nếu có đường dẫn file .py cụ thể sau pytest
# VD: pytest D:/Taadaa/.../test_x.py hoặc python -m pytest D:/...test_x.py
has_specific_file = bool(re.search(r'pytest[^\n]*[\s/\\][^\s]+test[^\s]*\.py', cmd))
has_k_filter     = bool(re.search(r'\s-k\s+\S', cmd))
has_nodeids       = bool(re.search(r'::\w+', cmd))

if has_specific_file or has_k_filter or has_nodeids:
    sys.exit(0)  # hợp lệ → cho qua

# Các pattern bị chặn: pytest trần, pytest tests/, pytest .
msg = (
    "[HARD GATE] pytest BỊ CHẶN: CẤM quét toàn bộ repo/thư mục. "
    "BẮT BUỘC chỉ định đúng 1 file test cụ thể:\n"
    "  terminal('D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest "
    "D:/Taadaa/.../tests/test_specific.py -x -q')\n"
    "Lý do: pytest toàn suite gây timeout >900s vi phạm rule điều phối."
)
print(json.dumps({"action": "block", "message": msg}))
sys.exit(0)
