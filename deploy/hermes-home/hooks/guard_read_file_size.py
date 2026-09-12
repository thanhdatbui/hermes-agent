"""
[HERMES HARD GATE #1] Pre-tool hook: Chặn read_file / read_file_tool trên file > 10MB.
Coordinator bị buộc dùng tail/grep thay vì đọc nguyên log 215MB.
Output: {"action": "block", "message": "..."} → Hermes từ chối chạy tool.
"""
import json, sys, os

MAX_BYTES = 10 * 1024 * 1024  # 10 MB

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # fail-open: không đọc được payload → cho qua

args = payload.get("args") or {}
path = args.get("path") or args.get("file_path") or ""

if not path:
    sys.exit(0)

try:
    size = os.path.getsize(path)
except OSError:
    sys.exit(0)  # file không tồn tại → để tool tự báo lỗi

if size > MAX_BYTES:
    mb = size // 1024 // 1024
    msg = (
        f"[HARD GATE] read_file BỊ CHẶN: file {path!r} dung lượng {mb}MB > 10MB giới hạn. "
        f"CẤM đọc toàn bộ file log khủng. BẮT BUỘC dùng một trong các lệnh sau:\n"
        f"  terminal('tail -n 200 {path!r}')\n"
        f"  terminal('grep -m 50 PATTERN {path!r}')\n"
        f"  read_file(path, offset=<dòng_cuối - 200>, limit=200)"
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)
