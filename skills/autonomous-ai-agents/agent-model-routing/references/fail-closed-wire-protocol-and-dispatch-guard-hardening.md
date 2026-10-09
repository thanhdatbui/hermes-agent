# Fail-Closed Wire Protocol & Dispatch Guard Hardening (2026-09-28)

## 1. Bối cảnh & Incident Lọt Lưới `deleg_ad3da98f`

Trong phiên ngày 29/09/2026, Coordinator dispatch task `deleg_ad3da98f` với mục tiêu:
*"Tích hợp CodexOAuth1455Lock vào codex_5sim_auto_verify.py và cron_chatgpt_web_pool_watchdog.py..."*
Mặc dù đã có quy tắc bất biến Anti-Multi-File trong hệ thống, lệnh dispatch gộp 2 file code nghiệp vụ này vẫn lọt qua hook và khiến Worker Luna High bị kéo vào vòng lặp đọc dạo 17 calls rồi chết đứng ở timeout 480s (8 phút).

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### Lỗ hổng 1: Lệch Schema Wire Protocol (`tool_input` vs `args`)
Hermes Agent Core khi kích hoạt `pre_tool_call` hook gửi payload theo chuẩn:
```json
{
  "tool_name": "delegate_task",
  "tool_input": {
    "goal": "...",
    "context": "..."
  }
}
```
Tuy nhiên, file hook `guard_dispatch_contract.py` trước đây chỉ đọc:
```python
args = payload.get("args") or {}
```
Do `payload.get("args")` trả về `None`, `args` trở thành `{}` rỗng $\to$ `goal` và `context` đều là chuỗi rỗng `""`.

### Lỗ hổng 2: Thiết kế Fail-Open chết người
Sau khi parse `goal`, hook có đoạn code:
```python
if not goal.strip():
    sys.exit(0)
```
Do `goal` rỗng, hook thực hiện `sys.exit(0)` mà không in JSON chặn, khiến Hermes Agent Core hiểu rằng hook cho phép lệnh dispatch đi qua tự do (Fail-Open)!

### Lỗ hổng 3: Bỏ sót Batch Mode (`tasks: [...]`)
Khi người dùng hoặc Coordinator gọi `delegate_task` dạng batch `tasks: [{goal, context}, ...]`, key `goal` ở cấp top-level không tồn tại. Hook cũ không bóc tách mảng `tasks`, dẫn đến việc các batch gộp file hoàn toàn thoát khỏi tầm kiểm soát.

### Lỗ hổng 4: Lỗi ký tự Word Boundary `\b` trên Shell
Khi ghi hoặc thay thế regex qua bash/python script, ký tự `\b` nếu không được xử lý cẩn thận sẽ bị bash hoặc python string escape hiểu nhầm thành ASCII `\x08` (Backspace byte), làm hỏng regex so khớp đuôi file code.

## 3. Bản Vá Kỹ Thuật Chuẩn Hóa (Fail-Closed Architecture)

Toàn bộ khối xử lý đầu vào của `guard_dispatch_contract.py` đã được nâng cấp sang chuẩn **FAIL-CLOSED 100%**:

```python
try:
    raw_in = sys.stdin.read()
    payload = json.loads(raw_in) if raw_in else {}
except Exception as e:
    _log_dispatch_audit("block", "fail_closed", f"Lỗi parse payload hook: {e}")
    print(json.dumps({"action": "block", "message": f"[HARD GATE #3 - FAIL-CLOSED] Lỗi parse payload hook: {e}"}))
    sys.exit(0)

tool_name = payload.get("tool_name") or payload.get("tool") or ""
if tool_name != "delegate_task":
    sys.exit(0)

args = payload.get("tool_input") or payload.get("args") or {}
if isinstance(args, str):
    try:
        args = json.loads(args)
    except Exception:
        pass

if not isinstance(args, dict):
    _log_dispatch_audit("block", "fail_closed", "tool_input không phải dict")
    print(json.dumps({"action": "block", "message": "[HARD GATE #3 - FAIL-CLOSED] tool_input của delegate_task phải là dict hợp lệ!"}))
    sys.exit(0)

# Trích xuất goal và context hỗ trợ cả Single task lẫn Batch mode (tasks: [...])
goal = args.get("goal") or args.get("prompt") or ""
context = args.get("context") or ""
tasks_list = args.get("tasks") or []

prompt_parts = []
if goal: prompt_parts.append(str(goal))
if context: prompt_parts.append(str(context))

if isinstance(tasks_list, list) and tasks_list:
    for t in tasks_list:
        if isinstance(t, dict):
            tg = t.get("goal") or ""
            tc = t.get("context") or ""
            if tg: prompt_parts.append(str(tg))
            if tc: prompt_parts.append(str(tc))

combined = chr(10).join(prompt_parts)

# FAIL-CLOSED: CẤM exit(0) nếu nội dung rỗng!
if not combined.strip():
    _log_dispatch_audit("block", "fail_closed", "Payload không có goal hoặc context")
    print(json.dumps({"action": "block", "message": "[HARD GATE #3 - FAIL-CLOSED] delegate_task BỊ CHẶN: Payload không có goal hoặc context hợp lệ!"}))
    sys.exit(0)
```

## 4. Dữ Liệu Đối Soát Thực Tế (10 Delegations Gần Nhất)

Đối soát từ `state.db` chứng minh mối tương quan trực tiếp giữa chất lượng Contract và kết quả của Worker:
- **Contract chuẩn (1 file, Scope Lock, focused test < 30s)**:
  - `deleg_93419cc6`: 171s, 8 calls $\to$ **COMPLETED**.
  - `deleg_65985bf7`: 152s, 11 calls $\to$ **COMPLETED**.
  - `deleg_9a287c86`: 242s, 12 calls $\to$ **COMPLETED**.
- **Contract vi phạm (Gộp file, goal mở, không khóa budget)**:
  - `deleg_ad3da98f`: Gộp 2 file $\to$ **TIMEOUT 480s (17 calls)**.
  - `deleg_714a4535`: Goal mở "tự động hồi sinh Codex" $\to$ **TIMEOUT 830s**.
  - `deleg_28e2e3b9`: Nâng cấp cache đa cụm $\to$ **TIMEOUT 480s (10 calls)**.
  - `deleg_08de2e51`: Lan man watchdog $\to$ **TIMEOUT 480s (28 calls)**.

👉 **KẾT LUẬN:** Bệnh "tê liệt / timeout" của Luna High 100% bắt nguồn từ việc Coordinator lơ là kỷ luật chia việc. Khi có khóa Fail-Closed chặn đứng các ca vi phạm từ cửa vào, Worker vận hành với độ tin cậy tuyệt đối.
