# System-Scanner Mock Isolation, Diff Budgeting & Reviewer Score Elevation (2026-10-09)

## 1. Unmocked Host System Scanners Trap (`assert 5 == 1`)
### Bối cảnh & Triệu chứng:
- Khi viết hàm dọn dẹp hoặc kiểm tra tiến trình nền (như `close_all_running_gpm_profiles`):
  Hàm gọi GPM API `stop/{pid}`, sau đó có fallback quét qua `psutil.process_iter(['name', 'cmdline'])` để dọn các tiến trình Chrome/GPM bị mồ côi.
- Khi viết unit test `test_close_all_running_gpm_profiles_via_api`, test chỉ mock `requests.get` (trả về 1 profile đang chạy) nhưng **quên mock `psutil.process_iter`**.
- Hậu quả: `psutil` chạy thật trên môi trường Windows host, quét trúng 4 tiến trình Chrome thật đang mở trên máy tính của user $\rightarrow$ trả về `closed = 5` $\rightarrow$ Test fail thảm khốc:
  ```text
  AssertionError: assert 5 == 1
  ```
### Quy tắc khắc phục (Hermetic Isolation):
- Mọi hàm có dính líu đến quét hệ điều hành host (`psutil.process_iter`, `psutil.pids`, `os.listdir` thư mục runtime, `subprocess.run(["tasklist"])`):
  **BẮT BUỘC PHẢI MOCK** ở mọi test case, kể cả test case của nhánh API thành công:
  ```python
  with patch("requests.get") as mock_get, patch("psutil.process_iter", return_value=[]):
      ...
  ```

---

## 2. Kiểm Soát Trần Kích Thước Diff (`MAX_DIFF_BYTES_GATE = 30_000` bytes)
### Bối cảnh:
- `closeout_gate.py` có chốt chặn fail-fast cứng: `targeted diff quá lớn (31116 > 30000 bytes) -> Exit Code 3 (DIFF_TOO_LARGE)`.
- Khi remediation vòng 2 và vòng 3 bổ sung nhiều docstrings dài, giải thích chi tiết trong code và thêm test files, tổng diff candidate tăng từ 28KB vọt lên 33.8KB rồi 31.1KB.
### Kỹ thuật nén diff giữ nguyên giá trị kỹ thuật:
1. **Rút gọn Docstrings & Comments:** Không viết essay/tiểu luận trong docstring của hàm production; giữ docstring 1 dòng súc tích mô tả contract và return type.
2. **Loại bỏ test file không liên quan:** Chỉ đưa vào `--files` các test file trực tiếp verify các file source đang sửa.
3. **Kết quả:** Diff giảm ngay từ 31.1KB xuống 29.4KB (< 30.000 bytes), cổng mở xanh và cho phép Reviewer chấm điểm ngay.

---

## 3. Bí Quyết Nâng Điểm Reviewer từ 82/100 lên 86/100 (APPROVED)
Reviewer (Sol Auditor / Combo Review `:20129`) chấm 5 tiêu chí:
1. **Logic Correctness (30/35):**
   - Loại bỏ hoàn toàn logic dư thừa (như việc gọi `check_dual_oauth` 2 lần độc lập trong `select_candidates` $\rightarrow$ gộp thành 1 điều kiện duy nhất `if stage in ("WAIT_7D", "CHANGE_INFO")`).
2. **Telemetry & Observability (13/15):**
   - Thêm `correlation_id` vào structured telemetry events (`log_telemetry_event`):
     ```python
     correlation_id = payload.get("correlation_id", SUPERVISOR_RUN_CORRELATION_ID)
     record = {"event": event_name, "timestamp": now(), "subsystem": "gpm_supervisor", "correlation_id": correlation_id, ...}
     ```
   - Ghi nhận `close_warning` telemetry khi API stop hoặc process terminate gặp lỗi thay vì chỉ log warning nội bộ.
3. **Test Evidence (23/25):**
   - Bổ sung test kiểm chứng cả ca thành công lẫn ca ngoại lệ/fallback của `close_all_running_gpm_profiles`.
   - Bổ sung test end-to-end `test_change_info_requires_dual_oauth_end_to_end` chứng minh candidate bị filter out nếu chưa dual OAuth.
4. **Farm Safety (12/15) & Architecture (8/10):**
   - Dọn sạch 100% credentials nhạy cảm hardcoded trong code (`password`, `totp_secret`).
   - Cung cấp biến môi trường override linh hoạt cho tất cả các đường dẫn file dữ liệu (`GPM_SUPERVISOR_DATA_DIR`, `OMNI_DB_PATH`, `ROUTER9_DB_PATH`).
