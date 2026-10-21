# Bẫy Nhận Diện Nhầm Màn Cài Đặt Là Form Đăng Nhập & Bẫy TRACKING_ROW_CHANGED Khi Trùng Credentials (2026-10-21)

## 1. Bẫy False-Positive Trong `_tiktok_login_modal_present()` Khi Mở Cài Đặt
### Hiện tượng
- Khi `open_account_dropdown` qua header không thành công hoặc bị popup che, script kích hoạt fallback `_open_account_dropdown_via_settings()`:
  - Mở Menu hồ sơ -> Cài đặt và quyền riêng tư (`Settings and privacy`).
- Màn hình Cài đặt của TikTok có phần header nhóm chức năng mang text:
  `c=android.widget.TextView | t='Đăng nhập' | b=[48,1260][356,1407]`
  (ngay trên mục "Chuyển đổi tài khoản" và "Đăng xuất").
- Hàm `_tiktok_login_modal_present(xml)` kiểm tra chuỗi generic `"dang nhap"` trong `_tiktok_flat_xml(xml)`.
- Khi máy đang ở màn Cài đặt, `_tiktok_login_modal_present(xml)` trả về `True`!
- Hậu quả dây chuyền:
  - `tap_add_account()` thấy cờ `True` liền log:
    `✓ already at login modal, skipping tap_add_account`
    và bỏ qua hoàn toàn việc tìm/bấm nút "Chuyển đổi tài khoản" hoặc "Thêm tài khoản"!
  - Bước 06 `choose_email_login` tiếp tục chạy trên màn hình Cài đặt, tìm kiếm các nút email không thấy, sau 3 lần retry dẫn đến dừng phiên với lỗi:
    `STOPPED: [06_email_option] Không tìm thấy: Email / icon email`.

### Khắc phục chuẩn
Trong `_tiktok_login_modal_present(xml)` (`social_reg_v1.py`):
BẮT BUỘC loại trừ màn hình Cài đặt trước khi kiểm tra các keyword đăng nhập:
```python
def _tiktok_login_modal_present(xml):
    """Detect login/signup text from TikTok, excluding system notifications and Settings."""
    flat = _tiktok_flat_xml(xml)
    if "cai dat va quyen rieng tu" in flat or "settings and privacy" in flat:
        return False
    return any(...)
```

---

## 2. Bẫy `TRACKING_ROW_CHANGED` Khi Slot Đã Chứa Đúng Credentials Mục Tiêu
### Hiện tượng
- Khi đăng nhập thành công vào profile `@trinhgiang7694`, `social_reg_v1.py` gọi `ensure_profile_completed_and_track` -> `upsert_tracking_account()`.
- Để chống ghi đè nhầm tài khoản khác, hàm re-read dòng trong Excel (`taikhoan_dat_v2_updated .xlsx`) và kiểm tra an toàn:
  ```python
  if row_id not in (None, "") or row_pass not in (None, ""):
      raise RuntimeError("TRACKING_ROW_CHANGED")
  ```
- Tuy nhiên, nếu tài khoản đã được Coordinator backfill đúng ID và PASS vào dòng đó trước khi chạy login (hoặc run trước đó đã ghi dở dang), `row_id` và `row_pass` không còn là `None`.
- Điều này kích hoạt exception `TRACKING_ROW_CHANGED`, khiến dù đăng nhập thành công 100% trên thiết bị, script vẫn thoát với `exit code 1` và log `STOPPED: TRACKING_ROW_CHANGED`.

### Khắc phục chuẩn
Trong `upsert_tracking_account()` (`social_reg_v1.py`):
Cho phép ghi nhận khi giá trị `row_id` và `row_pass` hiện tại trùng khớp với chính tài khoản mục tiêu đang nạp:
```python
if row_stt != stt or str(row_gmail or "").strip().lower() != email_l:
    raise RuntimeError("TRACKING_ROW_CHANGED")
if (row_id not in (None, "") and str(row_id).strip().lower() != str(tiktok_id or "").strip().lower()) or \
   (row_pass not in (None, "") and tiktok_pw and str(row_pass).strip() != str(tiktok_pw).strip()):
    raise RuntimeError("TRACKING_ROW_CHANGED")
```
Giúp luồng ghi nhận an toàn, idempotent và không bị crash giả khi credentials đã khớp.
