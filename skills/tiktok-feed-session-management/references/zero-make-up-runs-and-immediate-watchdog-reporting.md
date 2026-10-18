# Invariant Bỏ Chờ Chạy Bù & Chốt Báo Cáo Ngay (Zero Make-up Runs)

## 1. Bản chất & Nguyên tắc thực tế trên Phone Farm
- **Không có cơ chế chạy bù (No Make-up Runs):** 
  Khi feed runner (hoặc cron batch) đã hoàn thành quét toàn bộ dàn máy trong ca nuôi, tiến trình tắt hẳn (`runner_busy == False`). Farm tuyệt đối không có cơ chế tự động spawn lại lẻ tẻ giữa đêm để chạy bù cho riêng các máy bị kẹt lock hay lỗi.
- **Trạng thái cuối cùng của phiên:**
  Máy nào thành công ghi nhận thành công; máy nào kẹt device lock (`skipped-device-locked`) hoặc gặp lỗi mạng/app thì ghi nhận trực tiếp vào nhóm lỗi tương ứng. Đó là kết quả hoàn chỉnh duy nhất của phiên đó.

## 2. Lỗ hổng Watchdog om báo cáo sang rạng sáng (02:00 AM)
- **Triệu chứng:** Ca 3 Phiên 2 (20:00 tối) chạy xong lúc 21:28, nhưng đến tận 02:00 sáng hôm sau Watchdog mới gửi báo cáo lên Telegram, gây hiểu lầm nghiêm trọng cho Operator là có ca nuôi chạy lúc nửa đêm (trái với lịch đã bỏ Ca 0h).
- **Nguyên nhân gốc rễ:**
  1. Trong hàm `can_report_session()`, biến `has_unattempted_locked` phát hiện có máy bị kẹt lock dở dang (ví dụ do tool mạng đo `farm_network_gate` chạy đè lúc 20:00) -> Watchdog suy diễn máy đang chờ mở lock để chạy bù nên trả về `False`, chặn đứng việc chốt báo cáo trước 24:00.
  2. Sau 24:00 (sang ngày mới, `is_today == False`), code lại chứa logic cũ: `if now_hm < "02:00" and completed_expected_count < expected_count: return False` (hoãn chốt phiên hôm qua đến sau 02:00 sáng để "tránh chốt vội phiên đêm").
- **Hệ quả:** Báo cáo bị om suốt từ 21:28 đến đúng 02:00:59 sáng mới bung ra.

## 3. Quy tắc chuẩn hóa (Zero Make-up Delay Invariant)
1. **Runner idle > 15 phút là chốt ngay:**
   - Khi `runner_busy == False` và lượt chạy mới nhất kết thúc quá 15 phút (`latest_run_minutes_ago >= 15`), Watchdog BẮT BUỘC chốt báo cáo ngay lập tức trong phiên (khoảng 21:45 - 22:00 tối), tuyệt đối không chờ hết window 24:00.
2. **Không chặn vì `has_unattempted_locked` khi runner đã xong:**
   - Máy bị `skipped-device-locked` đã có kết quả ghi nhận rõ ràng. Không được lấy cớ kẹt lock để hoãn báo cáo toàn farm.
3. **Bỏ khóa 02:00 sáng cho phiên hôm trước:**
   - Với phiên hôm trước (`is_today == False`), chỉ cần `not runner_busy` là chốt báo cáo ngay lập tức, triệt tiêu hoàn toàn mốc delay 02:00 sáng.
