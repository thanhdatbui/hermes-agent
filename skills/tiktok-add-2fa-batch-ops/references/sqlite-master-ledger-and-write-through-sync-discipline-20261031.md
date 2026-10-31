# Quy Chuẩn Chuyển Đổi Sang SQLite farm_master.db & Đồng Bộ Write-Through (31/10/2026)

Tài liệu đúc kết từ phiên giải quyết triệt để tàn dư đọc file Excel thủ công và sửa lỗi Gate B Planner / Canary S4.

---

## 1. Nguyên Tắc Cốt Lõi: Cấm Đọc Excel Trực Tiếp Khi Đã Có SQLite
- **Hiện trạng:** Hệ thống Farm đã chuyển đổi 100% dữ liệu sang SQLite `D:/Taadaa/data/farm_master.db` (160 máy, 1.270 nick TikTok, 1.455 mailboxes).
- **Cấm tuyệt đối:** Viết code mới hoặc duy trì code cũ dùng `openpyxl.load_workbook()` để tra cứu thông tin máy, tài khoản, mật khẩu hoặc mã token Graph API.
- **Quy chuẩn truy xuất:** Mọi truy vấn bắt buộc đi qua DAL `D:/Taadaa/tools/farm_db.py`:
  * Tra cứu tài khoản theo máy: `get_accounts_by_machine(machine_id)`
  * Tra cứu tài khoản theo username: `get_account(username)`
  * Tra cứu thông tin máy / serial / proxy: `get_machine_info(machine_id)`
  * Tra cứu mật khẩu / token hòm thư: `get_mailbox_credentials(email)`

---

## 2. Kiến Trúc Đồng Bộ Ghi Kép (Write-Through Architecture)
- **Vấn đề:** Khi runner cập nhật 2FA Secret hoặc Mật khẩu TikTok mới, nếu chỉ ghi vào Excel `taikhoan_dat_v2_updated .xlsx` sẽ khiến Sổ Cái SQLite trên Web `:1905` bị lệch dữ liệu.
- **Giải pháp:** Trong `python_runner/core/workbook.py` (hàm `_write_cell`), sau khi hoàn thành atomic update vào file Excel, bắt buộc gọi hàm write-through cập nhật song song vào SQLite:
  ```python
  from farm_db import update_tiktok_credentials
  if column_name == "2fa":
      update_tiktok_credentials(target.username, twofa_secret=value)
  elif column_name == "pass":
      update_tiktok_credentials(target.username, password=value)
  ```
- **Xác thực Preflight không nghẽn I/O:**
  * Hàm `inspect_target()`, `password_is_blank()`, `read_pass_value()`, `read_email_value()` ưu tiên tra cứu trực tiếp từ SQLite `farm_master.db` (tốc độ 0.005s), chỉ dùng openpyxl làm fallback tầng cuối.

---

## 3. Bài Học Điều Phối: Chống Nhận Lỗi Suông & Kỷ Luật Gate B / S4 Canary
1. **Chống văn phong nhận lỗi suông (User Correction):**
   * Khi User chất vấn "Sao lại bỏ qua...", tuyệt đối **KHÔNG xin lỗi suông, không tự phê bình hình thức**.
   * Hành động chuẩn: Phân tích đúng nguyên nhân kỹ thuật, nêu rõ phương án khắc phục và **THỰC THI SỬA CODE / CƠ GIỚI HÓA NGAY LẬP TỨC**.
2. **Kỷ luật Gate B Planner (`gate_b_planner.py`):**
   * Cắt cụt context 800 dòng đầu file khiến các file monolith dài > 800 dòng bị rớt context (hàm lỗi nằm ở dòng 807 không thấy được, dẫn tới Gemini Web ảo giác anchor và bị reject sang Sol).
   * Chuẩn hóa: File $\le 1.500$ dòng nạp toàn bộ code thật; file lớn hơn tự động trích xuất các cửa sổ $\pm 60$ dòng quanh keyword mục tiêu.
3. **Kỷ luật Canary S4 (`unified_patch_pipeline.py` & `canary_runner.py`):**
   * Lệnh gọi Canary trong pipeline phải map đúng tham số CLI của runner: `--canary-device auto` $\rightarrow$ `--auto-device`; `--canary-device <N>` $\rightarrow$ `--machine <N>`.
   * Cấm tự ý chêm `--no-canary` chỉ vì né lỗi cờ lệnh CLI.
