# Phân Biệt Workbook Nuôi Feed (`taikhoan_run_safe.xlsx`) ↔ Workbook Đăng Video (`TikN.xlsx`) & Mở Rộng Upload Hook Row 3 (2026-08-25)

## 1. Kiến Trúc Workbook Phân Tách: Nuôi Feed ↔ Đăng Video

Trong hệ thống vận hành Taadaa TikTok Farm:

### A. Workbook Nuôi Feed (`taikhoan_run_safe.xlsx`):
- **Đường dẫn chuẩn:** `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (Sheet `Accounts`).
- **Mục đích:** Là nguồn danh sách tài khoản duy nhất được sử dụng cho toàn bộ các ca nuôi lướt feed hàng ngày (`multi_machine_feed_session.py`).
- **Cấu trúc:** Mỗi máy có nhiều dòng tương ứng với các Row (Row 1 = Ca 1, Row 2 = Ca 2, Row 3 = Ca 3 / chiều...).
- **Thực tế:** Cần phân biệt rõ: Khi kiểm tra "máy có nick hay trống nick để nuôi", BẮT BUỘC đọc từ `taikhoan_run_safe.xlsx`, TUYỆT ĐỐI KHÔNG đọc nhầm từ các file `TikN.xlsx`.
  - Ví dụ: Ở Row 3, `taikhoan_run_safe.xlsx` có tới **69/80 máy có nick**, chỉ có 11 máy thực sự trống nick.

### B. Workbook Đăng Video (`Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`):
- **Đường dẫn:** `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` (Ca 1), `Tik2.xlsx` (Ca 2), `tik3.xlsx` (Ca 3).
- **Mục đích:** Chỉ phục vụ cấu hình hook đăng video (Folder Video, video gốc, hashtag, tiến độ `Video Đã Đăng`).
- **Lưu ý tên file trên đĩa:** File Ca 3 tên thực tế là `tik3.xlsx` (chữ thường `t`).

---

## 2. Quy Tắc Kích Hoạt Hook Upload Ở Cuối Phiên 3

- **Quy định vận hành:** Mỗi ca gồm 3 phiên lướt feed. Ở **cuối Phiên 3**, hệ thống sẽ tự động kích hoạt tiến trình upload video lên TikTok theo hàng tài khoản tương ứng.
- **Cập nhật phạm vi Row (Commit `30c70cb` - 2026-08-25):**
  - Trước đây: Code chặn `if upload_row not in (1, 2): return skipped` (khiến Ca 3 chạy Row 3 bị bỏ qua không đăng video).
  - Hiện tại: Đã mở rộng cho phép cả 3 ca:
    ```python
    upload_row = int(getattr(account, "account_row_index", 1) or 1)
    if upload_row not in (1, 2, 3):
        payload = {
            "machine": getattr(account, "machine", 0),
            "row": upload_row,
            "status": "skipped",
            "reason": "upload-disabled-outside-row-1-2-3",
        }
        _write_upload_result(child_ctx, payload)
        return payload
    ```
- **Mapping tương ứng:**
  - `account_row_index == 1` ➔ Đăng video theo `Tik1.xlsx`
  - `account_row_index == 2` ➔ Đăng video theo `Tik2.xlsx`
  - `account_row_index == 3` ➔ Đăng video theo `tik3.xlsx`

---

## 3. Pitfall Cấm Kỵ: Báo Cáo Nhầm Trạng Thái Giữa Nuôi Feed và Đăng Video

1. **Không lấy danh sách `tik3.xlsx` để kết luận máy không nuôi feed:**
   - Nếu `tik3.xlsx` trống ô ID, điều đó chỉ có nghĩa là máy đó chưa cấu hình thông tin đăng video của Ca 3, KHÔNG có nghĩa là máy đó không được nuôi feed. Máy vẫn sẽ chạy nuôi bình thường nếu có nick trong `taikhoan_run_safe.xlsx`.
2. **Không tự kết luận upload thành công:**
   - Tuân thủ nghiêm ngặt Hard Gate: Phải có `report.json` với `post_verified == True` và kiểm chứng lưới video Profile thật trên thiết bị.
