# Pitfall & Pattern: TikTok Account Switcher Display Name vs Handle Matching & 0ms Click Swallowing (2026-09-17)

## Bối cảnh
Khi chạy batch feed swipe / nuôi acc diện rộng trên Farm Samsung S7, một loạt máy (ví dụ Máy 14, 71, 72...) bị văng cảnh báo:
`manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
Dẫn đến việc hệ thống hiểu nhầm là tài khoản bị văng khỏi máy, kích hoạt cơ chế `_maybe_recover_missing_account_via_login` (`reconcile_tiktok_accounts.py`), làm kẹt 2FA và kẹt trần 8 tài khoản.

## 2 Nguyên nhân Gốc rễ & Giải pháp

### 1. Matcher đánh trượt Display Name tiếng Việt
- Trên giao diện Bottom Sheet Account Switcher (`RecyclerView`), TikTok ưu tiên hiển thị **Display Name (Tên người dùng)** thay vì Username/Handle `@username`.
  - Ví dụ Máy 14: Switcher hiển thị `"Anh Hoang"` trong khi Username là `@hong.bo.anh83`.
  - Ví dụ Máy 71: Switcher hiển thị `"Anh Pham"` trong khi Username là `@ngc.anh.phm33`.
- Trước đây hàm `matches_switcher_identity` chỉ so khớp prefix / badge số trực tiếp giữa hai chuỗi string (`node_value` vs `target_value`), không có token overlap và không liên kết với Master DAT.
- **Giải pháp:**
  1. **Token Overlap:** Bóc tách các token chữ cái sau khi normalize NFKD (`_clean_alpha_tokens`). Nếu các token chữ của Display Name trùng khớp với token của handle hoặc email prefix đăng ký (như `"hoangthibaoanh..."` chứa `anh` và `hoang`), xác nhận match thành công.
  2. **DAT Fallback Cache:** Đọc mapping alias từ Master DAT `taikhoan_dat_v2_updated .xlsx` (cột `ID` ↔ `GMAIL` prefix) để tra cứu tên người dùng đăng ký khi TikTok chỉ hiện Display Name.

### 2. Bẫy nuốt click (0ms ADB Input Tap) trên RecyclerView Bottom Sheet
- Lệnh `adb shell input tap x y` gửi `ACTION_DOWN` rồi `ACTION_UP` với duration 0ms.
- Trên RecyclerView của TikTok v46+, các item container trong bottom sheet lọc bỏ sự kiện chạm 0ms để chống chạm nhầm khi đang cuộn danh sách (scroll jitter).
- Khi runner tap vào dòng tài khoản (như Máy 72 tap vào `m.ngc4624`), click bị nuốt hoàn toàn, tài khoản không được chọn và màn hình Switcher không đổi.
- **Giải pháp:**
  Thay thế `input tap x y` bằng synthetic click có giữ chạm 100ms:
  ```bash
  adb shell input swipe {x} {y} {x} {y} 100
  ```
  Giúp hệ thống Android nhận diện chắc chắn là một cú tap hợp lệ trên mọi custom view / RecyclerView.
