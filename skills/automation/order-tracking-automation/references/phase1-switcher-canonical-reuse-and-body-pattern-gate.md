# Phase 1 In-App Switcher Canonical Reuse & Body Pattern Hard Gate

## 1. Vấn Đề Lỗi Tự Chế Bánh Xe (Inline Monolith Evasion) Trong Phase 1
- **Hiện tượng:** Trong script Phase 1 (`tiktok_app_order_sync.py`), logic mở khay chuyển đổi tài khoản (Account Switcher) và so khớp nick bị tự chế thủ công bằng OCR (`_find_handle_center`, `_header_handle`), né tránh module chuẩn `automation_core.tiktok.account_switcher`.
- **Nguyên nhân Gate bị bypass:** 
  - `capabilities.json` ban đầu chỉ quét `signature_patterns` (tên hàm `def switch_account`, `def select_account`).
  - Worker giấu logic switcher vào trong hàm `ensure_order_screen`, khiến Hard Gate (`ui_policy_check.py`) trả về `EXIT 0` và để lọt code vi phạm.

## 2. Giải Pháp Chuẩn Hóa Kiến Trúc
1. **Nâng cấp Gate `ui_policy_check.py` & `capabilities.json`**:
   - Thêm `body_patterns`: Bắt các token đặc thù của switcher (`switcher_marker`, `_find_handle_center`, `chuyen doi`, `switch account`).
   - Bất kỳ file nào xuất hiện body pattern mà thiếu `from automation_core.tiktok.account_switcher import ...` sẽ bị **REJECT NGAY LẬP TỨC**.
2. **Refactor Phase 1 Script (`tiktok_app_order_sync.py`)**:
   - Bắt buộc import canonical:
     ```python
     from automation_core.tiktok.account_switcher import matches_switcher_identity
     ```
   - Thay thế việc so khớp chuỗi thô sơ trong `_find_handle_center` bằng `matches_switcher_identity(text, handle_key)`.
   - Chạy kiểm chứng: `python D:/Taadaa/orders/tiktok_app_order_sync.py --self-test` (EXIT 0) và `python D:/Taadaa/tools/ui_policy_check.py D:/Taadaa/orders/tiktok_app_order_sync.py` (EXIT 0).
