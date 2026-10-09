# Preflight Reg Bù Slot Mismatch & Cooldown Diagnostics

Tài liệu hướng dẫn chẩn đoán và xử lý các ca lỗi khi chạy `ensure_row_accounts.py` (Preflight Reg Bù Row N).

## 1. Triệu chứng & Mã lỗi

```
📋 [PREFLIGHT REG BÙ ROW N]
• Tổng máy thiếu: X (Đã chạy: Y, Cooldown: Z)
❌ Thất bại: Máy M: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)
⏸️ Bỏ qua / Cooldown: M_A, M_B...
```

## 2. Phân tích nguyên nhân gốc rễ

### A. Lỗi "Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)" (Ví dụ: Máy 53)
* **Hiện tượng:**
  * File điều phối `taikhoan_run_safe.xlsx` và file theo dõi `taikhoan_dat_v2_updated .xlsx` có ô trống (Row N / Slot N = `None`).
  * Script `social_reg_v1.py` mở app TikTok -> mở profile -> bung Switcher Dropdown (`53_03_dropdown_000432.png`) nhưng không thấy nút "Thêm tài khoản" do số lượng tài khoản trong danh sách đã đạt 8/8.
  * Guard `MACHINE_FULL_8_ACCOUNTS` kích hoạt, báo lỗi và thoát an toàn về Home.
* **Nguyên nhân cốt lõi:**
  * Có tài khoản thuộc máy khác bị đăng nhập / chuyển sang máy này (Cross-machine drift). Ví dụ: Nick `chichi13853` thuộc Máy 26 (Folder 206) nhưng thực tế đang nằm trên Máy 53.
  * Hoặc tài khoản đã được reg/login thủ công trước đó nhưng chưa được cập nhật backfill vào file Excel.
* **Quy trình xử lý an toàn (Bảo vệ tài sản Farm):**
  1. OCR/Đọc danh sách UID thực tế trên switcher dropdown từ screenshot bằng `windows-native-ocr`.
  2. Đối chiếu toàn bộ 8 UID thực tế với `taikhoan_dat_v2_updated .xlsx` xem UID lạ đến từ máy nào.
  3. Báo cáo Telegram với ảnh bằng chứng (`MEDIA:`), xin ý kiến User:
     - Hoặc backfill UID đó vào Slot trống của máy hiện tại (và điều chỉnh lại máy nguồn).
     - Hoặc thực hiện quy trình `exact_logout.py` an toàn để đăng xuất đúng tài khoản lạ trước khi reg tài khoản mới. Tuyệt đối CẤM tự ý xóa hay reg đè.

### B. Hiện tượng "Bỏ qua / Cooldown" do Duplicate Slot (Ví dụ: Máy 22, 36, 64)
* **Hiện tượng:**
  * Trong `taikhoan_run_safe.xlsx`: Row N của máy đang trống (`None`), khiến `ensure_row_accounts.py` nhận diện máy là `missing`.
  * Tuy nhiên, `_detect_clean.py` lại không cấp máy đó vào danh sách targets, khiến máy rơi vào danh sách `cooldown_stts`.
* **Nguyên nhân cốt lõi:**
  * File `taikhoan_dat_v2_updated .xlsx` bị ghi đúp bản ghi giữa các slot của cùng một máy (Duplicate slot entry).
  * Ví dụ:
    * Máy 22: UID `gialan555` bị trùng ở cả Folder 173 (Slot 5) và Folder 175 (Slot 7).
    * Máy 36: UID `loankem5` bị trùng ở cả Folder 285 (Slot 5) và Folder 287 (Slot 7).
    * Máy 64: UID `genuntfn1ch` bị trùng ở cả Folder 509 (Slot 5) và Folder 511 (Slot 7).
  * Hàm `load_registered_mailboxes(return_machine_counts=True)` đếm theo số dòng non-empty của máy trong workbook. Vì dòng bị duplicate vẫn tính là 1 tài khoản nên máy đã đủ 8 dòng -> `select_pending_targets` loại trừ máy vì đã đạt `max_accounts_per_machine=8`.
* **Quy trình xử lý:**
  1. Quét đối soát nội bộ các folder thuộc máy trong `taikhoan_dat_v2_updated .xlsx`.
  2. Xác định các cặp folder bị trùng UID/Email.
  3. Làm sạch dòng duplicate (trả về `None` nếu slot đó thực sự chưa có nick mới hoặc đồng bộ đúng nick đang chạy trên máy).
