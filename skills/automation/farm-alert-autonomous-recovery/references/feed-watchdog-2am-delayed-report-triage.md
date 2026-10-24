# Chẩn Đoán Báo Cáo Feed Watchdog Nổ Lúc 02:00 AM (Delay Báo Cáo Ca Tối Do Kẹt Device Lock)

## Hiện tượng
- Telegram nhận được thông báo: `📊 [TIKTOK NUÔI ACC] Ca 3 - Phiên 2/2 (Tối) hoàn tất (Row X)` vào khoảng **02:00 – 02:05 AM**.
- Operator nghi vấn: "Tại sao lại có ca nuôi chạy lúc 0h / 2h đêm trong khi đã chốt bỏ ca 0h đêm?"

## Bản chất kỹ thuật
1. **Ca 0h vẫn bỏ 100%:**
   - Khung giờ 21:30 – 05:59 là Dead Zone, `tiktok_runner.py` trả về `None`, không có batch nuôi nào được spawn ban đêm. Thư mục runtime ngày mới (ví dụ `live/YYYY-MM-DD`) chưa hề tồn tại lúc 2h sáng.
2. **Nguyên nhân Watchdog gửi muộn lúc 02:00 AM:**
   - Ca 3 Phiên 2 (20:00 tối hôm trước) kết thúc lúc ~21:30.
   - Nếu trong phiên có máy bị kẹt `Device Lock` (ví dụ `is_device_locked_skip = True`, máy bị chiếm lock bởi task khác hoặc kẹt owner), cờ `has_unattempted_locked = True` được bật.
   - Trong `feed_session_watchdog.py`, watchdog có cơ chế an toàn: **TUYỆT ĐỐI KHÔNG chốt báo cáo sớm** khi còn máy kẹt lock dở dang để chờ cơ hội chạy bù trong đêm.
   - Khi qua 00:00 (sang ngày mới, `is_today = False`), hàm `can_report_session` áp dụng luật:
     ```python
     # Nếu là hôm qua (is_today=False): chỉ cho phép báo cáo sau 02:00 sáng hôm nay để tránh chốt vội phiên đêm đang chạy dở
     if not is_today:
         if now_hm < "02:00" and completed_expected_count < expected_count:
             return False
         return True
     ```
   - Đến đúng `02:00` sáng, thời hạn hoãn báo cáo của phiên hôm trước hết hạn (`now_hm >= "02:00"`). Lúc này watchdog mới chính thức chốt sổ toàn bộ kết quả của Ca 3 tối hôm trước và xả tin nhắn tổng kết lên Telegram.

## Quy tắc kiểm chứng nhanh (O(1)) khi gặp alert/report lúc 2h sáng
1. Kiểm tra tiêu đề report: nếu là `Ca 3 - Phiên 2/2 (Tối) hoàn tất (Row ...)` thì chắc chắn 100% là báo cáo Ca tối hôm trước bị delay, không phải ca nuôi đêm.
2. Đối soát danh sách lỗi: xem trong mục `Fail` có máy nào bị `Kẹt Device Lock` không. Nếu có, đó chính là nguyên nhân kích hoạt hoãn báo cáo tới 02:00 AM.
3. Không vội vàng kết luận runner bị lỗi hay ca 0h bị bật lại; đối chiếu `runner_simple_state.json` và thư mục `runtime/<cluster>/live/` để xác nhận máy đã nghỉ từ 21:30.
