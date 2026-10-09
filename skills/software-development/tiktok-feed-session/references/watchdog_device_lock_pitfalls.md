# Feed Session Watchdog: Xử Lý Tránh Chốt Phiên Sớm Khi Kẹt Device-Lock

## Hiện Tượng & Nguyên Nhân (Sự cố 2026-09-06)
- **Bối cảnh:** Ca đêm chạy batch đăng ký Gmail/Hotmail còn giữ lock `C:\Users\Kibe\.codex\device-locks\machine_X.lock.json` qua khung giờ Ca 1 Phiên 1 (06:00 - 07:30).
- **Nguyên nhân chốt sớm:**
  - Runner chạy đợt 1 (06:02) gặp device lock nên thoát sớm (06:11), ghi nhận 80 máy với `final_status: skipped-device-locked` / `reason: [device-lock] SKIP machine X: device lock active`.
  - Lúc 06:15:44, watchdog thức dậy thấy folder run có 80 machines và `runner_busy` đang False (chưa tới tick chạy lại 06:16).
  - Watchdog đếm toàn bộ 80 máy bị skipped lock vào `completed_expected`, thỏa mãn điều kiện `completed_expected_count >= expected_count`, lập tức gửi alert nhầm "Fail (80): M1..M80" lên Telegram và ghi `session_key` vào `feed_session_reported.json`.
  - Khi Gmail nhả lock, runner chạy lại đợt 2 (06:16 - 07:17) thành công 64 máy nhưng watchdog không bao giờ báo cáo lại vì key đã nằm trong state file.

## Quy Tắc Watchdog Chuẩn (Anti-Premature Close)
1. **Phân biệt máy chạy thật vs skipped-device-locked:**
   - Máy có `is_machine_skipped_locked(data) == True` (`skipped-device-locked`, `[device-lock]`, `device lock active`) CHƯA TỪNG chạy live attempt nào trong phiên.
   - Khi kiểm tra điều kiện chốt sớm (`now_hm < window_end_hm`), `completed_expected_count` CHỈ tính máy chạy thực tế.
2. **Điều kiện chốt báo cáo (`can_report_session`):**
   - **Guard 100% lock:** Nếu toàn bộ máy trong session đều là `skipped-device-locked` (`has_locked_only == True`), TUYỆT ĐỐI KHÔNG chốt gửi báo cáo.
   - **Chốt sớm trước giờ hết phiên:** Chỉ cho phép khi `completed_real_expected >= expected_count`, `locked_count == 0` và `not runner_busy`.
   - **Hết giờ phiên (`now_hm >= window_end_hm`):** Cho phép chốt nếu phiên có ít nhất 1 máy đã chạy thực tế.
3. **Merge đợt chạy (Multi-run merging):**
   - Kết quả chạy thực tế (dù `status: success` hay runtime failure như `blocked-proxy-vpn`, `manual-needed`) luôn ghi đè placeholder `skipped-device-locked`.
4. **Xử lý khôi phục khi watchdog đã chốt nhầm:**
   - Xóa `session_key` tương ứng (ví dụ `"2026-09-06_ca1_phien1"`) khỏi mảng `reported_sessions` trong file:
     `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json`
   - Đảm bảo JSON format hợp lệ để tick watchdog tiếp theo đọc và gửi lại báo cáo chính xác.
