# Pitfall: False Cooldown / Silent Zero-Purchase Bug in Preflight Reg Bù

## 1. Triệu chứng
Thông báo Telegram hiển thị:
```text
📋 [PREFLIGHT REG BÙ ROW N]
• Tổng máy thiếu: 1 (Đã chạy: 0, Cooldown: 1)
⏸️ Bỏ qua / Cooldown (1): 80
```
User phản ánh: *"Ủa t thiết kế thiếu mail tự gọi lệnh mua mail rồi mà, sao lại báo cáo láo bảo đang cooldown?"*

## 2. Nguyên nhân gốc rễ (Root Cause)

### A. Bug nuốt lỗi (Silent Zero Purchase) trong `buy_hotmail.py`
- Khi cả hai nhà cung cấp mail đều không mua được (BoxTaiKhoan lỗi Product ID, CloneFBIG hết sạch stock = 0):
  - Hàm `buy_multiple_accounts` dừng sớm và trả về danh sách rỗng `[]`.
  - Hàm `main()` gọi `append_to_kibe_workbook([], ...)` và in `Successfully appended 0 account(s)`.
  - Script kết thúc với `exit code 0` (thành công giả mạo) thay vì `exit code 1` (lỗi).

### B. Báo cáo nhầm Cooldown trong `ensure_row_accounts.py`
- `ensure_mail_for_machines` thấy returncode == 0 nên tiếp tục gọi `run_tiktok_reg_for_machines([M])`.
- Vào `_run_all_targets.py`, vì máy M thực tế không có mail mới nào trong `gmail_clean_v2.xlsx`, máy không được đưa vào targets $\rightarrow$ `ran_stts` rỗng.
- Logic gom nhóm kết quả Telegram trong `ensure_row_accounts.py`:
  ```python
  cooldown_stts = sorted([m for m in missing if m not in ran_stts])
  ```
  Tất cả các máy thiếu mà không chạy được đều bị gộp thẳng vào `cooldown_stts`, dẫn tới việc **máy không chạy do thiếu mail bị vu oan là đang Cooldown**.

## 3. Quy chuẩn kiểm tra & Khắc phục khi gặp lỗi này

1. **Kiểm tra kho & số dư ngay tại chỗ:**
   ```bash
   python D:/Taadaa/tools/buy_hotmail.py --stock
   python D:/Taadaa/tools/buy_hotmail.py --balance
   ```
2. **Kỷ luật trả lời User:**
   - Tuyệt đối KHÔNG được vội vàng giải thích lý thuyết hay bịa chuyện *"hệ thống tự động tạm hoãn/cooldown"*.
   - Phải kiểm tra log hiện trường, stock nhà cung cấp và đối soát logic phân loại trạng thái.
   - Định dạng nhận lỗi khi bị user bắt lỗi: `[FAULT-CONFIRMED] + Evidence + Root Cause + Structural Fix + Verification`.
3. **Quy tắc Structural Fix:**
   - Trong `buy_hotmail.py`: Nếu số lượng tài khoản mua được `< count`, BẮT BUỘC thoát bằng `sys.exit(1)` với thông báo rõ ràng (`OUT_OF_STOCK` hoặc `PURCHASE_INCOMPLETE`).
   - Trong `ensure_row_accounts.py`: Tách bạch rõ 3 trạng thái độc lập khi báo cáo Telegram:
     - `Thành công`: Máy đã chạy và reg thành công (`status == SUCCESS`).
     - `Thất bại`: Máy đã chạy nhưng lỗi OTP/UI/device (`status == FAILED`).
     - `Thiếu mail / Mua mail fail`: Không cấp được mail trước ca.
     - `Cooldown`: CHỈ áp dụng cho các máy thực sự bị dính cooldown trong ngày (`get_machines_registered_today()` hoặc lock rejection cooldown).
