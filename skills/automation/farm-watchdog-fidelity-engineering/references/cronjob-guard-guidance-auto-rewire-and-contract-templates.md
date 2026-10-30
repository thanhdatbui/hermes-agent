# Cronjob Guard Guidance, Auto-Rewire & Farm Contract Templates

## 1. Bối Cảnh & Sự Cố Bão Vi Phạm G8 (391 Lượt Chặn / 6H)
Trong các báo cáo 6H (`gate_compliance_watchdog.py`), Gate G8 (*Cronjob Window Guard*) có thể bùng phát hàng trăm lượt chặn liên tiếp (ví dụ 391 vi phạm: 103 `CRON_AGENT_POLICY`, 99 `FARM_CONTRACT_INVALID`, 63 `WORKER_CAP_EXCEEDED`, 45 `NO_AGENT_REQUIRED`, 36 `FARM_CONTRACT_MISSING_KEYS`):

### Nguyên nhân cốt lõi (Block Death Spiral):
1. **Tool Parameter Default Mismatch:** Định nghĩa công cụ `cronjob` trong Hermes mặc định `no_agent=False` (LLM-driven prompt job). Khi Agent tạo cronjob chạy script nền, Agent thường bỏ qua tham số này $\to$ Hook `guard_cronjob_safety.py` chặn với lý do `CRON_AGENT_POLICY_BLOCKED`.
2. **Guidance Mơ Hồ & Thiếu Pre-filled Command:** Thông báo lỗi chỉ trả về text chung chung (*"Cronjob phải tuân thủ policy no_agent + farm_contract hợp lệ"*) và trường `command` trong `required_action` bị để trống `""`.
3. **Đoán Mò Thuộc Tính (Blind Guessing Chain):** Không có schema mẫu, Agent tự bịa cấu trúc `farm_contract` $\to$ liên tiếp kích hoạt các chốt chặn `FARM_CONTRACT_INVALID`, `FARM_CONTRACT_UNKNOWN_KEYS`, `WORKER_CAP_EXCEEDED` (>50 worker), `ROLLING_MODE_REQUIRED`.

---

## 2. Ranh Giới Cơ Giới: Auto-Rewire vs Active Pivot

Áp dụng **3 Tiêu Chí Vàng** (Deterministic • Authority-Narrowing • Transparent):

### A. Tầng Auto-Rewire (0-turn In-Place Repair):
- **Điều kiện:** Khi Agent gọi `cronjob(action="create"|"update")` đã có tham số `script` nhưng `no_agent` bị thiếu hoặc là `False`.
- **Cơ chế:** Hook tự động tiêm ngầm `no_agent=True` vào `tool_input` / `updated_args`, trả về receipt `NO_AGENT_AUTO_INJECTED`.
- **Lý do thỏa mãn:** Biến đổi tất định 100%, bảo toàn ý định chạy script của Agent, thu hẹp quyền hạn (không cho LLM chạy định kỳ gây tốn token và lag gateway).

### B. Tầng Active Pivot (Fail-Fast kèm Pre-filled Contract):
- **Nguyên tắc:** Hook KHÔNG ĐƯỢC tự ý bịa `farm_contract` nếu script chưa rõ có can thiệp thiết bị Android thật hay không.
- **Cơ chế:** Chặn ngay lập tức (Fail-Fast) nhưng BẮT BUỘC trả về đầy đủ 2 template hợp lệ 100% trong `required_action.instruction` để Agent chọn và copy-paste 1 chạm:

#### Template 1: Script nền / Watchdog thuần túy (Không chạm thiết bị Android)
```json
{
  "action": "create",
  "schedule": "every 30m",
  "script": "pythonw D:/Taadaa/tools/my_watchdog.py",
  "no_agent": true,
  "farm_contract": {
    "touches_device": false
  }
}
```

#### Template 2: Script farm có can thiệp thiết bị Android (Rolling Mode)
```json
{
  "action": "create",
  "schedule": "every 1h",
  "script": "pythonw D:/Taadaa/tools/farm_worker.py",
  "no_agent": true,
  "farm_contract": {
    "touches_device": true,
    "device_lock": "required",
    "mode": "rolling",
    "max_workers": 10,
    "release": "per_device",
    "lock_ttl_s": 300,
    "on_device_fail": "skip_continue"
  }
}
```

---

## 3. Quy Tắc Nắn Lại Anti-Scan Guidance (Gate G7)
Để triệt tiêu bão lỗi quét đĩa diện rộng (`GUARD_SEARCH_FILES_ROOT`, `GUARD_RECURSIVE_GREP`, `GUARD_FIND_SCAN`, `GUARD_DANGEROUS_ROOT`):
1. **Phân biệt ngữ cảnh thiết bị vs mã nguồn:**
   - Chỉ gắn hướng dẫn `python D:/Taadaa/tools/inspect_machine.py <N>` khi lệnh/target có chứa ID máy thật (`machine\s*\d+`, `m\d{1,3}`, `phone\s*\d+`).
2. **Hướng dẫn tra cứu mã nguồn O(1):**
   - Khi chặn tìm kiếm code diện rộng, guidance BẮT BUỘC chỉ đường dùng `search_files(target='files', pattern='...')` hoặc `git -C <repo> ls-files "<pattern>"`.
   - Tuyệt đối cấm để Agent bế tắc dẫn đến chuỗi thử sai: `grep -rn` $\to$ `find` $\to$ `os.walk`.
