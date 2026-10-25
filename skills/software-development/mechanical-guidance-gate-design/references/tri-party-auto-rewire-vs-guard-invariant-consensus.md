# Tri-Party Review Consensus: Auto-Rewire vs Guard Invariants

> **Tham chiếu cốt lõi:** Hội chẩn 3 bên (Advisor Sol :20129 + Claude CLI `claude -p` + Hermes Coordinator) ngày 2026-10-25.

---

## 1. Nguyên Tắc Nền Tảng: Safe Auto-Repair vs Policy Bypass

Auto-Rewire là cơ chế chuyển hướng hành vi của Agent từ đường đi vi phạm sang đường đi hợp lệ. Tuy nhiên, **Auto-Rewire chỉ được phép thay đổi cơ chế thực thi an toàn, TUYỆT ĐỐI KHÔNG ĐƯỢC làm suy yếu quyền hạn, bypass invariant hoặc che giấu lỗi**.

### 3 Xung đột Cốt lõi Cần Tránh:
1. **Block -> Rewire:** Nếu GuardGate cấm hành động theo policy (ví dụ: cấm can thiệp thiết bị farm ngoài ca), việc chuyển sang worker khác để làm vẫn là vi phạm. Rewire chỉ hợp lệ khi bản thân ý định là hợp pháp nhưng Agent dùng sai cú pháp / công cụ.
2. **Clamp -> Continue:** Kẹp trần ngân sách (budget clamp) là hạn chế tiêu hao tài nguyên, không phải giấy phép bỏ qua điều kiện nghiệm thu.
3. **Wrapper -> False Assurance:** Việc tự bọc wrapper không bảo đảm lock, timeout hay closeout thực sự thành công nếu không có kiểm chứng fail-closed.

---

## 2. Tiêu Chuẩn Thẩm Định 8 Guard Hooks Cụ Thể

| Hook / Vi phạm | Phán quyết Hội chẩn | Cơ chế Rewire & Ràng buộc Bắt buộc |
|:---|:---:|:---|
| **`subagent_edit_blocked`** | ⚠️ Có điều kiện | Khi Coordinator gọi `delegate_task` cho task sửa code: Tự động rewire sang `dispatch_worker.py` (O(1)). Bắt buộc giữ nguyên scope $\le 2$ files, $\le 30$ dòng, in rõ tag `[AUTO-REWIRED: delegate_task -> dispatch_worker]`. Cấm rewire âm thầm khiến agent ảo tưởng. |
| **`investigate`** | ⚠️ Rủi ro che giấu | Khi task khảo sát qua `delegate_task` vượt 8 calls: Kẹp trần `budget = 8`. **Bắt buộc gắn tag `BUDGET_CLAMPED (partial data)`** vào kết quả trả về để Coordinator không kết luận phiến diện trên dữ liệu bị cắt cụt. Giới hạn tính trên tổng task, chống loophole chia nhỏ lần gọi. |
| **`DANGEROUS_ROOT` & `SEARCH_FILES_ROOT`** | ✅ Chuẩn | Giữ nguyên HARD BLOCK đối với `os.walk`, `rglob`, `glob(recursive=True)` hoặc `search_files` trên root. Trả về `required_action` là lệnh copy-paste đường dẫn hẹp đã resolve canonical path (chống symlink và `..`). |
| **`DEVICE_LOCK_REQUIRED`** | 🚨 Rủi ro cao | **CHỈ auto-wrap `with_device_lock.py` cho lệnh ĐỌC** (`dumpsys`, `screencap`, `uiautomator dump`). **CẤM auto-wrap cho lệnh GHI/can thiệp** (`input tap`, `pm clear`, `reboot`, `force-stop`) vì có thể vô tình hợp thức hóa việc cướp quyền ca chính hoặc tap bừa. Lệnh ghi thiếu lock -> HARD BLOCK ngay. |
| **`FOREGROUND_TIMEOUT`** | ⚠️ Có điều kiện | Kẹp `timeout=30/60s` cho lệnh terminal foreground đọc/kiểm tra. Cấm kill giữa chừng các lệnh ghi có side-effect (`adb install`, `git push`). Chuyển sang `background=True` **bắt buộc kèm `notify_on_complete=True`** để tránh agent mất dấu và quay lại polling. |
| **`CLOSEOUT_DISCIPLINE`** | ✅ Tốt & An toàn | Tự động inject lệnh chạy `closeout_gate.py` trước khi `git push`. Bắt buộc fail-closed (`closeout_gate.py && git push`) và thẩm định trên HEAD commit SHA tươi mới nhất, cấm dùng artifact cũ. |
| **`CONSOLE_WINDOW`** | ✅ Chuẩn | Ép cờ `CREATE_NO_WINDOW` trên tiến trình background chạy ngầm để chống chớp nháy cướp focus màn hình Admin. Không áp dụng cho công cụ GUI hoặc cần console stdin thật (`scrcpy`). |

---

## 3. Ba Quy Tắc Bảo Vệ Tối Thượng (Invariants Khi Triển Khai Rewire)

1. **Minh bạch Provenance:**
   Mọi hành động Auto-Rewire phải xuất log và thẻ rõ ràng: `[AUTO-REWIRED: <nguồn> → <đích>]`.
2. **Fail-Closed khi Mơ hồ:**
   Nếu việc parse câu lệnh shell không bảo đảm an toàn 100% (đặc biệt là lệnh parse serial thiết bị), lập tức rơi về HARD BLOCK gốc, cấm suy đoán.
3. **Chống Vòng Lặp Vô Tận (Loop Escalation):**
   Nếu cùng một rule bị Auto-Rewire quá 3 lần liên tiếp trong một phiên làm việc, hệ thống tự động leo thang thành HARD BLOCK để ngăn chặn Agent loop ngầm vô tận.

---

## 4. Giao Thức Heartbeat Telemetry & Kiểm Soát Đa Session

- **Heartbeat Telemetry Protocol:** Các cron watchdogs tại `D:/Taadaa` bắt buộc xuất file telemetry tại `D:/Taadaa/runtime/cron_health/<script_name>.json` với các trường: `script_name`, `last_end` (ISO-8601 UTC), `status` (`NOMINAL` hoặc `ANOMALY`), `anomalies` (mảng rỗng hoặc danh sách mã lỗi).
- **Multi-Session Disjoint Verification:** Khi có nhiều session cùng thao tác trên repo:
  - Phân loại rõ ràng: Session A (Source code hooks/workers) vs Session B (Runtime state telemetry/health).
  - Sử dụng `session_search` và `git status -s` để xác nhận quyền sở hữu hunk/path, loại trừ nguy cơ đè code lẫn nhau.
