# Profile Identity Drift & Account Switcher Recovery (Case 125, 137, 138)

Tài liệu vận hành, cơ chế lỗi và giải pháp cho sự cố đối soát sai danh tính tài khoản (`profile username still mismatched after switch`) và kẹt switch account trên hệ thống Farm TikTok.

---

## 1. Lỗi Đối Soát Sai Danh Tính Do Drift Về Home Feed (Case 125)

### Triệu chứng:
- Alert Farm `[MÁY N]`: `manual-needed: profile username still mismatched after switch`.
- Màn hình dừng tại Trang chủ (For You Feed), đang phát video của một creator ngẫu nhiên.
- Log đối soát danh tính hiển thị username đọc được là `@creator` của video thay vì nick của máy nuôi.

### Nguyên nhân gốc rễ (Anti-Pattern):
1. **Lọt màn hình trong `_profile_guard_drifted_from_profile`:**
   - Hàm kiểm tra drift trước đây chỉ kiểm tra:
     ```python
     if "keyboard cleanup" in reason:
         return True
     return xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS
     ```
   - Khi TikTok đổi tài khoản hoặc reload phiên bị rơi về Home Feed nhưng bản dump XML hoàn chỉnh (`xml_error == ""`), hàm trả về `False`, khiến runner tưởng nhầm app vẫn đang ở Profile.
   - Code trôi xuống `read_profile_identity()`, parse nhầm caption/creator trên Feed làm username máy nuôi và kích hoạt dừng phiên an toàn `profile username still mismatched after switch`.

### Giải pháp chuẩn (Case Fix):
1. **Khẳng định Home Feed là Drift:**
   - Trong `_profile_guard_drifted_from_profile`, bắt buộc kiểm tra:
     ```python
     if detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}:
         return True
     ```
     kể cả khi XML dump không có degraded error.
2. **Auto Re-tap Profile:**
   - Trong `_read_profile_identity_with_add_phone_guard`, khi phát hiện app bị trôi về Feed, lập tức kích hoạt `_try_profile_retap_on_drift` re-tap tab Hồ sơ (`[972, 1857]`) để đưa app về đúng Profile trước khi đọc danh tính.

---

## 2. Cơ Chế Click Button Switcher vs Child TextView (`_find_account_switch_option`)

### Hiện tượng:
- Switcher bottom sheet (`Chuyển đổi tài khoản`) mở lên đầy đủ.
- Tọa độ tap được tính dựa trên child `TextView` (`id/mtx` hoặc `id/n72` tại `x ≈ 397`):
  ```python
  # Anti-pattern: Override bounds container sang child TextView
  best_bounds = inner.bounds
  ```
- Trên một số phiên bản TikTok cũ (ví dụ 46.2.3 trên Galaxy S7) hoặc theme máy, child `TextView` có `clickable="false"`, trong khi view cha `android.widget.Button` (`id/l9b` hoặc `id/lkp`) có `clickable="true"`.
- Việc gửi `input tap` vào tâm child TextView bị nuốt sự kiện, không kích hoạt click của Button cha khiến dấu kiểm (`id/fdu`) không dịch chuyển sang tài khoản mới.

### Giải pháp chuẩn:
- Khi view hàng container là `Button` (`clickable=True`), ưu tiên giữ nguyên bounds của container (`best_bounds = node.bounds` với center `x=540`) để đảm bảo lệnh tap ăn vào Button của TikTok:
  ```python
  if node.attributes.get("clickable", "false").casefold() == "true":
      best_bounds = node.bounds
  elif node.bounds is not None and (node.bounds[2] - node.bounds[0]) >= 600:
      # Chỉ fallback tìm inner text khi container không phải là view clickable trực tiếp
  ```

---

## 3. "Cha Khóa Cửa Con" Khi Reconcile Missing Account (Case 138 - Lock Inheritance)

### Triệu chứng:
- Khi nick chỉ định trong Row workbook chưa đăng nhập sẵn trên máy, tiến trình cha `multi-machine-feed-session` khởi chạy subprocess `reconcile_tiktok_accounts.py`.
- Subprocess con kết thúc sau 2 giây với return code 4 (`SKIPPED_LOCKED`).
- Tiến trình cha báo lỗi auto-login thất bại và dừng phiên với `profile username still mismatched after switch`.

### Nguyên nhân gốc rễ:
- Subprocess con cố gắng chiếm device lock (`acquire_device_lock`), nhưng device lock đang được giữ bởi chính tiến trình cha (PID active). Hệ thống lock fail-closed từ chối cấp quyền để chống 2 tiến trình độc lập giẫm chân nhau.

### Giải pháp chuẩn:
1. **Cờ `--allow-parent-lock`:**
   - Trong `feed_swipe_smoke.py` (`_maybe_recover_missing_account_via_login`), truyền cờ `--allow-parent-lock`.
2. **Kế thừa quyền qua `InheritedDeviceLock`:**
   - Trong `tiktok-log-in` (`account_reconcile.py`), khi phát hiện active lock thuộc `PARENT_LOCK_PROJECTS` và có cờ `--allow-parent-lock`, cấp `InheritedDeviceLock()` (no-op lease) cho worker con để hoàn tất nạp tài khoản mà không xung đột với lock của cha.

---

## 4. Quản Lý Mapping 8 Row và Phân Bổ APK Theo Đợt Farm

1. **Mapping 8 Row (`taikhoan_run_safe.xlsx`):**
   - Từ Case 137, farm mở rộng hỗ trợ 8 slot/máy (Row 1..8).
   - Mỗi máy có thể có các tài khoản rải rác ở các row (ví dụ Máy 79: Row 1 = `shirldlpbkg`, Row 2 = `lavincghb5r`, Row 3 = `liddiwad5cr`, Row 4 = `refughbmh33`, Row 6 = `ruffumyxkvv`).
   - Khi chạy Canary test, đối soát chính xác Row tương ứng với nick active hoặc nick mục tiêu cần kiểm chứng.

2. **Cập nhật APK trên mạng Farm USB:**
   - Tránh chạy `adb install-multiple` trực tiếp gói split APK (~200MB) trên nhiều máy cùng lúc khi các hub USB đang chịu tải cao (băng thông rơi xuống ~0.1 MB/s gây timeout).
   - Khi cần nâng cấp hàng loạt, thực hiện đẩy file nền vào `/data/local/tmp/` trước hoặc chạy vào khung giờ nghỉ ca (00:00 - 01:00).
