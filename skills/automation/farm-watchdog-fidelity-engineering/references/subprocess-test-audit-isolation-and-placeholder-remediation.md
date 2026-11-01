# Subprocess Test Audit Isolation & Guard Block Death Spiral Remediation

## 1. Context & Operational Symptoms
Trong các đợt đối soát 6H (`gate_compliance_watchdog.py`), hệ thống thường xuất hiện 2 cụm triệu chứng nghiêm trọng:
1. **Bão lỗi ảo từ Test Mock (Phantom Test Flood):** Gate G8 (Cronjob Window Guard) đột ngột nổ 44 vi phạm liên tiếp (`CRON_AGENT_POLICY`, `FARM_CONTRACT_INVALID`, `WORKER_CAP_EXCEEDED`, `NO_AGENT_REQUIRED`), đẩy toàn bộ báo cáo về trạng thái `FAIL` dù farm không có sự cố vận hành nào.
2. **Agent loay hoay đập đầu vào rào chắn (Guard Block Death Spiral):** Sau khi Guard chặn một lệnh không hợp lệ, Agent liên tục thử các lệnh cấm khác (`os.walk` -> `find` -> `grep -rn` -> `adb shell input tap`), gây ra 20-30 lượt chặn liên tiếp trong vòng 30 phút.

---

## 2. Root Cause Analysis

### A. Subprocess Monkeypatch Leak
- Các bộ test guard (`test_guard_cronjob_safety.py`) khi test tính năng thường kiểm thử bằng cách gọi subprocess:
  ```python
  proc = subprocess.run([sys.executable, str(HOOK_PATH)], input=json.dumps(payload))
  ```
- **Điểm mù:** `pytest` `monkeypatch.setattr(mod, "AUDIT_LOG", tmp_path)` chỉ có hiệu lực **in-process**. Khi chạy tiến trình con độc lập qua `subprocess.run()`, tiến trình mới không kế thừa monkeypatch mà ghi thẳng toàn bộ payload giả lập (`attacker_injected_key`, `farm_burst.py`, `max_workers=100`, `no_agent=false`) vào file audit thật của production (`console_block_audit.jsonl`).
- Do các chuỗi assert trong test không chứa từ khóa `"pytest"`, bộ lọc watchdog xem đây là vi phạm thật của Agent.

### B. Chỉ đường tù mù với Placeholder `<N>` & Vắng bóng Auto-Rewire
- Khi Agent gõ lệnh ADB trần (ví dụ `adb -s 9885b64957334f5a46 shell "pm list packages"`), Hook chặn và hướng dẫn:
  `Bọc lệnh qua: python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>`
- **Hậu quả:** Agent không biết serial `9885b64957334f5a46` ứng với Máy số mấy (`<N>`). Vì không biết số máy, Agent hoảng loạn gõ tiếp lệnh trần khác hoặc thử bấm tay `adb shell input tap`, dẫn tới chuỗi vi phạm liên hoàn.

---

## 3. Kiến Trúc Khắc Phục Cơ Giới Hóa (Canonical Solution)

### 1. Cách Ly Audit Log Trong Test Subprocess
Mọi hook ghi audit telemetry bắt buộc hỗ trợ biến môi trường override:
```python
AUDIT_LOG = Path(os.environ.get("AUDIT_LOG_PATH", "D:/Taadaa/runtime/audit_logs/console_block_audit.jsonl"))
```
Trong hàm `run_hook` của test suite, bắt buộc inject đường dẫn file tạm:
```python
def run_hook(payload: dict) -> dict:
    env = os.environ.copy()
    env["AUDIT_LOG_PATH"] = str(Path(tempfile.gettempdir()) / "cron_audit_test.jsonl")
    proc = subprocess.run([sys.executable, str(HOOK_PATH)], input=json.dumps(payload), env=env, ...)
```

### 2. Dual-Defense: Mở Rộng `TEST_MOCK_SIGNATURES` trong Watchdog
Bổ sung các định dạng payload giả lập của test vào danh sách loại trừ của `gate_compliance_watchdog.py`:
```python
TEST_MOCK_SIGNATURES = (
    ...
    "cron_agent_policy", "farm_contract", "fake_module", "attacker_injected_key",
    "farm_burst", "test_ssh_powershell", "unsafe_ssh.py", "bad_runner.py",
    "powershell -command get-process",
)
```

### 3. Tra Cứu Serial Ra Số Máy O(1) & Auto-Rewire Thay Vì Chặn
1. **DAL Mapping O(1):** `farm_db.get_machine_by_serial(serial)` tra cứu trực tiếp từ bảng `machines` trong SQLite `farm_master.db`.
2. **Auto-Rewire Cho Lệnh Đọc:** Khi Agent gõ lệnh ADB đọc (`getprop`, `pm list`, `dumpsys`, `screencap`, `pull`):
   Hook tự động rewrite sang:
   `python D:/Taadaa/tools/with_device_lock.py --machine {mach_id} -- {cmd}`
   -> Lệnh chạy an toàn ngay lập tức, Agent không bị chặn, không tốn token lặp lại.
3. **Triệt Tiêu Placeholder `<N>`:** Khi bắt buộc phải block (với lệnh can thiệp ghi/xóa), thông báo guidance phải in thẳng số máy thực tế:
   `python D:/Taadaa/tools/with_device_lock.py --machine 1 -- ...` (thay hẳn chữ `<N>` thành `1`).
4. **Action Mandate Cụ Thể Khi Cấm Bấm Tay ADB (`GUARD_MANUAL_ADB_TAP`):**
   Hướng dẫn rõ 2 bước thay vì cấm suông:
   - Thu evidence: `python D:/Taadaa/tools/inspect_machine.py {mach_id}`
   - Tự động đóng dialog lỗi/crash app: `python D:/Taadaa/tools/farm_idle_screen_and_app_healer.py --machine {mach_id}`
