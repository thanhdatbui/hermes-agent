# Triage Màn Hình Guest Profile, Cơ Chế Auto-Login Khi Tiền Kiểm Feed Gặp Màn Login, & Kỷ Luật Bằng Chứng Đăng Nhập (10/10/2026)

## 1. Bẫy Màn Hình "Hồ Sơ Khách" (Guest Profile) vs Lỗi `[03_dropdown] Khong mo duoc account dropdown`
- **Hiện tượng**: Chạy `tiktok_login_v1.py` trên máy chưa có session nào active (hoặc vừa bị đăng xuất sạch tài khoản), script mở app, vào tab Hồ sơ nhưng kẹt timeout liên tục và văng lỗi:
  ```text
  STOPPED: [03_dropdown] Khong mo duoc account dropdown
  ```
- **Căn nguyên cốt lõi**:
  - Khi chưa có session active, TikTok render màn hình Guest Profile:
    * Tiêu đề: `Hồ sơ`
    * Dòng mô tả: `Đăng nhập vào tài khoản hiện có` (`com.ss.android.ugc.trill:id/k1r`)
    * Nút hành động trung tâm: Nút to màu đỏ **`Đăng nhập`** (`com.ss.android.ugc.trill:id/d01`, bounds `[165,1016][915,1172]`).
  - Trên màn hình này, **hoàn toàn KHÔNG có tên người dùng, không có nút mũi tên dropdown (`rv5`)**, vì chưa có tài khoản nào được đăng nhập.
  - Script login cũ giả định máy luôn có ít nhất 1 nick active để mở Switcher dropdown từ header. Khi gặp Guest Profile, script thử tìm dropdown qua header và qua Menu hồ sơ -> không thấy -> timeout fail.
- **Giải pháp chuẩn hóa O(1) trong `tiktok_login_v1.py`**:
  - Trong `ensure_login_entry_screen`, sau khi tap tab Hồ sơ:
    * Kiểm tra: Nếu `flat` chứa `"dang nhap vao tai khoan hien co"` hoặc có button `:id/d01`:
      Bấm nút **`Đăng nhập`** (`find_text_tap("Đăng nhập")` hoặc click tọa độ tâm `d01`).
    * Sau khi bấm `Đăng nhập`, TikTok sẽ bung màn hình One-tap **"Chào mừng bạn trở lại"** (lưu các tài khoản phụ cũ) kèm nút *"+ Thêm tài khoản khác"*.
    * Kiểm tra One-tap list:
      - Nếu nick đích **đã có trong danh sách One-tap**: Chạm trực tiếp vào tên nick để active ngay phiên mà không cần pass/OTP (trả về `"already_logged_in"`).
      - Nếu nick đích **chưa có trong danh sách**: Bấm nút **"Thêm tài khoản khác"** để vào form đăng nhập chính thống (trả về `"one_tap"`).

---

## 2. Nâng Cấp Feed Runner Tự Động Kích Hoạt Auto-Login Khi Tiền Kiểm Gặp Màn Login (`feed_swipe_smoke.py`)
- **Vấn đề**:
  - Feed runner (`feed-session-smoke`) có sẵn hàm nạp nick tự động `_maybe_recover_missing_account_via_login(ctx, expected, ...)`.
  - Tuy nhiên, trước đây hàm này chỉ được móc ở nhánh `if _is_account_switcher_missing_expected_reason(last_reason):` (sau khi đã mở được Account Switcher từ Profile mà không thấy nick).
  - Khi máy rơi vào màn hình "Chào mừng bạn trở lại" (hoặc Guest Profile) ngay lúc mở Profile, bước tiền kiểm `profile_preflight_identity_guard` gắn nhãn `manual-needed:login` ("login/account screen detected").
  - Hàm `verify_and_switch_profile` thấy `identity_manual_row` là lập tức dừng khẩn cấp với lý do `profile identity blocked by manual-needed screen`, thoát ra ngoài và bắn cảnh báo đỏ P0 về Telegram thay vì tự động nạp nick!
- **Giải pháp chuẩn hóa trong `verify_and_switch_profile`**:
  ```python
  if isinstance(identity_manual_row, dict):
      if allow_auto_reconcile and any("login" in str(identity_manual_row.get(k) or "").lower() for k in ("detected", "safety_reason", "reason")):
          if _maybe_recover_missing_account_via_login(ctx, expected, results=results, max_swipes=max_swipes, result_kwargs=result_kwargs):
              ctx.logger.log(
                  device_id=ctx.device_id, account=ctx.account,
                  step=f"{SESSION_ARTIFACT_PREFIX}/profile_preflight",
                  action="auto_login_recovered_from_login_screen", result="retry",
                  extra={"reason": f"auto-login succeeded after login screen for {expected}", "expected_account": expected},
              )
              return verify_and_switch_profile(ctx, expected_account, results=results, max_swipes=max_swipes, result_kwargs=result_kwargs, allow_auto_reconcile=False)
      row = _profile_manual_preflight_row(...)
      return row
  ```
  - Khi gặp nhãn `login` ở bước tiền kiểm, hệ thống tự động gọi `_maybe_recover_missing_account_via_login` nạp nick tại chỗ; sau khi nạp xong tự động tái thẩm định Profile với `allow_auto_reconcile=False` (chống lặp vô hạn).

---

## 3. Cảnh Báo Regex Thông Báo Samsung Trong `dismiss_profile_overlays` (`social_reg_v1.py`)
- **Cạm bẫy**:
  - Trên điện thoại Samsung Galaxy S7, thanh trạng thái (status bar) thường có thông báo hệ thống:
    `"Tìm di động của bạn: Nếu bạn mất điện thoại thì sao?"`
  - Hàm `dismiss_profile_overlays` có bộ lọc kiểm tra modal yêu cầu thêm số điện thoại:
    `if any(k in flat for k in ["add phone", "them so dien thoai", "so dien thoai cua ban"]):`
  - Chuỗi `"so dien thoai cua ban"` (bỏ dấu = `"dien thoai cua ban"`) vô tình khớp với cụm `"mất điện thoại thì sao / Tìm di động của bạn"` trên status bar!
  - Hậu quả: Script hiểu nhầm màn hình hiện tại là popup đòi thêm số điện thoại, tự động bấm nút `Đóng` (`rid='com.ss.android.ugc.trill:id/z7l'`). Nút này trên màn hình "Chào mừng bạn trở lại" chính là nút thoát màn hình One-tap, làm app văng về Home feed và mất dấu vết login!
- **Khắc phục**:
  - Tại đầu hàm `dismiss_profile_overlays`, đặt guard bảo vệ:
    ```python
    if any(k in flat for k in ["chao mung ban tro lai", "welcome back", "them tai khoan khac"]):
        return
    ```
    Tuyệt đối không thực hiện bất kỳ thao tác đóng modal nào nếu đang ở màn hình One-tap Login.

---

## 4. Kỷ Luật Bằng Chứng Đăng Nhập Thành Công: CẤM DÙNG MÀN HÌNH HOME FEED
- **Quy tắc bất biến**:
  - Màn hình Home Feed (video lướt trang chủ) **KHÔNG PHẢI LÀ BẰNG CHỨNG ĐĂNG NHẬP THÀNH CÔNG**. Video feed chỉ chứng minh app đang mở, không chứng minh được nick nào đang active hay session có hợp lệ hay không.
  - **Bắt buộc**: Bằng chứng hoàn tất đăng nhập/nạp nick phải là:
    1. **Màn hình Hồ sơ (Profile)**: Hiển thị rõ username đích `@<username>`, tên hiển thị, các chỉ số Following/Follower.
    2. **Màn hình Account Switcher (Chuyển đổi tài khoản)**: Hiển thị danh sách nick trong máy kèm dấu tích xanh chọn trúng tài khoản đích.
  - Coordinator BẮT BUỘC dùng Vision/WinRT OCR soi mắt kiểm tra đúng username đích trên 1 trong 2 màn hình này trước khi đính kèm `MEDIA:` và tuyên bố thành công.
