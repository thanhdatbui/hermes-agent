# Closeout Gate Test Timeout in Dirty Repos & Mandatory Target Scoping

## 1. Context & Root Cause (30s Pytest Timeout Trap)
Khi thực hiện chốt phiên qua `closeout_gate.py` (hoặc `closeout_v2.py`) trên repo có nhiều file dirty tồn đọng (`git status` có nhiều file `.py` chưa commit từ các phiên khác):
- **Cơ chế gom test tự động:** Nếu gọi lệnh trần không có tham số phạm vi:
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/tools --json-output
  ```
  Script sẽ tự động quét danh sách `dirty_files` và gom TẤT CẢ các file test tương ứng trong thư mục `tests/` vào **một lệnh pytest duy nhất**.
- **Vượt ngưỡng Timeout cứng:**
  Ví dụ khi tồn đọng 5 file dirty:
  - `test_admin_ssh.py`: 2.2s
  - `test_canary_plan.py`: 0.3s
  - `test_dispatch_worker.py`: 12.0s
  - `test_guard_cronjob_safety.py`: 17.5s (chứa 104 tests)
  - `test_tiktok_dashboard.py`: 9.8s
  Tổng thời gian chạy gom: **41.8 giây** $\rightarrow$ Vượt quá ngưỡng cứng `timeout=30` trong hàm `run_cmd`:
  ```text
  ❌ [Closeout v2] TEST FAILED:
  Command '['...python.exe', '-m', 'pytest', '-q', ...]' timed out after 30 seconds
  ```
  Hệ thống lập tức đánh rớt phiên dù file code của phiên hiện tại hoàn toàn đúng cú pháp và pass test 100%.

---

## 2. Invariant: Mandatory Target Scoping Cho Closeout Gate

### Quy tắc bất biến:
Mọi lệnh gọi `closeout_gate.py` (bao gồm cả lệnh trực tiếp hoặc thông qua wrapper pipeline) **BẮT BUỘC phải truyền rõ cờ `--target-file <file>` (hoặc `--files <file>`)** để chỉ định đích danh file mục tiêu của phiên:

```bash
python D:/Taadaa/tools/closeout_gate.py --repo <repo> --target-file <target_file> --json-output
```

### Lợi ích cơ học:
1. **Phân lập tuyệt đối:** `closeout_v2.py` chỉ phát hiện và chạy duy nhất bộ test của `<target_file>` (ví dụ `test_guard_cronjob_safety.py` mất 17.5s < 30s).
2. **Kháng nhiễu dirty files:** Không bị ảnh hưởng bởi các file dirty tồn đọng hay các tiến trình chạy song song khác trong repo.
3. **Đạt chuẩn O(1):** Vượt qua Closeout Gate nhanh chóng trong thời gian < 30s, sinh bản ghi `APPROVED (score=100)` hợp lệ vào `gate_audit.jsonl`.
