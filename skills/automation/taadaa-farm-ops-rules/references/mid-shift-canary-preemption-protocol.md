# Mid-Shift Preemption Canary Protocol (Giành Lock Chạy Canary Giữa Ca)

> 📌 **Bối cảnh & Bài học thực tế (2026-10-01)**:
> Khi user phát hiện nghi vấn hoặc yêu cầu kiểm tra đối soát bằng canary ngay giữa ca nuôi acc đang chạy (Ca 3 Row 5), Coordinator ban đầu do dự và đề xuất *"đợi 15-20 phút nữa khi ca chạy kết thúc"*.
> User đã chỉnh đốn trực tiếp: **"Đéo đợi. Giành lock chạy canary cho tao"**.
> Sau khi kích hoạt quy trình giành lock an toàn, canary đã chạy thành công trên Máy 8 (nick `@aliciwwt40z`) và chỉ ra chính xác lỗi false positive trong script follow.

---

## 1. Nguyên Tắc Vận Hành Chủ Động (Proactive Mid-Shift Execution)

1. **Tuyệt Đối Không Phản Kháng / Đóng Băng / Thụ Động Bắt User Chờ:**
   - Khi operator đã yêu cầu chạy canary kiểm chứng giữa ca, Coordinator PHẢI lập tức kích hoạt quy trình can thiệp an toàn có kiểm soát, TUYỆT ĐỐI CẤM viện cớ an toàn để trì hoãn hoặc ép user chờ hàng chục phút.
2. **Nguyên Tắc Cô Lập Máy (Machine Isolation Gate):**
   - Chỉ được giành lock trên 1 máy duy nhất không tham gia hoặc đã hoàn thành nhiệm vụ trong batch hiện tại.
   - Tuyệt đối không làm gián đoạn các máy còn lại của farm.

---

## 2. Quy Trình 5 Bước Giành Lock Chạy Canary An Toàn

### Bước 1: Rà soát và chọn máy rảnh an toàn (O(1) Inspection)
- CẤM quét toàn bộ farm. Chỉ dùng lệnh O(1) kiểm tra máy mục tiêu:
  `python D:/Taadaa/tools/inspect_machine.py <N>`
- Kiểm tra bảng tiến trình hệ thống qua `psutil`:
  Đảm bảo máy `<N>` KHÔNG có tiến trình con active (`run_follow`, `run_tiktok`, `multi-machine-feed-session`).
- Điều kiện thỏa mãn máy rảnh:
  + Màn hình đang `OFF (Sleep/Dozing)` hoặc `LauncherActivity` (Home screen).
  + Pin > 20%, kết nối ADB bình thường.

### Bước 2: Tạo file cấu hình Canary cô lập ngân sách O(1)
- **CẤM TUYỆT ĐỐI** dùng file config production (`config.example.yaml` hoặc config chạy 20-40 follow).
- Tạo file config canary riêng `D:/Taadaa/tiktok-follow/config/canary_machine<N>.yaml`:
  ```yaml
  adb_path: "C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe"
  tiktok_package: "com.ss.android.ugc.trill"
  workbook: "D:\\OneDrive\\TaadaaData\\kibe\\taikhoan_run_safe.xlsx"
  state_workbook: ""
  mode: "2"
  budget_per_day: 40
  budget_per_session_min: 1
  budget_per_session_max: 1
  budget_per_session: 1
  delay_min: 1
  delay_max: 3
  inter_follow_delay_min: 5
  inter_follow_delay_max: 10
  swipe_before_search: 2
  swipe_between_follows: 1
  verify_reload_retries: 2
  verify_sample_every: 1
  timezone: "Asia/Ho_Chi_Minh"
  max_machines: 1
  allow_device_reboot_recovery: true
  startup_wait_seconds: 60
  startup_poll_seconds: 1
  feed_timeout_seconds: 600   # BẮT BUỘC >= 600s, XEM CẠM BẪY MỤC 3!
  ```

### Bước 3: Chạy Dry-Run xác minh kế hoạch trước khi đụng thiết bị
```bash
PYTHONPATH="D:/Taadaa/tiktok-follow;D:/Taadaa/automation-core" \
"D:/Taadaa/python-envs/automation/Scripts/python.exe" \
-m follow_runner.run_follow --machine <N> --config config/canary_machine<N>.yaml \
--account-row-index <R> --force-preempt --dry-run
```
- Phải thấy `FOLLOW_PLAN` với đúng target nick và `budget_per_session: 1`.

### Bước 4: Chạy Canary qua Background Process có Notify
- Vì follow runner chạy thật trên thiết bị mất 1-3 phút, lệnh foreground sẽ chạm trần 60s (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
- BẮT BUỘC dùng:
  `terminal(background=True, notify_on_complete=True, command="...", workdir="D:/Taadaa/tiktok-follow")`
- Tham số chạy:
  `... -m follow_runner.run_follow --machine <N> --config config/canary_machine<N>.yaml --account-row-index <R> --force-preempt --skip-identity-verify`
  + Cờ `--force-preempt`: Ghi đè lock cũ nếu có và giành quyền điều khiển máy.
  + Cờ `--skip-identity-verify`: Bỏ qua switcher nếu account row đã được xác định trước.

### Bước 5: Chụp ảnh nghiệm thu và đối soát Web ngay lập tức
- Ngay khi process kết thúc:
  1. Chụp ảnh màn hình qua ADB:
     `adb -s <serial> exec-out screencap -p > D:/Taadaa/runtime/kibe/canary_m<N>_result.png`
  2. Đính kèm `MEDIA:...` gửi ngay cho user.
  3. Cào đối soát trực tiếp TikTok Web (`https://www.tiktok.com/@<username>`) để so sánh số liệu `followingCount` trước và sau khi chạy. Báo cáo rõ runner báo khống hay server TikTok đã ghi nhận thật.

---

## 3. Cạm Bẫy Trọng Yếu: `feed_timeout_seconds` vs `reserve_seconds`

- **Hiện tượng:** Runner chạy exit code 0, báo `status: OK`, nhưng `followed: []`, `mode2_followed_count: 0`.
- **Nguyên nhân:** File config đặt `feed_timeout_seconds: 90`. Trong khi `has_time_for_next_action(reserve_seconds=180.0)` yêu cầu thời gian còn lại phải > 180s. Do `90 - 0 = 90 < 180`, vòng lặp follow bị break ngay lập tức ở giây đầu tiên!
- **Giải pháp:** Trong mọi config của follow runner, luôn đặt `feed_timeout_seconds: 600` hoặc `1200`.
