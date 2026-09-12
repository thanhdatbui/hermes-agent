"""
[HERMES HARD GATE #0 - PROGRESS SUPERVISOR & DEADMAN SWITCH]
Pre-tool hook:
Giám sát nhịp tiến độ thực tế (Real State Change) của từng Session độc lập.
Vá toàn diện:
- BLOCKER-1 CRITICAL: if lock_fd is None -> sys.exit(0) fail-safe, TUYỆT ĐỐI CẤM RMW khi không có lock!
- BLOCKER-1 HIGH: Stale lock breaking theo mtime (>10s tuổi tự hủy) chống deadlock khi process trước bị kill.
- Quản lý state độc lập theo session_id.
- Ghi file ATOMIC (temp file + os.replace).
"""
import json, sys, os, time

SUPERVISOR_STATE_FILE = "C:/Users/Kibe/AppData/Local/hermes/cache/progress_supervisor_state.json"
SUPERVISOR_LOCK_FILE = "C:/Users/Kibe/AppData/Local/hermes/cache/progress_supervisor.lock"
MAX_STALL_SECONDS = 15 * 60  # 15 phút không có state change = STALL
MAX_ACTION_COUNT = 8
STALE_LOCK_SECONDS = 10.0

REAL_STATE_CHANGES = [
    "patch",
    "write_file",
]

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = payload.get("tool") or payload.get("tool_name") or ""
args = payload.get("args") or {}
cmd = args.get("command") or ""
session_id = payload.get("session_id") or "global_session"

now = time.time()
cache_dir = os.path.dirname(SUPERVISOR_STATE_FILE)
os.makedirs(cache_dir, exist_ok=True)

# Helper acquire lock an toàn có phá stale lock
def acquire_lock_safe(lock_path, max_attempts=50, sleep_sec=0.02):
    for _ in range(max_attempts):
        try:
            return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except (FileExistsError, OSError):
            # Kiểm tra stale lock
            try:
                if os.path.exists(lock_path):
                    age = time.time() - os.path.getmtime(lock_path)
                    if age > STALE_LOCK_SECONDS:
                        os.remove(lock_path)
                        continue
            except Exception:
                pass
            time.sleep(sleep_sec)
    return None

lock_fd = acquire_lock_safe(SUPERVISOR_LOCK_FILE)

# BLOCKER-1 CRITICAL: Không có lock thì THOÁT NGAY (fail-safe), CẤM RMW không khóa!
if lock_fd is None:
    sys.exit(0)

try:
    all_states = {}
    if os.path.exists(SUPERVISOR_STATE_FILE):
        try:
            with open(SUPERVISOR_STATE_FILE, 'r', encoding='utf-8') as f:
                all_states = json.load(f)
        except Exception:
            all_states = {}

    session_state = all_states.setdefault(session_id, {
        "last_progress_time": now,
        "action_count_since_progress": 0,
        "last_progress_action": "session_init"
    })

    last_progress = session_state.get("last_progress_time", now)
    action_count = session_state.get("action_count_since_progress", 0)

    # Nhận diện hành vi tạo ra tiến độ THỰC TẾ
    is_real_progress = False
    if tool_name in REAL_STATE_CHANGES:
        is_real_progress = True
    elif tool_name == "terminal":
        if any(k in cmd for k in ["py_compile", "git commit", "git push", "pytest"]):
            is_real_progress = True

    if is_real_progress:
        session_state["last_progress_time"] = now
        session_state["last_progress_action"] = f"{tool_name}: {cmd[:50]}"
        session_state["action_count_since_progress"] = 0
        
        tmp_file = f"{SUPERVISOR_STATE_FILE}.{os.getpid()}.tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(all_states, f, indent=2)
        os.replace(tmp_file, SUPERVISOR_STATE_FILE)
        sys.exit(0)

    # Tăng biến đếm thao tác thăm dò
    action_count += 1
    session_state["action_count_since_progress"] = action_count
    tmp_file = f"{SUPERVISOR_STATE_FILE}.{os.getpid()}.tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(all_states, f, indent=2)
    os.replace(tmp_file, SUPERVISOR_STATE_FILE)

    # KIỂM TRA ĐIỀU KIỆN TREO (STALL CONDITION)
    elapsed = now - last_progress
    if elapsed > MAX_STALL_SECONDS and action_count > MAX_ACTION_COUNT:
        msg = (
            f"[HARD GATE #0 - PROGRESS SUPERVISOR DEADMAN SWITCH] TIẾN TRÌNH BỊ ĐÓNG BĂNG!\n"
            f"Session '{session_id}' đã chạy {elapsed/60:.1f} phút và thực hiện {action_count} thao tác thăm dò "
            f"mà KHÔNG có bất kỳ State Change thực tế nào (không patch code, không compile, không chạy test)!\n"
            f"CẤM tiếp tục mò mẫm hay quay cuồng gọi terminal/read_file.\n"
            f"BẮT BUỘC:\n"
            f"  1. Dừng ngay lập tức.\n"
            f"  2. Báo cáo User hiện trạng, blocker cụ thể và đề xuất hướng giải quyết.\n"
            f"  (Chỉ mở lại sau khi có lệnh mới từ User hoặc reset state file)."
        )
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)
finally:
    try:
        os.close(lock_fd)
        if os.path.exists(SUPERVISOR_LOCK_FILE):
            os.remove(SUPERVISOR_LOCK_FILE)
    except Exception:
        pass

sys.exit(0)
