# Universal Hook Guidance Audit & Silent Veto Elimination (Kiểm Toán Độ Phủ Action Mandate & Triệt Tiêu Veto Câm)

## 1. Bối cảnh & Hiện Tượng Thực Tế (Sự Cố 2026-10-25)
Trong quá trình vận hành hệ thống AI Coordinator - Worker, User đặt câu hỏi cốt lõi:
*"Hook cơ học đã tích hợp guide của hook guide để chỉ dẫn agent chưa?"*

Qua đối soát toàn diện hệ thống hooks (`guard_dispatch_contract.py`, `guard_cronjob_safety.py`, `hooks/guard_broad_grep.py`, `claude_worker.py`), phát hiện sự bất đối xứng nghiêm trọng về độ phủ của chuẩn Action Mandate (Rule 1 & Rule 26 trong skill `mechanical-guidance-gate-design`):

| Hook Kiểm Soát | Vị Trí Chặn | Trạng Thái Guidance | Cấu Trúc Trả Về | Đánh Giá Chuẩn Rule 1 |
| :--- | :--- | :--- | :--- | :--- |
| **`guard_dispatch_contract.py`** | `delegate_task` (Create, Investigate, Edit) | ✅ ĐẦY ĐỦ | `rule_id`, `message`, `guidance`, `required_action` (`command`, `instruction`, `description`), `next_action` | **CHUẨN ACTION MANDATE** (Agent có ngay lệnh $O(1)$ để chạy tiếp) |
| **`guard_cronjob_safety.py`** | `cronjob` (create, update), `terminal` (background) | ✅ ĐÃ FIX (commit `ba16ae4`) | `rule_id`, `message`, `guidance`, `required_action` (`command`, `instruction`, `description`), `tool`, `timestamp` | **CHUẨN ACTION MANDATE** (Đã nâng cấp xong, 98/98 unit tests pass) |
| **`claude_worker.py`** | `terminal` (gọi trực tiếp `--role worker`) | ✅ ĐÃ FIX (commit `44ec6fc`) | Chặn exit 126, bắt buộc `--from-dispatch` hoặc `DISPATCH_TIER_CALLER` | **TIER GATE ENFORCED** (Chặn cửa sau gọi trực tiếp, ép qua Sol Worker) |
| **`guard_broad_grep.py`** | `terminal` (grep -r, rg, find, timeout 60s) | ⚠️ SẮP NÂNG CẤP | `{"action": "block", "rule_id": ..., "message": ..., "severity": "HIGH"}` | **VETO CÂM (SILENT VETO)** (Cần nâng cấp guidance và required_action để thoát kẹt) |

---

## 2. Tác Hại Kiến Trúc Của Veto Câm (Silent Veto Pitfall)
1. **Rơi vào Cognitive Void (Khoảng Trống Nhận Thức):**
   - Khi hook chỉ trả về `[CONSOLE_WINDOW_BLOCKED] Gọi trực tiếp 'python' sẽ mở cửa sổ console; BẮT BUỘC dùng pythonw hoặc powershell -WindowStyle Hidden`, Agent không biết phải sửa code như thế nào (ví dụ: cần thêm `creationflags=subprocess.CREATE_NO_WINDOW`).
   - Agent bắt đầu đoán mò, thử đổi sang `powershell` $\to$ lại bị Cổng Coordinator Default-Deny chém tiếp $\to$ rơi vào vòng xoáy 9-10 turn bại liệt, than thở ném việc cho User.
2. **Ảo Tưởng An Toàn Khi Chỉ Mới Chuẩn Hóa 1 Cổng:**
   - Kỹ sư tưởng rằng hệ thống đã có Action Mandate vì `guard_dispatch_contract.py` đã hoàn thiện. Nhưng khi Agent vấp phải `guard_broad_grep.py` (bị clamp 60s) hoặc `guard_cronjob_safety.py`, Agent vẫn bị tắc nghẽn và biến thành "đứa trẻ khóc nhè".

---

## 3. Triển Khai Thực Tế Đã Kiểm Chứng (Production Verification)

### A. Triển Khai Trên `guard_cronjob_safety.py` (Commit `ba16ae4`)
Đã cấu trúc lại 2 hàm chặn `deny()` và `deny_cron_policy()`:
```python
CONSOLE_GUIDANCE = (
    "Lệnh/script chạy nền hoặc cron trên Windows phải ẩn hoàn toàn cửa sổ console, "
    "nếu không sẽ cướp focus của máy vận hành."
)
CONSOLE_COMMAND = "pythonw <script.py>"
CONSOLE_INSTRUCTION = (
    "Chạy bằng pythonw hoặc powershell -WindowStyle Hidden; trong Python dùng "
    "subprocess với creationflags=subprocess.CREATE_NO_WINDOW (0x08000000), "
    "không dùng os.system/os.popen; sau đó gửi lại lệnh."
)
CRON_GUIDANCE = {
    "FARM_CONTRACT_INVALID": "farm_contract phải là dict hợp lệ với đúng kiểu dữ liệu từng key.",
    "FARM_CONTRACT_UNKNOWN_KEYS": "farm_contract chỉ được chứa các key nằm trong schema cho phép.",
    "FARM_CONTRACT_MISMATCH": "Script có lệnh can thiệp thiết bị Android nên không được khai touches_device=false.",
    "FARM_CONTRACT_MISSING_KEYS": "Script can thiệp thiết bị phải khai đủ các key bắt buộc của farm_contract.",
    "DEVICE_LOCK_REQUIRED": "Script can thiệp thiết bị phải giữ device lock cho từng máy.",
    "ROLLING_MODE_REQUIRED": "Script farm phải chạy mode rolling với số worker nguyên trong 1..50.",
    "WORKER_CAP_EXCEEDED": "max_workers phải là số nguyên trong 1..50.",
    "NO_AGENT_REQUIRED": "Cronjob phải giữ no_agent=true để không tốn LLM mỗi lần chạy.",
    "SCRIPT_REQUIRED": "Cronjob phải trỏ tới một script cụ thể, không được để trống.",
    "PATH_TRAVERSAL": "Đường dẫn script không được chứa '..'.",
    "SCRIPT_EXISTS": "Script của cronjob phải tồn tại trên đĩa trước khi tạo/cập nhật.",
}
CRON_INSTRUCTION = {
    "DEVICE_LOCK_REQUIRED": "Khai farm_contract.device_lock='required' và bọc phần chạm máy trong 'with acquire_device_lock(...)' (automation_core.device_lock), rồi gửi lại.",
    "ROLLING_MODE_REQUIRED": "Khai mode='rolling' và max_workers là số nguyên 1..50, rồi gửi lại.",
}

def _action_mandate(msg: str, rule_id: str, guidance: str, command: str, instruction: str) -> dict:
    return {
        "action": "block",
        "rule_id": rule_id,
        "message": f"{msg}\nHƯỚNG DẪN: {guidance}\nCHỈ DẪN: {instruction}",
        "guidance": guidance,
        "required_action": {
            "command": command,
            "instruction": instruction,
            "description": f"Khắc phục vi phạm {rule_id} theo hướng dẫn rồi gửi lại.",
        },
        "tool": "guard_cronjob_safety",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def _print_payload(payload: dict) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(payload, ensure_ascii=False))
```
- **UTF-8 Immunity:** Tích hợp `sys.stdout.reconfigure(encoding="utf-8")` chống văng lỗi cp1252 trên Windows.
- **Unit Test Coverage:** Thêm 2 unit test kiểm tra bắt buộc phải có `guidance` và `required_action` (`instruction`, `description`). Đạt **98/98 passed (100% PASS)** trong `tests/test_guard_cronjob_safety.py`.

### B. Triển Khai Chốt Chặn Tier Trên `claude_worker.py` (Commit `44ec6fc`)
Khóa chặt cửa sau gọi trực tiếp CLI:
```python
if role == "worker" and not (args.from_dispatch or os.environ.get("DISPATCH_TIER_CALLER") == "dispatch_worker"):
    audit("mechanical_tier_gate_violation", role=role)
    print("⛔ [MECHANICAL TIER GATE VIOLATION]: Direct invocation of claude_worker for role worker is forbidden! "
          "Route through dispatch_worker.py (Tier 1 Sol first).", file=sys.stderr)
    return 126
```
- Phối hợp với `dispatch_worker.py`: Hàm `haiku_cmd` tự động đính kèm `--from-dispatch` khi gọi Claude Haiku ở Tier 3.
- Unit Test Coverage: 4 unit test mới trong `tests/test_claude_worker.py` và assertion trong `tests/test_dispatch_worker.py`, toàn bộ **115/115 passed (100% PASS)**.

---

## 4. Bảng Tra Cứu Quy Chuẩn Action Mandate 4 Thành Phần
Khi thiết kế bất kỳ hook chặn nào trong tương lai, BẮT BUỘC trả về đúng 4 thành phần sau:
1. `rule_id`: Định danh duy nhất (ví dụ: `DEVICE_LOCK_REQUIRED`, `CONSOLE_WINDOW_BLOCKED`).
2. `message`: Bắt đầu bằng tiền tố `[RULE_ID] <lý_do_ngắn_gọn>`, kèm `HƯỚNG DẪN:` và `CHỈ DẪN:`.
3. `guidance`: Giải thích tại sao cấm và nguyên tắc kiến trúc của hệ thống.
4. `required_action`: Cung cấp `command` (nếu có lệnh thoát $O(1)$) hoặc `instruction` (chỉ dẫn sửa code/contract cụ thể) kèm `description`.
