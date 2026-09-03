# Taadaa Farm Automation Case Fix Catalog & Anti-Patterns

## 1. Case UI-01: False-Positive Camera Overlay (Negative Exclusions Invariant)
- **Cơ chế lỗi:** Quét substring từ khóa thô trên toàn bộ XML dump (`10 phút, 60s, 15s, ẢNH, VĂN BẢN, 10m, Photo, Templates, CAMERA`). Trang Hồ sơ chuẩn của TikTok luôn có `Ảnh hồ sơ` (khớp `ẢNH`) và nút `Camera` (khớp `CAMERA`) -> `match_count >= 2` luôn đúng trên 100% máy bình thường. Script gửi phím BACK để "tắt camera" làm văng khỏi Profile về lại FYP, không đọc được username (`detected: null`), kết luận sai `profile account mismatch` và kích hoạt khóa giữ hiện trường 28 máy.
- **Quy tắc bất biến:**
  1. **Negative Exclusions là BẮT BUỘC:** Khi màn hình có các thành phần Profile (`Đã follow`, `Follower`, `Sửa hồ sơ`, `Menu hồ sơ`, `Thêm tiểu sử`...) hoặc Bottom Nav FYP (`Trang chủ` + `Hộp thư`/`Hồ sơ`) -> Tuyệt đối không nhận diện là camera hay popup kẹt.
  2. **Yêu cầu cụm từ chế độ quay đặc thù:** Tối thiểu 2 chế độ quay thật (`15s`, `60s`, `10 phút`, `10m`, `templates`, `văn bản`, `tạo`) hoặc 1 chế độ quay + 1 công cụ camera (`lật`, `hẹn giờ`, `tốc độ`, `bộ lọc`, `thêm âm thanh`).
  3. **Tách biệt lỗi UI và lỗi tài khoản:** Bấm trượt/chưa chuyển tab Profile (`detected: null`) tuyệt đối không quy kết thành `account mismatch`.

## 2. Case CRON-01: Cron & Watchdog Synchronization (Preflight Auto-Reap)
- **Cơ chế lỗi:** Reaper chạy định kỳ ở `0,15,30,45`, Watchdog chạy ở `11,26,41,56`. Lock chạm 120 phút ở `52` thì Watchdog quét thấy ở `56` và bắn cảnh báo Telegram `QUÁ HẠN > 2H` trước khi Reaper kịp dọn ở `00`, sinh ra cảnh báo rác "Tại sao quá 2h đéo tự unlock".
- **Quy tắc bất biến:**
  1. **Preflight Auto-Reap:** Trước khi scan danh sách báo cáo device lock gửi Telegram, script watchdog phải chủ động trigger chạy `reap-dead-owner-locks.py` để dọn dẹp các lock đã hết hạn TTL (2h) hoặc dead-owner.
  2. **Xếp lịch Cron đồng bộ:** Xếp lịch Watchdog chạy sau Reaper 1 phút (`1,16,31,46 * * * *`).

## 3. Quy trình Chốt phiên bắt buộc với Farm Automation (Gate 0.5)
- Bất kỳ session nào có sửa code/logic liên quan đến Farm Automation (UI, Cron, Sync, Lock, ADB, Workbook...), **BẮT BUỘC phải cập nhật Case Fix thực tế và Anti-Pattern tương ứng vào `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`)** trước khi Model Review và Commit.
- Trước khi bắt đầu viết/sửa script tương tác UI, **BẮT BUỘC phải đọc và đối chiếu `docs/farm-automation-cases.md`** để không bao giờ tái phạm các pattern gây lỗi cũ.
