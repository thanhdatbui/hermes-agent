# Feed Watchdog Immediate Reporting (Bỏ Chờ Chạy Bù)

## Bối Cảnh Sự Cố (19/10/2026)
Vào lúc 02:00 sáng, Telegram nhận được báo cáo:
`📊 [TIKTOK NUÔI ACC] Ca 3 - Phiên 2/2 (Tối) hoàn tất (Row 6)`
Gây hiểu lầm nghiêm trọng cho Operator rằng Farm đang chạy ca đêm (00:00 - 02:00) dù Ca 0h đã được lệnh bỏ hoàn toàn.

## Nguyên Nhân Gốc (Root Cause)
1. **Ca 3 Phiên 2 thực tế đã chạy xong lúc 21:28 tối hôm trước.** Trong đợt chạy có Máy 7 bị `skipped-device-locked` do trùng lúc `farm_network_gate.py` đang đo mạng.
2. **Cơ chế chờ chạy bù gây nghẽn trong `can_report_session`:**
   - Khi có máy bị lock (`has_unattempted_locked = True`), Watchdog hiểu lầm rằng máy sẽ được mở lock để chạy bù sau đó, nên **chặn báo cáo trong toàn bộ cửa sổ phiên** (`now_hm < window_end_hm` tức 20:00 - 24:00).
   - Khi qua nửa đêm (`is_today = False`), Watchdog lại có điều kiện giữ báo cáo đến sau **02:00 sáng** (`if now_hm < "02:00" and completed_expected_count < expected_count: return False`) để tránh chốt vội phiên đêm.
   - Hậu quả: Đến đúng 02:00:59 sáng hôm sau Watchdog mới chịu xả báo cáo của Ca tối hôm trước.

## Nguyên Tắc Bất Biến (Invariant: Bỏ Chờ Chạy Bù)
1. **Không có cơ chế chạy bù giữa đêm:** Batch nuôi TikTok quét cuốn chiếu toàn farm một lần duy nhất cho mỗi phiên. Máy nào bị kẹt lock hay lỗi thì ghi nhận trực tiếp vào báo cáo (`Kẹt Device Lock` / `Fail`). Không om báo cáo chờ máy mở lock.
2. **Chốt báo cáo ngay khi Runner rảnh:**
   - Khi `runner_busy == False` và lượt chạy mới nhất cách đây $\ge 15$ phút (`latest_run_minutes_ago >= 15`): **BẮT BUỘC chốt và gửi báo cáo ngay lập tức** (thường vào khoảng 21:45 tối).
   - Chỉ chặn stale-run khi `completed_expected_count == 0` VÀ vẫn còn máy kẹt lock chưa từng được thử chạy (để chống chốt mù khi batch chưa kịp bắt đầu). Nếu đã có $\ge 1$ máy hoàn tất hoặc không còn lock unattempted $\rightarrow$ chốt ngay.
3. **Bỏ mốc khóa 02:00 sáng cho phiên hôm trước:** Với các phiên ngày hôm trước (`is_today == False`), bỏ hoàn toàn điều kiện `now_hm < "02:00"`. Bất kỳ lúc nào runner không bận (`not runner_busy`), chốt báo cáo ngay.
4. **Kiểm tra chặt chẽ kiểu dữ liệu thời gian:**
   - `latest_run_minutes_ago` bắt buộc phải là số thực hữu hạn:
     `isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val)`
   - Ngăn chặn hoàn toàn lỗi logic do `NaN`, `Inf`, âm, `None` hoặc kiểu `bool`.
5. **Telemetry Logging bắt buộc:**
   - Mọi nhánh quyết định (`report` hoặc `defer`) trong `can_report_session` bắt buộc ghi log có cấu trúc `[WATCHDOG_DECISION]` kèm đầy đủ ngữ cảnh (`decision`, `reason`, `is_today`, `completed`, `expected`, `latest_run_m`).
