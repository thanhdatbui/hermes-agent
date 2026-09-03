# Follow máy 10 (anhtruong840) — Chuỗi lỗi & Nghiệm thu hoàn tất 2026-08-17

Session chạy follow thật máy 10 (row 1 `anhtruong840`, serial `988627464e374e3234`, mode both, budget 8) — chuỗi điều tra từng lớp và kết quả nghiệm thu thành công.

---

## 🏆 KẾT QUẢ NGHIỆM THU CUỐI CÙNG
- **Follow thành công:** **8/8 UID (100% budget_per_session)**:
  1. `doanthu1005`
  2. `quachtieu2106`
  3. `muyduyen4589`
  4. `hatien15118`
  5. `maichi21052`
  6. `.thy.v5`
  7. `giangqih2xm`
  8. `truong.thuy950` (Ảnh màn hình nghiệm thu nút hiển thị rõ **"Đã follow"**)
- **State JSON:** `runs/state/follow_state_10.json` ghi nhận `budget_used: 8/30`, `failed: False`.
- **Tổng kết:** Đã chuyển đổi hoàn toàn cơ chế đọc UI sang **ATX Session Primary (port 7912)** siêu nhanh, xử lý triệt để mở switcher bằng sticky header trên TikTok 46.4.3 layout mới và verify nick.

---

## Chuỗi 5 sự cố kỹ thuật & Cách khắc phục

### 1. Lần 1: máy reboot giữa chừng (NFC crash loop)
- **Triệu chứng:** Runner chạy ~6 phút → máy mất ADB (`device not found`) → runner chết.
- **Root cause:** NFC crash loop do antenna NG + service cố bật (`turning on`) -> `system_server_watchdog` reboot.
- **Fix:** `settings put secure nfc_on 0` + `pm enable com.android.nfc` + reboot → hết crash (0 tombstone).

### 2. Lần 2: OPEN_TIKTOK_FAILED (máy quá tải sau reboot)
- **Triệu chứng:** Máy reboot xong load ~17-19 (app nền YouTube, TikTok, GMS ăn CPU/RAM) -> TikTok kẹt SplashActivity không lên feed -> runner báo `OPEN_TIKTOK_FAILED`.
- **Fix:** Force-stop TikTok để giải phóng render buffer, chờ máy settle load ~6-8 trước khi chạy lại.

### 3. Lần 3: `FollowAdapter.dump_ui()` kẹt shell `uiautomator dump` (`ERROR: could not get idle state`)
- **Triệu chứng:** TikTok đang mở ở Feed video bình thường nhưng `_observe_feed_once` văng UIDumpError liên tục -> timeout 90s -> báo `OPEN_TIKTOK_FAILED`.
- **Root cause:** Trong `follow_runner/core/adapter.py`, hàm `dump_ui` gọi `capture_ui_xml(self._adb, lightweight=True, ...)` với các cờ probe lightweight (`deadline_seconds`, `foreground_probe`...). Trong `automation_core/ui.py:1420`, khi có `lightweight=True` hoặc lightweight probe keys, core **ép chạy nhánh `_dump_current_ui_lightweight` (shell `uiautomator dump`)** và **bỏ qua hoàn toàn ATX session primary (port 7912)**. Khi TikTok phát video liên tục animation, shell uiautomator kẹt `ERROR: could not get idle state`.
- **Fix:** Sửa `follow_runner/core/adapter.py::dump_ui` chỉ truyền `timeout` và `provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED` để core tự route qua ATX session port 7912 (`dumpWindowHierarchy`). Sau fix: XML dump tức thì trong 0.3s (độ dài 33KB - 98KB).

### 4. Lần 4: `AccountSwitcherError: SWITCHER_ANCHOR_AMBIGUOUS` trên TikTok 46.4.3 layout mới
- **Triệu chứng:** `open_account_switcher` fail dù trang Hồ sơ đã mở.
- **Root cause:** TikTok 46.4.3 đưa tên `@username` nằm lệch hẳn sang góc bên trái (không ở giữa đỉnh), không có mũi tên dropdown ở giữa -> `find_switcher_anchor` không tìm thấy.
- **Giải pháp:** Vuốt nhẹ từ dưới lên khoảng 400px (từ `y=0.65h` lên `y=0.42h` trong 200ms) -> tên tài khoản `display_name` nhảy lên sticky header chính giữa trên cùng (`com.ss.android.ugc.trill:id/pcq`) -> tap vào node này để bung popup Account Switcher.

### 5. Lần 5: `ACCOUNT_VERIFY_MISMATCH` sau khi switch account
- **Triệu chứng:** Switch account xong nhưng bước `verify_selected_account` báo không thấy `@anhtruong840`.
- **Root cause:** Sau khi scroll nhẹ lên để mở sticky header, text `@username` ở profile root bị cuộn khuất lên trên (header chỉ còn display name `Anh Trương`).
- **Fix (automation-core `account_switcher.py`)**: Trong `verify_selected_account`, nếu `expected not in values`, adapter thực hiện vuốt nhẹ ngược xuống (từ `y=0.25h` xuống `y=0.75h`) để kéo profile root về đỉnh -> text `@username` xuất hiện lại đầy đủ trong XML -> verify pass 100%.

---

## Bài học vận hành & STOP GATE
- **CẤM tự ý sửa code / xóa recovery mà chưa hỏi**: Khi gặp sự cố hoặc phân tích với user, không được tự tiện sửa recovery B1/B2/B3 khi chưa có lệnh rõ ràng.
- **CẤM script tự đóng app khi fail — giữ nguyên màn hình lỗi**: User: "Ai cho phép tự đóng app khai fail? Sửa lại cho tao. Giữ nguyên chỗ lỗi".
- **Giao tiếp & format ảnh**: Luôn gửi ảnh thật `MEDIA:C:\Users\...` ở dòng riêng (dùng backslash) và đọc ảnh bằng `vision_analyze` trước khi phân tích báo cáo.
