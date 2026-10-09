# Mode 2 Degraded Fallback & Farm Alert Dual-Gate

## 1. Bối cảnh & Hiện tượng (2026-09-28)
- Trong phiên nuôi acc TikTok, nick lướt feed thực hiện Follow tự nhiên (`natural_follows`) thành công bình thường (2-4 lượt).
- Tuy nhiên bước Follow chéo (`follow-hook`) qua `tiktok-follow` chạy được đúng 1 lượt (follow anchor) rồi dừng hẳn hoặc 0 lượt.
- Nguyên nhân: Module 2 (Anchor following list) khi vào profile anchor bấm vào dòng chỉ số "Đã follow" (Following), màn hình danh sách relation không render đúng tab hoặc UiAutomator không bắt kịp `selected="true"`.
- Code cũ: Sau 2 lần thử mở tab fail văng `MANUAL_REVIEW`, set `failed=True` và `break` làm dừng toàn bộ session, đồng thời chặn luôn Module 1 (Search follow bù) vì `follow_engine` chỉ kích hoạt Module 1 khi `res.status == STATE_OK`.

## 2. Thiết kế Dual-Gate (Fallback Bù nhưng Vẫn Bắn Farm Alert)
Khi Module 2 lỗi kỹ thuật nhưng cần cứu vãn phiên follow:
1. **Chủ động tap tab "Đã follow":** Trong vòng lặp poll (`_open_following_tab`), nếu màn hình relation mở ra mà tab "Đã follow" chưa được chọn, script chủ động tìm node tab có text chứa `đã follow` / `đang follow` / `following` và tap trực tiếp vào tab thay vì đợi timeout.
2. **Safe-skip thay vì Abort:** Khi anchor fail mở tab sau ladder (lần 2), script **không abort session** thành `MANUAL_REVIEW`, mà:
   - Ghi nhận cờ: `res.details["mode2_degraded"] = True`
   - Lưu lý do chi tiết vào: `res.details["mode2_degraded_reasons"]`
   - Lùi về Feed an toàn (`_back_to_feed`), sau đó `continue` chuyển sang anchor tiếp theo.
   - Session vẫn giữ status hợp lệ để Module 1 (Search follow bù) kích hoạt chạy bù quota.
3. **Farm Alert Gate tại Runner Farm (`multi_machine_feed_session.py`):**
   - Parser đọc cờ `mode2_degraded` từ payload kết quả.
   - Điều kiện alert:
     ```python
     elif (proc.returncode != 0 or bool(result.get("failed"))
           or result.get("status") != "OK" or has_contract_error
           or bool(result.get("mode2_degraded"))):
     ```
   - Kể cả khi Module 1 chạy bù thành công khiến status trả về là `OK` (`failed=0`, `exit_code=0`), **hệ thống vẫn lập tức bắn Farm Alert** qua `send_farm_machine_alert`.
   - `result_log` được đánh dấu là `"script_error"` (thay vì `"ok"`).
   - Nội dung cảnh báo hiển thị rõ ràng: `mode2_degraded: mở tab Đã follow fail cho @<anchor> sau ladder (lần 2)`.

## 3. Đối soát Following trong Watchdog (`feed_session_watchdog.py`)
- Lỗi đối soát lệch ảo giữa Web và Script: Khi đối soát số lượng following tăng thật trên TikTok Web so với script báo cáo, hàm `reconcile_cluster_following` phải nhận `all_machines` từ session manifest.
- BẮT BUỘC cộng gộp cả:
  - `cross_cnt`: Lượt follow chéo từ `all_follows[m]["followed"]`
  - `nat_cnt`: Lượt follow tự nhiên từ `all_machines[m]["natural_follows"]`
  - `cnt = cross_cnt + nat_cnt`
- Nếu chỉ tính `cross_cnt` sẽ gây lệch ảo nghiêm trọng khi nick có follow tự nhiên trong lúc lướt feed.
