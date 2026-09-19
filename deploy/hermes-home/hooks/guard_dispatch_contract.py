"""
[HERMES HARD GATE #3 - CLAUDE OPUS VERIFIED CONTRACT]
Pre-tool hook: Kiểm chứng tính đúng đắn của Dispatch Contract.
Phân loại DỰA TRÊN TÍN HIỆU CẤU TRÚC (Structural Signal), triệt tiêu Fake Compliance P0-1:
1. Có 'OLD_STRING:' -> BẮT BUỘC luồng EDIT (verify đĩa, uniqueness == 1, FOCUSED_TEST).
2. Có 'FILE_CONTENT:' và KHÔNG có 'OLD_STRING:' -> Luồng CREATE.
3. Luồng INVESTIGATE CHỈ HỢP LỆ khi KHÔNG CÓ 'FILE:' và KHÔNG CÓ 'OLD_STRING:' (task đọc mã thuần túy)
   và bắt buộc có BUDGET giới hạn (<= 5 calls).
"""
import json, sys, os, re

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = payload.get("tool") or payload.get("tool_name") or ""
if tool_name != "delegate_task":
    sys.exit(0)

args = payload.get("args") or {}
goal = args.get("goal") or args.get("prompt") or ""
context = args.get("context") or ""
combined = goal + "\n" + context

if not goal.strip():
    sys.exit(0)

# Normalization: Hỗ trợ linh hoạt hoa/thường, triệt tiêu lỗ hổng bypass case
file_match = re.search(r'\b(?:FILE|File|file|File cần sửa|Target file|target_file):\s*([^\r\n]+)', combined)
old_str_match = re.search(r'\b(?:OLD_STRING|Old_string|old_string|Mã cũ|Đoạn cũ):\s*[\r\n]+(.*?)(?=[\r\n]+\b(?:NEW_STRING|New_string|new_string|FOCUSED_TEST|focused_test)\b|$)', combined, re.DOTALL)
if not old_str_match:
    old_str_match = re.search(r'\b(?:OLD_STRING|Old_string|old_string|Mã cũ|Đoạn cũ):\s*(.*?)(?=\b(?:NEW_STRING|New_string|new_string|FOCUSED_TEST|focused_test)\b|$)', combined)

new_str_match = re.search(r'\b(?:NEW_STRING|New_string|new_string|Mã mới|Đoạn mới):\s*[\r\n]+(.*?)(?=[\r\n]+\b(?:FOCUSED_TEST|focused_test|OLD_STRING|old_string)\b|$)', combined, re.DOTALL)
if not new_str_match:
    new_str_match = re.search(r'\b(?:NEW_STRING|New_string|new_string|Mã mới|Đoạn mới):\s*(.*?)(?=\b(?:FOCUSED_TEST|focused_test|OLD_STRING|old_string)\b|$)', combined)

has_old_string = bool(old_str_match)
has_file = bool(file_match)
has_file_content = bool(re.search(r'\b(?:FILE_CONTENT|NEW_FILE_CONTENT):\s*', combined, re.IGNORECASE))

# Phát hiện ý đồ sửa code thông qua đường dẫn file code hoặc từ khóa patch
code_ext_match = re.search(r'[A-Za-z]:[\\/][^\s\'",;]+\.(?:py|json|yaml|yml|sh|ps1|js|ts)', combined)
edit_intent = bool(re.search(r'\b(?:patch|sửa code|chỉnh sửa|cập nhật code|refactor|fix code)\b', combined, re.IGNORECASE))
is_code_edit = has_old_string or (has_file and not has_file_content) or (bool(code_ext_match) and edit_intent)

# ==========================================
# 1. NHÁNH CREATE (Tạo file mới)
# ==========================================
if has_file_content and not has_old_string:
    if not file_match:
        msg = (
            f"[HARD GATE #3 - CREATE ROUTE] delegate_task BỊ CHẶN: Tạo file mới bắt buộc phải có nhãn 'FILE: <đường_dẫn_tuyệt_đối>'."
        )
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)
    sys.exit(0)

# ==========================================
# 2. NHÁNH INVESTIGATE (Thám hiểm thuần túy - CẤM ĐÁNH LẬN SANG EDIT)
# ==========================================
if not is_code_edit and not has_file_content:
    if not re.search(r'\b(?:max_calls|budget|tối đa|giới hạn)\b', combined, re.IGNORECASE):
        msg = (
            f"[HARD GATE #3 - INVESTIGATE ROUTE] delegate_task BỊ CHẶN: Task điều tra/khảo sát bắt buộc phải có BUDGET GIỚI HẠN!\n"
            f"Thêm vào context: 'BUDGET: <= 5 tool calls, thời gian < 3 phút. Trả về kết luận/anchor rồi THOÁT NGAY'."
        )
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)
    sys.exit(0)

# ==========================================
# 3. NHÁNH EDIT CODE (Code Surgery - BẮT BUỘC SOL PLAN / T0 BYPASS)
# ==========================================
if not file_match:
    if code_ext_match:
        target_file = code_ext_match.group(0).strip().strip('"').strip("'")
    else:
        msg = (
            f"[HARD GATE #3 - VERIFICATION] delegate_task BỊ CHẶN: Thiếu nhãn 'FILE: <đường_dẫn_tuyệt_đối>'.\n"
            f"Mọi task sửa code bắt buộc phải chỉ định rõ file đích duy nhất."
        )
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)
else:
    target_file = file_match.group(1).strip().strip('"').strip("'")

norm_path = os.path.normpath(target_file)

if not os.path.isabs(norm_path) or not os.path.isfile(norm_path):
    msg = (
        f"[HARD GATE #3 - VERIFICATION] delegate_task BỊ CHẶN: File đích '{target_file}' KHÔNG TỒN TẠI trên đĩa!\n"
        f"Coordinator phải kiểm tra đĩa vật lý trước khi dispatch worker."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

# Bắt buộc có FOCUSED_TEST (hỗ trợ hoa/thường)
focused_test_match = re.search(r'\b(?:FOCUSED_TEST|focused_test|test):\s*([^\r\n]+)', combined)
if not focused_test_match:
    msg = (
        f"[HARD GATE #3 - VERIFICATION] delegate_task BỊ CHẶN: Thiếu nhãn 'FOCUSED_TEST: <lệnh_test_hoặc_compile>'.\n"
        f"Worker cần lệnh kiểm chứng cụ thể < 30s."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

if not old_str_match or len(old_str_match.group(1).strip()) < 10:
    msg = (
        f"[HARD GATE #3 - ANTI-FAKE-COMPLIANCE] delegate_task BỊ CHẶN: Đã chỉ định FILE: nhưng THIẾU 'OLD_STRING:' (hoặc < 10 chars)!\n"
        f"CẤM mượn danh 'investigate' khi đã nhắm file sửa. BẮT BUỘC cung cấp mốc code cũ cần sửa để worker không đọc dạo."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

old_string = old_str_match.group(1).strip()
new_string = new_str_match.group(1).strip() if new_str_match else ""

# ---------------------------------------------------------
# HARD GATE #3B: SOL PLAN GATE (CẤM ĐI TẮT, KHÓA CỨNG T0)
# ---------------------------------------------------------
def _evaluate_t0_bypass(old_s: str, new_s: str) -> tuple:
    if not new_s:
        return False, "Không có new_string để xác thực T0"
    diff = abs(len(new_s) - len(old_s))
    if diff >= 60:
        return False, f"Diff {diff} >= 60 ký tự"
    combo = old_s + "\n" + new_s
    ctrl_kws = [
        r'\bif\b', r'\belif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b',
        r'\btry\b', r'\bexcept\b', r'\bfinally\b', r'\bdef\b', r'\bclass\b',
        r'\breturn\b', r'\byield\b', r'\bbreak\b', r'\bcontinue\b',
        r'\braise\b', r'\bwith\b', r'\bmatch\b', r'\bcase\b'
    ]
    for kw in ctrl_kws:
        if re.search(kw, combo, re.IGNORECASE):
            return False, f"Chứa từ khóa điều khiển logic/branching '{kw}'"
    for line in combo.splitlines():
        l = line.strip()
        if not l or l.startswith("#"):
            continue
        if re.match(r'^[A-Za-z0-9_]+\s*=\s*[\d"\'\.\-_]+$', l):
            continue
        return False, f"Dòng code '{l}' vượt quá phạm vi hằng số/comment"
    return True, "Hợp lệ"

is_t0, t0_reason = _evaluate_t0_bypass(old_string, new_string)

# Van xả áp khẩn cấp & Van an toàn đạo đức (Safety Valve):
# Cho phép bypass Sol Plan khi Sol sập, dính bẫy đạo đức (Safety Policy Refusal) hoặc có chỉ đạo khẩn cấp
emergency_match = re.search(r'\b(?:EMERGENCY_OVERRIDE|SOL_FALLBACK|SOL_OFFLINE|USER_OVERRIDE|SAFETY_REFUSAL|ETHICS_BYPASS|POLICY_OVERRIDE|SAFETY_POLICY_BYPASS):\s*([^\r\n]+)', combined, re.IGNORECASE)

if emergency_match:
    # Ghi audit log vật lý khi kích hoạt van xả áp
    try:
        import datetime
        log_dir = r"D:\Taadaa\runtime\audit_logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "safety_valve_trigger.jsonl")
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "trigger_flag": emergency_match.group(0).split(":")[0].strip(),
            "reason": emergency_match.group(1).strip(),
            "target_file": target_file if 'target_file' in locals() else "unknown",
            "goal": goal[:200]
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

if not is_t0 and not emergency_match:
    # BẮT BUỘC PHẢI CÓ SOL PLAN HỢP LỆ
    sol_match = re.search(r'\b(?:SOL_PLAN_ID|sol_plan_id|SOL_PLAN|sol_plan):\s*([a-zA-Z0-9_\-]+)', combined)
    if not sol_match:
        # TỰ ĐỘNG GỌI SOL PLANNER (VISIBLE BLOCKING HANDOFF)
        # Recursion breaker: Tránh loop nếu vừa tự gọi xong
        is_retry = bool(re.search(r'\b(?:SOL_AUTOCALL_ATTEMPTED|sol_autocall_attempted)\b', combined, re.IGNORECASE))
        auto_plan_id = None
        auto_err = None
        
        if not is_retry:
            try:
                import subprocess
                cmd = [
                    sys.executable,
                    r"D:\Taadaa\tools\sol_planner.py",
                    "--goal", goal[:300],
                    "--file", norm_path,
                    "--context", context[:1000]
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
                if proc.returncode == 0 and proc.stdout:
                    try:
                        res_json = json.loads(proc.stdout)
                        auto_plan_id = res_json.get("sol_plan_id")
                    except Exception:
                        pass
                else:
                    auto_err = proc.stderr[:200] if proc.stderr else f"Exit code {proc.returncode}"
            except subprocess.TimeoutExpired:
                auto_err = "Sol Planner timeout > 25s"
            except Exception as e:
                auto_err = str(e)
        
        if auto_plan_id:
            # Sinh plan thành công -> Visible Blocking để Coordinator retry kèm SOL_PLAN_ID
            msg = (
                f"[SOL_GATE AUTO-RESOLVE] 🟢 ĐÃ TỰ ĐỘNG GỌI SOL PLANNER (:20129) VÀ SINH KẾ HOẠCH THÀNH CÔNG!\n"
                f"• SOL_PLAN_ID: {auto_plan_id}\n"
                f"• File đích: {norm_path}\n"
                f"• Mục tiêu: {goal[:150]}\n\n"
                f"👉 HÀNH ĐỘNG TIẾP THEO:\n"
                f"Coordinator hãy re-dispatch lại worker với dòng sau trong context:\n"
                f"SOL_PLAN_ID: {auto_plan_id}\n"
            )
            print(json.dumps({"action": "block", "message": msg}))
            sys.exit(0)
        else:
            # Sol sập / timeout / refusal do policy đạo đức -> KÍCH HOẠT SOL_FALLBACK CHO PHÉP COORDINATOR CHỈ ĐẠO
            fallback_reason = auto_err or "Sol Planner offline / refusal / policy block"
            msg = (
                f"[SOL_GATE FALLBACK VALVE] ⚠️ SOL PLANNER KHÔNG KHẢ DỤNG HOẶC TỪ CHỐI DO POLICY/OFFLINE!\n"
                f"• Lý do: {fallback_reason}\n"
                f"• Quyền chỉ đạo kỹ thuật tự động chuyển về cho COORDINATOR & SẾP KIBE.\n\n"
                f"👉 HÀNH ĐỘNG TIẾP THEO:\n"
                f"Coordinator hãy re-dispatch lại worker với dòng sau trong context để bypass an toàn:\n"
                f"SOL_FALLBACK: {fallback_reason}\n"
            )
            print(json.dumps({"action": "block", "message": msg}))
            sys.exit(0)

    sol_id = sol_match.group(1).strip()
    sol_paths = [
        os.path.join(r"D:\Taadaa\runtime\sol_plans", f"{sol_id}.json"),
        os.path.join(r"C:\Users\Kibe\AppData\Local\hermes\runtime\sol_plans", f"{sol_id}.json")
    ]
    valid_sol_file = next((p for p in sol_paths if os.path.isfile(p)), None)
    if not valid_sol_file:
        msg = (
            f"[SOL_GATE HARD HOOK] ❌ DISPATCH BỊ CHẶN: Không tìm thấy file kế hoạch của SOL_PLAN_ID='{sol_id}' trên đĩa!\n"
            f"Hãy gọi Sol Planner thật qua python D:/Taadaa/tools/sol_planner.py để sinh kế hoạch hợp lệ."
        )
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)

    import time
    try:
        with open(valid_sol_file, "r", encoding="utf-8") as sf:
            sol_data = json.load(sf)
        created_at = sol_data.get("created_at", 0)
        age = time.time() - created_at
        if age > 600:
            msg = (
                f"[SOL_GATE HARD HOOK] ❌ DISPATCH BỊ CHẶN: Kế hoạch '{sol_id}' đã quá hạn ({int(age)}s > 600s)!\n"
                f"Hãy chạy lại Sol Planner để cấp kế hoạch mới cập nhật."
            )
            print(json.dumps({"action": "block", "message": msg}))
            sys.exit(0)
    except Exception as e:
        msg = f"[SOL_GATE HARD HOOK] ❌ Lỗi đọc file kế hoạch '{valid_sol_file}': {e}"
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)

# ĐỌC ĐĨA KIỂM CHỨNG (VERIFICATION GATE)
try:
    with open(norm_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
except Exception as e:
    msg = f"[HARD GATE #3] Không thể đọc file '{norm_path}': {e}"
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

norm_old = "\n".join(line.strip() for line in old_string.splitlines() if line.strip())
norm_content = "\n".join(line.strip() for line in content.splitlines() if line.strip())

occurrences = norm_content.count(norm_old)

if occurrences == 0:
    msg = (
        f"[HARD GATE #3 - VERIFICATION FAILED] delegate_task BỊ CHẶN: 'OLD_STRING' KHÔNG TỒN TẠI trong file '{os.path.basename(norm_path)}'!\n"
        f"Coordinator đang gửi đoạn code cũ sai lệch/chế mồm. Hãy kiểm tra lại file bằng read_file trước khi soạn contract."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

if occurrences > 1:
    msg = (
        f"[HARD GATE #3 - UNIQUENESS FAILED] delegate_task BỊ CHẶN: 'OLD_STRING' xuất hiện {occurrences} LẦN trong file!\n"
        f"Anchor không duy nhất sẽ làm worker patch nhầm chỗ. Bổ sung thêm dòng context xung quanh để đảm bảo duy nhất tuyệt đối (count == 1)."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

sys.exit(0)
