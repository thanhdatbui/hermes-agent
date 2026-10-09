# Bẫy One-Tap Fast Login ("Chào mừng bạn trở lại") & Blind Tap Nút Camera Đáy Gây Timeout 180s (2026-09-24)

## 1. Hiện tượng & Triệu chứng
- Trong ca nuôi feed (`verify_and_switch_profile`), hệ thống phát hiện Switcher thiếu tài khoản mục tiêu (`account-switcher-missing-expected`), hook tự động kích hoạt `tiktok_login_v1.py <STT> --email <nick> --ss --allow-parent-lock`.
- Lệnh login chạy độc lập nhưng bị `subprocess.TimeoutExpired` sau đúng 180 giây (hoặc fallback `reconcile_tiktok_accounts.py` timeout 300s).
- Kiểm tra log `social_reg_log.txt` thấy vòng lặp liên tục:
  ```
  [go_to_profile] tap profile tab node (972, 1857)
  [profile] dismiss bottom sheet modal (fxs) via Huy tap + BACK
  [profile] dismiss Camera / Create video screen (đóng màn hình tạo video)
  ✗ Không thấy: ('Đóng', 'Dong', 'Close')
  → tap retry profile tab node (972, 1857)
  [profile] dismiss bottom sheet modal (fxs) via Huy tap + BACK
  ... (loop lặp lại cho đến khi hết 180s)
  ```

## 2. Phân tích Nguyên nhân Gốc rễ (Root Causes)

### A. Màn hình One-Tap Fast Login ("Chào mừng bạn trở lại")
- Khi TikTok lưu cache phiên đăng nhập của một tài khoản cũ (hoặc tài khoản đã đăng xuất/gần đây), khi mở app TikTok hiển thị màn hình One-Tap Login:
  - Header: `"Chào mừng bạn trở lại"` (`id/z3h`)
  - Username hiển thị: `@username` (`id/z3l`)
  - Nút chính: `"Đăng nhập"` (`id/z3i`)
  - Nút phụ: `"Thêm tài khoản khác"` (`com.ss.android.ugc.trill:id/z3k`, bounds `[180,1435][900,1579]`)
  - Nút đóng góc trên: `"Đóng"` (`com.ss.android.ugc.trill:id/zom`, bounds `[936,78][1068,210]`)
  - Chân trang: `"Bạn không có tài khoản? Đăng ký"` (`bounds=[0,1740][1080,1920]`)
- Hàm `ensure_login_entry_screen` trong `tiktok_login_v1.py` chỉ kiểm tra `is_auth_landing_screen(xml)`. Khi màn hình One-tap này xuất hiện, `is_auth_landing_screen` trả về `False` vì không chứa cụm từ `"tiếp tục với email"`.
- Do đó, `ensure_login_entry_screen` nhảy sang nhánh gọi `go_to_profile(device_id)`. Tuy nhiên, màn hình One-Tap này hoàn toàn KHÔNG có thanh tab Profile (đáy màn là dòng chữ đăng ký). Việc cố bấm tab Profile ở `(972, 1857)` bị thất bại.

### B. Blind Tap `(540, 1842)` trong `dismiss_profile_overlays` (`social_reg_v1.py`)
- Trong `social_reg_v1.py` (khoảng dòng 2777), hàm `dismiss_profile_overlays` có đoạn code:
  ```python
  if any(k in flat for k in ["trang tinh duoi cung", "dang ho tro:", "supporting:"]) or "fxs" in xml:
      log("   [profile] dismiss bottom sheet modal (fxs) via Huy tap + BACK")
      tap(device_id, 540, 1842, wait=D_SHORT)
      keyevent(device_id, 4, wait=D_SHORT)
      time.sleep(D_SHORT)
      continue
  ```
- **Lỗi 1 (False Match):** Mọi Bottom Sheet trong ứng dụng TikTok bản tiếng Việt (kể cả Account Switcher "Chuyển đổi tài khoản", popup chia sẻ, bình luận...) đều có container mang thuộc tính `content-desc="Trang tính dưới cùng"`. Do đó, điều kiện `k in flat for k in ["trang tinh duoi cung"]` luôn luôn `True` mỗi khi có bất kỳ bottom sheet nào đang mở (kể cả Account Switcher)!
- **Lỗi 2 (Blind Tap nguy hiểm):** Tọa độ `(540, 1842)` là tọa độ chính giữa phía dưới màn hình (độ phân giải 1080x1920). Trên giao diện chính của TikTok, đây chính là **nút "+" Tạo video / Mở Camera** (`[432, 1780][648, 1920]`)!
- Khi lệnh tap `(540, 1842)` được thực thi:
  1. TikTok mở giao diện Camera quay video (`com.ss.android.ugc.aweme.shortvideo.ui.VideoRecordNewActivity`).
  2. Lệnh `keyevent 4` (BACK) hoặc handler `dismiss Camera / Create video screen` cố gắng đóng camera quay lại màn hình trước.
  3. Màn hình trước lại là Profile/Home có bottom sheet, `dismiss_profile_overlays` lại thấy `"trang tính dưới cùng"`, lại blind tap `(540, 1842)` mở Camera!
  4. Vòng lặp tử thần (infinite camera open/close loop) diễn ra liên tục cho đến khi tiến trình cha timeout 180s.

## 3. Quy chuẩn Khắc phục (Patch Contract)

### A. Xử lý màn One-Tap Fast Login trong `ensure_login_entry_screen` (`tiktok_login_v1.py`)
Kiểm tra ngay đầu hàm `ensure_login_entry_screen`:
```python
def ensure_login_entry_screen(device_id, stt=None):
    xml = get_ui_xml(device_id)
    if is_auth_landing_screen(xml):
        log("[login-entry] App dang o man auth landing -> vao login truc tiep")
        return

    flat = strip_accents(xml).lower()
    if any(k in flat for k in ["chao mung ban tro lai", "welcome back"]) or "them tai khoan khac" in flat:
        log("[login-entry] Phat hien man One-tap / Chao mung ban tro lai -> tap Them tai khoan khac de vao form login")
        if find_text_tap(device_id, "Thêm tài khoản khác", "Them tai khoan khac", "Add another account", wait=D_LONG):
            time.sleep(D_LONG)
            return

    go_to_profile(device_id)
    xml_after_profile = get_ui_xml(device_id)
    if is_auth_landing_screen(xml_after_profile):
        log("[login-entry] Sau khi tap profile ra auth landing -> vao login truc tiep")
        return

    flat_after = strip_accents(xml_after_profile).lower()
    if any(k in flat_after for k in ["chao mung ban tro lai", "welcome back"]) or "them tai khoan khac" in flat_after:
        log("[login-entry] Sau khi tap profile ra man One-tap -> tap Them tai khoan khac")
        if find_text_tap(device_id, "Thêm tài khoản khác", "Them tai khoan khac", "Add another account", wait=D_LONG):
            time.sleep(D_LONG)
            return
    ...
```

### B. Bảo vệ Account Switcher & Triệt tiêu Blind Tap đáy trong `dismiss_profile_overlays` (`social_reg_v1.py`)
```python
    # Loại bỏ chuỗi generic "trang tinh duoi cung", bảo vệ Switcher, cấm blind tap (540, 1842)
    if (any(k in flat for k in ["dang ho tro:", "supporting:"]) or "fxs" in xml) and not _account_dropdown_open_xml(xml):
        log("   [profile] dismiss bottom sheet modal (fxs)")
        if not find_text_tap(device_id, "Hủy", "Huy", "Cancel", "Đóng", "Close", wait=D_SHORT):
            keyevent(device_id, 4, wait=D_SHORT)
        time.sleep(D_SHORT)
        continue
```

## 4. Quy tắc Bất biến khi Sửa Code Điều hướng (Invariants)
1. **Tuyệt đối KHÔNG dùng chuỗi generic như `"trang tính dưới cùng"` (Bottom Sheet)** làm điều kiện phát hiện modal lạ để đóng vì mọi sheet chức năng (bao gồm Switcher) đều mang thuộc tính này.
2. **Tuyệt đối KHÔNG blind tap vào vùng đáy trung tâm `(x~540, y>=1780)`** trên giao diện TikTok vì đây là vị trí phím Tạo video / Camera (+). Blind tap vào đây sẽ kích hoạt Activity quay phim và làm gãy toàn bộ flow đăng nhập.
3. Khi gặp màn hình One-Tap / Fast Login ("Chào mừng bạn trở lại"), nút `"Thêm tài khoản khác"` là gateway chính tắc đưa thẳng vào danh sách phương thức đăng nhập ("Dùng SĐT / Email / Tên người dùng").
