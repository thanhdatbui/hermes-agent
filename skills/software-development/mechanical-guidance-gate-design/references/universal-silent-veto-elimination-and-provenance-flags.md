# Universal Silent Veto Gate Elimination & Provenance Flag Enforcement

## 1. Silent Veto Gate vs. Guidance Gate Architecture

### Veto Gate Câm (Silent Veto Gate) — Kẻ Thù Số 1 Của AI Agent
- **Định nghĩa:** Một hook hoặc guard chỉ biết trả về `{"action": "block", "message": "..."}` hoặc thoát `sys.exit(1)` kèm dòng thông báo cấm cộc lốc, không cung cấp lý do kiến trúc (`guidance`) và không có lệnh/chỉ dẫn khắc phục (`required_action`).
- **Hậu quả hành vi trên LLM Agent:**
  1. *Vòng 1–3:* Đoán mò sửa vụn vặt, hao phí token và số lượt turns.
  2. *Vòng 4–6:* Tìm cách lách luật, đi cửa sau (như gõ trực tiếp CLI worker qua terminal để né gate của `delegate_task`).
  3. *Vòng 7–8:* Bế tắc, sinh ra phản xạ tiêu cực (phân trần, khóc lóc, biện minh).
  4. *Vòng 9–10:* Tự dán nhãn `BLOCKED` vô cớ, hoặc đẩy việc ngược lại cho Operator ("nhờ anh mở terminal ngoài gõ lệnh hộ em").

### Guidance Gate (Cổng Chỉ Dẫn có Action Mandate O(1))
- **Quy chuẩn bắt buộc:** Mọi điểm chặn trong gate/hook BẮT BUỘC phải phát sinh payload Action Mandate chuẩn:
  ```json
  {
    "action": "block",
    "rule_id": "<RULE_ID>",
    "message": "[<RULE_ID>] <lý_do>\nHƯỚNG DẪN: <guidance>\nCHỈ DẪN: <instruction>",
    "guidance": "<bài_học_kiến_trúc_và_lý_do_cấm>",
    "required_action": {
      "command": "<lệnh_thoát_O1_nếu_có>",
      "instruction": "<chỉ_dẫn_hành_động_cụ_thể>",
      "description": "<mô_tả_khắc_phục>"
    },
    "tool": "<guard_name>",
    "timestamp": "<UTC_ISO_TIMESTAMP>"
  }
  ```

---

## 2. Case Study: Nâng Cấp guard_cronjob_safety.py & hooks/guard_broad_grep.py

### A. guard_cronjob_safety.py
- **Hiện trạng cũ:** `deny()` và `deny_cron_policy()` in JSON thô `{"action": "block", "message": msg}`.
- **Nâng cấp Guidance:**
  - Bổ sung bảng tra cứu `CRON_GUIDANCE` và `CRON_INSTRUCTION` theo từng `rule_id` (`DEVICE_LOCK_REQUIRED`, `ROLLING_MODE_REQUIRED`, `SCRIPT_EXISTS`, `NO_AGENT_REQUIRED`, v.v.).
  - Bổ sung `CONSOLE_GUIDANCE`, `CONSOLE_COMMAND`, `CONSOLE_INSTRUCTION` hướng dẫn dùng `pythonw` hoặc `powershell -WindowStyle Hidden` và cờ `creationflags=subprocess.CREATE_NO_WINDOW (0x08000000)`.
  - Tự động gọi `sys.stdout.reconfigure(encoding="utf-8")` trong `_print_payload()` để chống crash `cp1252` trên Windows console.

### B. hooks/guard_broad_grep.py
- **Hiện trạng cũ:** `block()` chỉ in payload telemetry phẳng, không có trường guidance.
- **Nâng cấp Guidance:**
  - Bổ sung `GUIDANCE_MAP` và `INSTRUCTION_MAP` đầy đủ cho cả 10 mã vi phạm: `GUARD_DANGEROUS_ROOT`, `GUARD_RECURSIVE_GREP`, `GUARD_RECURSIVE_RG`, `GUARD_PYTHON_WALKER`, `GUARD_POWERSHELL_SCAN`, `GUARD_FIND_SCAN`, `GUARD_FOREGROUND_TIMEOUT_MISSING`, `GUARD_FOREGROUND_TIMEOUT_INVALID`, `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`, `GUARD_SEARCH_FILES_ROOT`.
  - Trả về payload cấu trúc có `guidance` và `required_action` (`instruction` + `description`), đồng thời nối trực tiếp `HƯỚNG DẪN:` và `CHỈ DẪN:` vào trường `message`.

---

## 3. Khóa Cơ Học Cửa Sau Terminal (Provenance Flag: --from-dispatch)

### Lỗ Hổng Lách Cổng (Terminal Backdoor)
- Dù `guard_dispatch_contract.py` đã chặn `delegate_task` và ép đi qua `dispatch_worker.py` (Tier 1 Sol Worker), Agent vẫn có thể đi đường tắt bằng cách gọi trực tiếp `python D:/Taadaa/tools/claude_worker.py --role worker ...` vào công cụ `terminal` (vì `claude_worker.py` nằm trong whitelist timeout của terminal).
- Điều này vi phạm nghiêm trọng tôn ti Worker Tiering và làm lãng phí quota Claude.

### Giải Pháp Khóa Chặt Bằng Cờ Xuất Xứ (Provenance Flag)
- Trong `claude_worker.py`: Thêm đối số CLI `--from-dispatch`.
- Khi `role == "worker"`, bắt buộc phải có cờ `--from-dispatch` hoặc biến môi trường `DISPATCH_TIER_CALLER == "dispatch_worker"`.
- Nếu phát hiện gọi trực tiếp đơn lẻ không qua dispatch gateway:
  ```text
  ⛔ [MECHANICAL TIER GATE VIOLATION]: Direct invocation of claude_worker for role worker is forbidden!
  HƯỚNG DẪN: Tier 1 là Sol Web Worker (100% Free qua OmniRoute :20129). Bắt buộc thi công qua gateway dispatch_worker.py để ưu tiên Sol và Agy trước, cấm đốt quota Claude trực tiếp.
  LỆNH THOÁT O(1): python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<prompt>"
  ```
  Thoát ngay lập tức với `exit 126`.
- Trong `dispatch_worker.py`: `haiku_cmd` tự động truyền thêm cờ `--from-dispatch` khi fallback Tier 3 được kích hoạt hợp lệ.
