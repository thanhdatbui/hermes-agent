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

has_old_string = "OLD_STRING:" in combined
has_file = "FILE:" in combined
has_file_content = "FILE_CONTENT:" in combined or "NEW_FILE_CONTENT:" in combined

# ==========================================
# 1. NHÁNH CREATE (Tạo file mới)
# ==========================================
if has_file_content and not has_old_string:
    file_match = re.search(r'FILE:\s*([^\r\n]+)', combined)
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
# P0-1: Chỉ cho phép Investigate nếu TUYỆT ĐỐI KHÔNG có FILE: và KHÔNG có OLD_STRING:
if not has_file and not has_old_string:
    # Bắt buộc phải có trần ngân sách
    if not re.search(r'\b(?:max_calls|budget|tối đa|giới hạn)\b', combined, re.IGNORECASE):
        msg = (
            f"[HARD GATE #3 - INVESTIGATE ROUTE] delegate_task BỊ CHẶN: Task điều tra/khảo sát bắt buộc phải có BUDGET GIỚI HẠN!\n"
            f"Thêm vào context: 'BUDGET: <= 5 tool calls, thời gian < 3 phút. Trả về kết luận/anchor rồi THOÁT NGAY'."
        )
        print(json.dumps({"action": "block", "message": msg}))
        sys.exit(0)
    sys.exit(0)

# ==========================================
# 3. NHÁNH EDIT CODE (Mặc định khi có FILE: hoặc sửa code)
# ==========================================
file_match = re.search(r'FILE:\s*([^\r\n]+)', combined)
if not file_match:
    msg = (
        f"[HARD GATE #3 - VERIFICATION] delegate_task BỊ CHẶN: Thiếu nhãn 'FILE: <đường_dẫn_tuyệt_đối>'.\n"
        f"Mọi task sửa code bắt buộc phải chỉ định rõ file đích duy nhất."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

target_file = file_match.group(1).strip().strip('"').strip("'")
norm_path = os.path.normpath(target_file)

if not os.path.isabs(norm_path) or not os.path.isfile(norm_path):
    msg = (
        f"[HARD GATE #3 - VERIFICATION] delegate_task BỊ CHẶN: File đích '{target_file}' KHÔNG TỒN TẠI trên đĩa!\n"
        f"Coordinator phải kiểm tra đĩa vật lý trước khi dispatch worker."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

# Bắt buộc có FOCUSED_TEST
if "FOCUSED_TEST:" not in combined:
    msg = (
        f"[HARD GATE #3 - VERIFICATION] delegate_task BỊ CHẶN: Thiếu nhãn 'FOCUSED_TEST: <lệnh_test_hoặc_compile>'.\n"
        f"Worker cần lệnh kiểm chứng cụ thể < 30s."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

# Trích xuất OLD_STRING
old_str_match = re.search(r'OLD_STRING:\s*[\r\n]+(.*?)(?=[\r\n]+NEW_STRING:|$)', combined, re.DOTALL)
if not old_str_match:
    old_str_match = re.search(r'OLD_STRING:\s*(.*?)(?=NEW_STRING:|$)', combined)

if not old_str_match or len(old_str_match.group(1).strip()) < 10:
    msg = (
        f"[HARD GATE #3 - ANTI-FAKE-COMPLIANCE] delegate_task BỊ CHẶN: Đã chỉ định FILE: nhưng THIẾU 'OLD_STRING:' (hoặc < 10 chars)!\n"
        f"CẤM mượn danh 'investigate' khi đã nhắm file sửa. BẮT BUỘC cung cấp mốc code cũ cần sửa để worker không đọc dạo."
    )
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

old_string = old_str_match.group(1).strip()

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
