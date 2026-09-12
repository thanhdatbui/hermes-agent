"""
[HERMES HARD GATE #5 - POST-TOOL CIRCUIT BREAKER RECORDER]
Post-tool hook: Ghi nhận kết quả của các lệnh điều khiển thiết bị (Canary/PowerShell/ADB).
Vá toàn diện theo Claude Opus Review:
- BLOCKER-0 P0: Đưa inline flag (?im) ra ĐẦU pattern (tránh re.error: global flags not at the start of expression).
- Bọc try/except toàn khối nhận diện lỗi, fail-safe về exit_code != 0.
- BLOCKER-1 CRITICAL: if lock_fd is None -> sys.exit(0) fail-safe.
- BLOCKER-1 HIGH: Stale lock breaking theo mtime (>10s tuổi tự hủy).
- BLOCKER-2: Neo regex dòng summary: r'(?m)^\s*.*?\b([1-9]\d*)\s+failed\b'.
- BLOCKER-3: Tách danh sách máy hỗ trợ cả phẩy và khoảng trắng: `re.split(r'[,\s]+', raw_m)`.
"""
import json, sys, os, time, re

CIRCUIT_STATE_FILE = "C:/Users/Kibe/AppData/Local/hermes/cache/device_circuit_breaker.json"
LOCK_FILE = "C:/Users/Kibe/AppData/Local/hermes/cache/device_circuit_breaker.lock"
STALE_LOCK_SECONDS = 10.0

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = payload.get("tool") or payload.get("tool_name") or ""
if tool_name != "terminal":
    sys.exit(0)

args = payload.get("args") or {}
cmd = args.get("command") or ""
result = payload.get("result") or {}
exit_code = result.get("exit_code", 0)
output = result.get("output") or ""

is_device_cmd = bool(re.search(r'\b(?:run-feed-session|run_tiktok|run-follow)\.ps1\b', cmd, re.IGNORECASE))
machine_matches = re.findall(r'-(?:Machines|machine)\s+[\'"]?([0-9,\s]+)[\'"]?', cmd, re.IGNORECASE)

if is_device_cmd and machine_matches:
    raw_m = machine_matches[0]
    target_machines = [m.strip() for m in re.split(r'[,\s]+', raw_m) if m.strip().isdigit()]
    
    cache_dir = os.path.dirname(CIRCUIT_STATE_FILE)
    os.makedirs(cache_dir, exist_ok=True)
    
    # BLOCKER-0 & Fail-safe: Đưa (?im) ra đầu biểu thức và bọc try
    is_failed = (exit_code != 0)
    try:
        has_summary_failed = bool(re.search(r'(?m)^\s*.*?\b([1-9]\d*)\s+failed\b', output, re.IGNORECASE))
        has_hard_error = bool(re.search(r'(?im)\bmanual-needed\b|Command timed out|^\s*(?:FATAL|CRITICAL)\b', output))
        if has_summary_failed or has_hard_error:
            is_failed = True
    except Exception:
        pass
    
    now = time.time()
    
    # Helper acquire lock an toàn có phá stale lock
    lock_fd = None
    for _ in range(50):
        try:
            lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except (FileExistsError, OSError):
            try:
                if os.path.exists(LOCK_FILE):
                    age = time.time() - os.path.getmtime(LOCK_FILE)
                    if age > STALE_LOCK_SECONDS:
                        os.remove(LOCK_FILE)
                        continue
            except Exception:
                pass
            time.sleep(0.02)
            
    # BLOCKER-1 CRITICAL: Không có lock thì THOÁT NGAY, CẤM RMW!
    if lock_fd is None:
        sys.exit(0)
        
    try:
        cb_data = {}
        if os.path.exists(CIRCUIT_STATE_FILE):
            try:
                with open(CIRCUIT_STATE_FILE, 'r', encoding='utf-8') as f:
                    cb_data = json.load(f)
            except Exception:
                cb_data = {}
                
        for m_id in target_machines:
            m_entry = cb_data.setdefault(m_id, {"consecutive_fails": 0, "last_updated": 0})
            if is_failed:
                m_entry["consecutive_fails"] += 1
            else:
                m_entry["consecutive_fails"] = 0
            m_entry["last_updated"] = now
            
        # Ghi atomic
        tmp_file = f"{CIRCUIT_STATE_FILE}.{os.getpid()}.tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(cb_data, f, indent=2)
        os.replace(tmp_file, CIRCUIT_STATE_FILE)
    finally:
        try:
            os.close(lock_fd)
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass

sys.exit(0)
