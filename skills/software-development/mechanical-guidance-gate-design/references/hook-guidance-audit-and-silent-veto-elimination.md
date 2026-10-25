# Universal Hook Guidance Audit & Silent Veto Elimination (Kiểm Toán Độ Phủ Action Mandate & Triệt Tiêu Veto Câm)

## 1. Bối cảnh & Hiện Tượng Thực Tế (Sự Cố 2026-10-25)
Trong quá trình vận hành hệ thống AI Coordinator - Worker, User đặt câu hỏi cốt lõi:
*"Hook cơ học đã tích hợp guide của hook guide để chỉ dẫn agent chưa?"*

Qua đối soát toàn diện hệ thống hooks (`guard_dispatch_contract.py`, `guard_cronjob_safety.py`, `hooks/guard_broad_grep.py`, `claude_worker.py`), phát hiện sự bất đối xứng nghiêm trọng về độ phủ của chuẩn Action Mandate (Rule 1 & Rule 26 trong skill `mechanical-guidance-gate-design`):

| Hook Kiểm Soát | Vị Trí Chặn | Trạng Thái Guidance | Cấu Trúc Trả Về | Đánh Giá Chuẩn Rule 1 |
| :--- | :--- | :--- | :--- | :--- |
| **`guard_dispatch_contract.py`** | `delegate_task` (Create, Investigate, Edit) | ✅ ĐẦY ĐỦ | `rule_id`, `message`, `guidance`, `required_action` (`command`, `instruction`, `description`), `next_action` | **CHUẨN ACTION MANDATE** (Agent có ngay lệnh $O(1)$ để chạy tiếp) |
| **`guard_cronjob_safety.py`** | `cronjob` (create, update), `terminal` (background) | ❌ THIẾU | `{"action": "block", "message": "[CONSOLE_WINDOW_BLOCKED] ..."}` | **VETO CÂM (SILENT VETO)** (Chỉ quăng lỗi cộc lốc, không có guidance, không có next action) |
| **`guard_broad_grep.py`** | `terminal` (grep -r, rg, find, timeout 60s) | ❌ THIẾU | `{"action": "block", "rule_id": ..., "message": ..., "severity": "HIGH"}` | **VETO CÂM (SILENT VETO)** (Thiếu guidance kiến trúc và required_action để thoát kẹt) |
| **`claude_worker.py`** | `terminal` (gọi trực tiếp `--role worker`) | ⚠️ SƠ KHAI | `⛔ [MECHANICAL TIER GATE VIOLATION]...` ra stderr, exit 126 | **CHẶN ĐÚNG CƠ HỌC NHƯNG THIẾU LỆNH MẪU** (Chưa in lệnh thoát $O(1)$ vào `dispatch_worker.py`) |

---

## 2. Tác Hại Kiến Trúc Của Veto Câm (Silent Veto Pitfall)
1. **Rơi vào Cognitive Void (Khoảng Trống Nhận Thức):**
   - Khi hook chỉ trả về `[CONSOLE_WINDOW_BLOCKED] Gọi trực tiếp 'python' sẽ mở cửa sổ console; BẮT BUỘC dùng pythonw hoặc powershell -WindowStyle Hidden`, Agent không biết phải sửa code như thế nào (ví dụ: cần thêm `creationflags=subprocess.CREATE_NO_WINDOW`).
   - Agent bắt đầu đoán mò, thử đổi sang `powershell` $\to$ lại bị Cổng Coordinator Default-Deny chém tiếp $\to$ rơi vào vòng xoáy 9-10 turn bại liệt, than thở ném việc cho User.
2. **Ảo Tưởng An Toàn Khi Chỉ Mới Chuẩn Hóa 1 Cổng:**
   - Kỹ sư tưởng rằng hệ thống đã có Action Mandate vì `guard_dispatch_contract.py` đã hoàn thiện. Nhưng khi Agent vấp phải `guard_broad_grep.py` (bị clamp 60s) hoặc `guard_cronjob_safety.py`, Agent vẫn bị tắc nghẽn và biến thành "đứa trẻ khóc nhè".

---

## 3. Quy Chuẩn Khắc Phục Chuẩn Hóa (Universal Action Mandate Rollout)

### Tiêu Chuẩn 1: Triệt Tiêu 100% Veto Câm Qua `action_mandate.emit_block`
Mọi hàm chặn trong mọi hook BẮT BUỘC phải sử dụng module `action_mandate.py` hoặc sinh payload JSON chứa tối thiểu 4 trường:
1. `rule_id`: Mã định danh vi phạm duy nhất.
2. `message`: Thông báo lỗi rõ ràng kèm lý do.
3. `guidance`: Hướng dẫn kiến trúc giải thích TẠI SAO hành vi đó bị cấm và nguyên tắc của hệ thống.
4. `required_action`: Cung cấp cụ thể:
   - `command`: Câu lệnh $O(1)$ copy-paste chạy được ngay nếu có (đã interpolate sẵn đường dẫn thực tế).
   - `instruction`: Chỉ dẫn từng bước cụ thể nếu là thao tác sửa code / cấu hình.
   - `description`: Mô tả mục đích của hành động khắc phục.

### Tiêu Chuẩn 2: Mẫu Nâng Cấp Chuẩn Cho `guard_cronjob_safety.py`
```python
# Thay vì chỉ print message cụt lủn:
def deny_console_window(reason: str, command: str = "") -> None:
    emit_block(
        rule_id="CONSOLE_WINDOW_BLOCKED",
        reason=reason,
        guidance="Các tiến trình chạy ngầm (background/cron) trên Windows bắt buộc phải ẩn cửa sổ console CMD để tránh cướp focus/chuột của User.",
        instruction="Nếu là script Python: Thêm creationflags=subprocess.CREATE_NO_WINDOW vào toàn bộ lệnh subprocess.run/Popen. Nếu là Cronjob: Đăng ký với no_agent=True và chỉ truyền tên script trần.",
        tool_name="terminal",
        target=command,
    )
```

### Tiêu Chuẩn 3: Mẫu Nâng Cấp Chuẩn Cho `guard_broad_grep.py`
```python
# Khi clamp timeout 60s:
def block_foreground_timeout(cmd: str, timeout: float) -> None:
    emit_block(
        rule_id="GUARD_FOREGROUND_TIMEOUT_EXCEEDED",
        reason=f"Lệnh terminal foreground có timeout={timeout}s > 60s!",
        guidance="Lệnh foreground bị giới hạn cứng <= 60s để chống treo session. Các công cụ chạy lâu được phê duyệt (dispatch_worker.py, closeout_gate.py, pytest, transfer_game_lan.py) được phép chạy tới 360s.",
        command=f"python D:/Taadaa/tools/dispatch_worker.py --workdir . '{cmd[:100]}'",
        instruction="Hạ timeout xuống <= 60s, hoặc nếu là tác vụ batch/sync kéo dài thì chuyển sang chạy qua Hermes Cron Scheduler (no_agent=True) hoặc dispatch_worker.py.",
        tool_name="terminal",
        target=cmd,
    )
```

### Tiêu Chuẩn 4: Chốt Chặn Tier Trong `claude_worker.py`
Khi chặn gọi trực tiếp `claude_worker.py --role worker`:
```python
if role == "worker" and not (args.from_dispatch or os.environ.get("DISPATCH_TIER_CALLER") == "dispatch_worker"):
    audit("mechanical_tier_gate_violation", role=role)
    target_arg = f"--file '{args.file}'" if args.file else ""
    prompt_arg = shlex.quote(args.prompt or "")
    suggested_cmd = f"python D:/Taadaa/tools/dispatch_worker.py {target_arg} {prompt_arg}".strip()
    print(
        f"⛔ [MECHANICAL TIER GATE VIOLATION]: Direct invocation of claude_worker for role worker is forbidden!\n"
        f"HƯỚNG DẪN: Tier 1 là Sol Worker (:20129, Miễn phí 100%). Bắt buộc đi qua dispatch_worker.py để ưu tiên Sol trước khi fallback sang Claude.\n"
        f"LỆNH THOÁT O(1): {suggested_cmd}",
        file=sys.stderr,
    )
    return 126
```
