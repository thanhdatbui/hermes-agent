"""
[HERMES HARD GATE #5 - DEVICE BULKHEAD & CIRCUIT BREAKER]
Pre-tool hook:
1. P0-2: Chặn TUYỆT ĐỐI bấm tay ADB: input tap, swipe, keyevent, text.
2. Zero-Foreground Device I/O: Mọi thao tác Canary/PowerShell thiết bị bắt buộc Background HOẶC timeout <= 60s.
3. Device Circuit Breaker: Kiểm tra danh sách máy (kể cả quote '"1,2,3"' hay bare '1,2,3', phân tách phẩy hoặc space).
   Bổ sung Cooldown tự động (15 phút) chuyển circuit breaker sang half-open thay vì khóa vĩnh viễn.
"""
import json, sys, os, time, re

CIRCUIT_STATE_FILE = "C:/Users/Kibe/AppData/Local/hermes/cache/device_circuit_breaker.json"
MAX_CONSECUTIVE_FAILS = 3
CIRCUIT_COOLDOWN_SECONDS = 15 * 60  # Sau 15 phút cho phép thử lại (Half-Open)

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = payload.get("tool") or payload.get("tool_name") or ""
if tool_name != "terminal":
    sys.exit(0)

args = payload.get("args") or {}
cmd = args.get("command") or ""
timeout = args.get("timeout")
is_bg = args.get("background", False)

# ==========================================
# 1. P0-2: CẤM BẤM TAY ADB CHỮA CHÁY
# ==========================================
is_manual_adb = bool(re.search(r'\badb\b.*\bshell\b.*\binput\b\s+(tap|swipe|keyevent|text)', cmd, re.IGNORECASE))
if is_manual_adb:
    msg = (
        f"[HARD GATE #5 - CẤM BẤM TAY ADB] COMMAND BỊ CHẶN: '{cmd[:70]}...'.\n"
        f"INVARIANT FARM SAFETY: CẤM TUYỆT ĐỐI dùng adb shell input tap/swipe/keyevent bấm qua màn hình lỗi thay cho sửa code!\n"
        f"Máy lỗi là hiện trường để viết code handler tự động, không được can thiệp tay."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

# ==========================================
# 2. DEVICE BULKHEAD & CIRCUIT BREAKER
# ==========================================
is_device_cmd = bool(re.search(r'\b(?:run-feed-session|run_tiktok|run-follow)\.ps1\b', cmd, re.IGNORECASE))
# BLOCKER-3: Bắt cả dạng có quotes và khoảng trắng
machine_matches = re.findall(r'-(?:Machines|machine)\s+[\'"]?([0-9,\s]+)[\'"]?', cmd, re.IGNORECASE)

if is_device_cmd:
    target_machines = []
    if machine_matches:
        raw_m = machine_matches[0]
        target_machines = [m.strip() for m in re.split(r'[,\s]+', raw_m) if m.strip().isdigit()]
    
    # 2.1 KIỂM TRA CIRCUIT BREAKER CHO TỪNG MÁY
    if os.path.exists(CIRCUIT_STATE_FILE):
        try:
            with open(CIRCUIT_STATE_FILE, 'r', encoding='utf-8') as f:
                cb_data = json.load(f)
            
            now = time.time()
            for m_id in target_machines:
                m_info = cb_data.get(m_id, {})
                machine_fails = m_info.get("consecutive_fails", 0)
                last_updated = m_info.get("last_updated", 0)
                
                # Nếu đã quá thời gian cooldown -> Half-Open cho phép thử lại
                is_in_cooldown = (now - last_updated) < CIRCUIT_COOLDOWN_SECONDS
                
                if machine_fails >= MAX_CONSECUTIVE_FAILS and is_in_cooldown:
                    remaining_cooldown = int((CIRCUIT_COOLDOWN_SECONDS - (now - last_updated)) / 60)
                    msg = (
                        f"[HARD GATE #5 - CIRCUIT BREAKER OPEN] LỆNH BỊ CHẶN: Máy M{m_id} đã thất bại liên tiếp {machine_fails} lần!\n"
                        f"Máy đang bị cách ly (Quarantine, còn {remaining_cooldown}m cooldown) để bảo vệ session khỏi việc lặp lại vô tận.\n"
                        f"BẮT BUỘC:\n"
                        f"  1. Dừng thử lại trên máy M{m_id}.\n"
                        f"  2. Báo cáo User kiểm tra phần cứng/proxy mạng vật lý của máy M{m_id}.\n"
                        f"  (Chỉ mở lại sau khi User can thiệp hoặc reset state: rm -f {CIRCUIT_STATE_FILE})"
                    )
                    print(json.dumps({"action": "block", "message": msg}))
                    sys.exit(0)
        except Exception:
            pass

    # 2.2 BULKHEAD: CẤM FOREGROUND CHẠY DÀI TRÊN SESSION CHÍNH
    if not is_bg and (timeout is None or timeout > 60):
        msg = (
            f"[HARD GATE #5 - DEVICE BULKHEAD] LỆNH ĐIỀU KHIỂN THIẾT BỊ BỊ CHẶN (timeout={timeout}s)!\n"
            f"Coordinator KHÔNG ĐƯỢC PHÉP block luồng điều phối chính quá 60s để chờ thiết bị thật.\n"
            f"BẮT BUỘC thực hiện theo 1 trong 2 cách:\n"
            f"  Cách 1 (Khuyên dùng): terminal(command='{cmd[:60]}...', background=True, notify_on_complete=True)\n"
            f"  Cách 2 (Quick probe < 60s): Đặt rõ timeout <= 60s."
        )
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)

sys.exit(0)
