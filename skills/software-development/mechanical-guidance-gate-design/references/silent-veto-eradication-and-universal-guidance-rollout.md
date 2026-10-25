# Silent Veto Gate Eradication & Universal Guidance Gate Rollout

## 1. Bản Chất Kiến Trúc: Veto Gate vs. Silent Veto vs. Guidance Gate

### 1.1 Veto Gate (Cổng Phủ Quyết Cơ Học)
- Là chốt chặn ở các tầng tiền kiểm (pre-tool hook, middleware, git hook, closeout gate) có quyền lực ngắt ngay lập tức khi phát hiện hành vi vi phạm quy tắc bất biến (quét đĩa diện rộng, bung cửa sổ đen CMD, bypass tier worker, đọc file khổng lồ).

### 1.2 Silent Veto Gate (Kẻ Thù Số 1 Gây Bại Liệt & Khóc Lóc)
- **Đặc điểm:** Chặn đứng hành vi nhưng chỉ in một thông báo lỗi cộc lốc hoặc mã lỗi `exit 1` / `{"action": "block", "message": "Denied"}` mà **hoàn toàn không cung cấp đường bay tiếp theo**.
- **Bi kịch Khoảng Trống Nhận Thức (Cognitive Void Escalation - 4 Giai Đoạn Suy Thoái):**
  1. *Giai đoạn 1 (Vòng 1–3):* Agent thử các biến thể cú pháp vụn vặt, mò mẫm vô định.
  2. *Giai đoạn 2 (Vòng 4–6):* Agent tìm cách "đi cửa sau" (như gõ tắt CLI qua terminal để né hook `delegate_task`).
  3. *Giai đoạn 3 (Vòng 7–8):* Agent rơi vào bế tắc, sinh ra phản xạ **khóc lóc, phân trần sớ dài, biện minh cho sự bất lực**.
  4. *Giai đoạn 4 (Vòng 9–10):* Agent tự dán nhãn `BLOCKED` giả mạo hoặc tệ hại nhất là **đẩy việc cho User** (*"Anh mở terminal ngoài gõ lệnh hộ em"*).

### 1.3 Guidance Gate (Cổng Chỉ Dẫn Có Action Mandate O(1) - Chuẩn Hóa Rule 1 & Rule 26)
- **Đặc điểm:** Bất kỳ khi nào chặn, gate BẮT BUỘC phải trả về 3 thành phần cấu trúc:
  1. `rule_id`: Mã định danh vi phạm duy nhất.
  2. `guidance`: Bài học kiến trúc giải thích nguyên nhân cấm (tại sao cấm, tác hại đối với hệ thống).
  3. `required_action`: Cung cấp sẵn một câu lệnh `command` chạy được ngay ở turn tiếp theo hoặc `instruction` chỉ dẫn từng bước cụ thể.
- **Tác dụng:** Agent khi chạm tường sẽ lập tức đọc được lệnh thoát O(1), tự động bẻ lái (pivot) sang đường bay hợp lệ mà không cần phân trần hay làm phiền User.

---

## 2. Chuẩn Hóa Schema Action Mandate Toàn Diện

Mọi hook và gate trong hệ sinh thái Taadaa / Hermes bắt buộc phải xuất payload theo schema sau:

```json
{
  "action": "block",
  "rule_id": "<RULE_ID_DUY_NHẤT>",
  "message": "[<RULE_ID>] <lý_do_vi_phạm>\nHƯỚNG DẪN: <guidance_kiến_trúc>\nCHỈ DẪN: <chỉ_dẫn_thoát_O1>",
  "guidance": "<giải_thích_tại_sao_cấm_và_nguy_cơ_hệ_thống>",
  "required_action": {
    "command": "<lệnh_copy_paste_chạy_ngay_hoặc_rỗng>",
    "instruction": "<hành_động_cần_thực_hiện>",
    "description": "<mô_tả_khắc_phục>"
  },
  "tool": "<tên_tool_bị_chặn>",
  "timestamp": "<UTC_ISO_8601>"
}
```

### Chống Sập Encoding Trên Windows (sys.stdout.reconfigure):
Mọi script hook/gate Python trên Windows chạy với stdout mặc định là `cp1252`. Khi in tiếng Việt có dấu (`HƯỚNG DẪN:`, `CHỈ DẪN:`), Python sẽ ném `UnicodeEncodeError` và crash ngầm, làm hook bị treo im lặng.
**BẮT BUỘC:** Gọi hàm bọc an toàn trước khi in JSON:
```python
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
sys.exit(0)
```

---

## 3. Bản Đồ 11 Hook & Gate Đã Được Nâng Cấp Toàn Diện (Sự Cố 2026-10-25)

| STT | Hook / Gate | Tầng Can Thiệp | Rule IDs Đã Chuẩn Hóa Guidance | Lệnh Thoát / Chỉ Dẫn O(1) |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `hooks/guard_broad_grep.py` | Pre-tool: `terminal`, `search_files` | `GUARD_DANGEROUS_ROOT`, `GUARD_RECURSIVE_GREP`, `GUARD_RECURSIVE_RG`, `GUARD_PYTHON_WALKER`, `GUARD_POWERSHELL_SCAN`, `GUARD_FIND_SCAN`, `GUARD_FOREGROUND_TIMEOUT_*`, `GUARD_SEARCH_FILES_ROOT` | Chỉ dẫn thu hẹp path, dùng grep trên 1 file hoặc đặt timeout <= 60s/360s. |
| **2** | `guard_cronjob_safety.py` | Pre-tool: `cronjob`, `terminal` background | `CONSOLE_WINDOW`, `NO_AGENT_REQUIRED`, `SCRIPT_EXISTS`, `DEVICE_LOCK_REQUIRED`, `ROLLING_MODE_REQUIRED`, `FARM_CONTRACT_*` | Chỉ dẫn dùng `pythonw` / `powershell -WindowStyle Hidden`, `creationflags=CREATE_NO_WINDOW`, `with acquire_device_lock(...)`. |
| **3** | `claude_worker.py` | CLI Worker Execution (Tier 3) | `mechanical_tier_gate_violation` | Lệnh thoát O(1): `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<prompt>"`. |
| **4** | `hooks/guard_dispatch_contract.py` | Pre-tool: `delegate_task` | `HARD_GATE_3_CODE_EDIT_DISPATCH_BLOCKED`, `HARD_GATE_3_INVESTIGATE_*`, `HARD_GATE_3_CREATE_*` | Lệnh thoát O(1): Ghép chuỗi an toàn qua `shlex.join` gọi `dispatch_worker.py`. |
| **5** | `hooks/guard_read_file_size.py` | Pre-tool: `read_file` | `GUARD_READ_FILE_SIZE_EXCEEDED` | Lệnh thoát O(1): `tail -n 200 <path>` hoặc `read_file(..., limit=200)`. |
| **6** | `hooks/guard_pytest_scope.py` | Pre-tool: `terminal` | `GUARD_PYTEST_SCOPE_BROAD` | Lệnh thoát O(1): `python -m pytest <path/to/test_file.py> -q`. |
| **7** | `hooks/guard_model_drift.py` | Pre-tool: `terminal` | `GUARD_MODEL_DRIFT` | Lệnh thoát O(1): `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --json-output`. |
| **8** | `hooks/guard_closeout_discipline.py` | Pre-tool: `terminal`, `clarify` | `GUARD_CLOSEOUT_DISCIPLINE`, `GUARD_CLOSEOUT_DISCIPLINE_CLARIFY_*` | Chỉ dẫn giữ nguyên working tree, cấm panic rollback, gọi reviewer remediate thay vì clarify. |
| **9** | `hooks/guard_device_bulkhead.py` | Pre-tool: `terminal` | `GUARD_MANUAL_ADB_TAP`, `GUARD_DEVICE_LOCK_REQUIRED`, `GUARD_AMBIGUOUS_ADB_COMMAND`, `GUARD_DEVICE_CIRCUIT_BREAKER`, `GUARD_DEVICE_FOREGROUND_TIMEOUT` | Lệnh thoát O(1): `with_device_lock.py --machine <N> -- ...` hoặc thêm `-s <serial>`. |
| **10**| `done_gate.py` | CLI Done Verification | `UI_POLICY_VIOLATED`, `GPM_CANARY_MISSING`, `DEVICE_CANARY_REQUIRED`, `STRICT_DEVICE_FAIL` | Lệnh thoát O(1): `python D:/Taadaa/tools/done_gate.py --task-type automation --canary-file <path>`. |
| **11**| `hooks/pre-push.sh` | Git Hook: `pre-push` | `PRE_PUSH_GATE_CHECK_FAILED` | Lệnh thoát O(1): `python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/tools --base HEAD~1 --json-output`. |
