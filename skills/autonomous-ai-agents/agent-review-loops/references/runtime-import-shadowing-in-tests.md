# Runtime Import Shadowing in Test Suites & Dynamic Spec Resolution

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Root Cause)
- **Môi trường:** Hệ thống Taadaa Farm trên Windows có kiến trúc phân tầng:
  1. Kho mã nguồn trong Git repo: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`.
  2. Môi trường thực thi runtime: `%LOCALAPPDATA%\hermes\scripts\` và thư mục package `site-packages`.
- **Lỗi Shadowing:** 
  Khi viết unit test (ví dụ trong `tests/test_cron_chatgpt_web_pool_watchdog.py`) cho một script vừa được nâng cấp (ví dụ `sync_gpm_lifecycle.py`), câu lệnh `import sync_gpm_lifecycle` theo thứ tự tìm kiếm `sys.path` có thể vô tình nạp phiên bản cũ đang nằm ở `%LOCALAPPDATA%` hoặc cache Python.
- **Biểu hiện lỗi:**
  ```text
  AttributeError: module 'sync_gpm_lifecycle' has no attribute 'merge_taikhoan_dat_candidates'
  ```
  Mặc dù kiểm tra file mã nguồn trong repo thì hàm `merge_taikhoan_dat_candidates` đã có sẵn và hoàn toàn đúng cú pháp.

---

## 2. Quy Chuẩn Khắc Phục Bắt Buộc (Deterministic Module Loading)
Khi viết test kiểm thử các script nằm trong `deploy/hermes-home/scripts/` hoặc các consumer script:
1. **CẤM dùng bare `import <script_name>`** nếu script có khả năng bị trùng tên hoặc có bản sao ở runtime.
2. **BẮT BUỘC dùng `importlib.util.spec_from_file_location`** để nạp trực tiếp từ file repo đích:
   ```python
   import importlib.util
   from pathlib import Path

   REPO_SCRIPTS = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
   target_path = REPO_SCRIPTS / "sync_gpm_lifecycle.py"

   spec = importlib.util.spec_from_file_location("sync_gpm_lifecycle_target", str(target_path))
   sgl = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(sgl)
   ```
3. **Lợi ích kiến trúc:**
   - Đảm bảo 100% test suite đang kiểm chứng đúng các byte mới nhất trong Git working tree.
   - Loại trừ hoàn toàn tác động phụ từ phiên bản cũ trong `%LOCALAPPDATA%`, OneDrive hay cache `sys.modules`.

---

## 3. Kết Hợp Chống Bẫy Test Giả Lập (Anti-Synthetic Test Pattern)
Sau khi import đúng module qua dynamic spec, kiểm thử phải gọi trực tiếp hàm production thay vì tự reimplement logic trong test:
```python
def test_taikhoan_dat_reading_and_exclusions(self):
    with tempfile.TemporaryDirectory() as td:
        wb_path = Path(td) / "test_tk.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tài Khoản"
        ws.append(["Mã Máy", "c1", "c2", "c3", "c4", "Email", "c6", "c7", "c8", "Serial", "Proxy"])
        ws.append([45, "", "", "", "", "valid45@gmail.com", "", "", "", "ce071607", "1.1.1.1:5107:u:p"])
        wb.save(str(wb_path))

        candidates = {}
        # GỌI TRỰC TIẾP HÀM PRODUCTION:
        added = sgl.merge_taikhoan_dat_candidates(str(wb_path), candidates, {"excluded@gmail.com"})
        serials, proxy_map = {}, {}
        sgl.merge_taikhoan_dat_proxies(str(wb_path), serials, proxy_map)

        self.assertEqual(added, 1)
        self.assertEqual(candidates["valid45@gmail.com"], 45)
        self.assertEqual(serials[45], "ce071607")
        self.assertEqual(proxy_map[45], "1.1.1.1:5107:u:p")
```
Cách viết này chứng minh được:
- Hàm production thật chạy tốt với fixture độc lập.
- Không bị phụ thuộc vào môi trường bên ngoài (No live ADB / No live network).
- Sol Reviewer công nhận 100% bằng chứng kiểm thử đạt chuẩn `Test Evidence` cao.
