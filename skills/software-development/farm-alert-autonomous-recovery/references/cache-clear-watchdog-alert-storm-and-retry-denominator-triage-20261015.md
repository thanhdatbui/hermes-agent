# Cache Clear Watchdog Alert Storm & Retry Denominator Triage (2026-10-15)

## 1. Context & Triệu chứng
Vào lúc 04:50 sáng, kênh Farm Alert (`telegram:-5373649734`) bị xả hàng loạt tin nhắn và danh sách 31 máy lỗi, kéo theo việc Hermes Gateway tự động kích hoạt phiên phản ứng sự cố chạy 95 tool calls ngầm:
1. Tin nhắn 1: `🚨 [FARM ALERT: LỖI SCRIPT / PIPELINE] Đa số máy dọn cache thất bại/timeout (31/36 máy fail): ...`
2. Tin nhắn 2: `[BÁO CÁO DỌN DẸP CACHE TIKTOK] • Đã hoàn tất: 123 máy` xả tiếp 31 dòng máy lỗi đơn lẻ (`- Máy 208: Timeout...`).

## 2. Root Cause Analysis
Có 3 nguyên nhân cốt lõi gây ra tình trạng alert spam và số liệu mâu thuẫn:
1. **Double Delivery Loop (Kênh nhận tin trùng lặp)**:
   - Script watchdog `cron_clear_tiktok_cache.py` tự gọi hàm nội bộ `_send_clear_cache_alert()` bắn tin vào `DEFAULT_ALERT_CHAT_ID = "-5373649734"`.
   - Cùng lúc đó, cron job Hermes (`end-of-day-clear-tiktok-cache`) cấu hình `deliver: telegram:-5373649734`. Khi script hoàn thành và in báo cáo ra stdout, Hermes cron engine lại bắt stdout này gửi tiếp vào đúng kênh Alert đó.
2. **Batch Retry Denominator Drift (Lệch mẫu số đợt retry)**:
   - Script chạy cuốn chiếu: Đợt đầu chạy toàn farm (154 máy), đợt cuối chỉ retry 36 máy còn sót.
   - Khi tính tỷ lệ lỗi để quyết định giật chuông báo động:
     ```python
     if total_attempted > 0 and f_count >= 5 and f_count > (total_attempted * 0.3):
         alert_msg = f"Đa số máy dọn cache thất bại/timeout ({f_count}/{total_attempted} máy fail): ..."
     ```
     Biến `total_attempted` trong đợt retry chỉ bằng 36 (thay vì 154 toàn farm). Kết quả là `31/36 máy fail` (~86%), tạo ra ảo giác farm sập nặng nề, trong khi thực tế toàn farm đã hoàn tất 123/154 máy (80% thành công).
3. **Uncollapsed Failure Lines (Xả danh sách dòng đơn lẻ)**:
   - Thay vì gom các máy cùng mã lỗi vào một dòng (ví dụ: `• Timeout (30 máy): M01, M02...`), script in lặp 31 dòng `- Máy N: Timeout`, chiếm dụng chiều cao màn hình Telegram và làm loãng luồng giám sát.

## 3. Quy chuẩn phòng chống & Invariants
1. **Quy tắc kênh phát hành (Deliver Governance)**:
   - Các watchdog / cron script đã tích hợp sẵn cơ chế tự bắn alert có chọn lọc (`send_farm_script_alert` / `send_farm_machine_alert`) thì cấu hình cron Hermes BẮT BUỘC đặt `deliver: local` hoặc chỉ gửi stdout khi có sự cố thực sự.
   - Tuyệt đối không cấu hình cron `deliver: telegram:<alert_channel>` cho các script in báo cáo chi tiết hàng ngày nếu script đó đã có logic tự bắn Telegram.
2. **Quy tắc mẫu số đánh giá (Fleet Denominator Invariant)**:
   - Mọi ngưỡng kích hoạt Farm Alert cấp hệ thống (>30% lỗi hoặc >= 8 máy) BẮT BUỘC tính trên tổng quy mô online toàn farm (`cleared / fleet_total` hoặc `failed / fleet_total`).
   - CẤM TUYỆT ĐỐI dùng `total_attempted` của riêng nhịp retry làm mẫu số đánh giá tỷ lệ sập farm.
3. **Quy tắc nén danh sách lỗi (Collapsed Grouping Invariant)**:
   - Trong mọi bản tin báo cáo stdout / Telegram, các máy gặp cùng mã lỗi (Timeout, WIDGET_MISS, Offline) BẮT BUỘC phải gom nhóm theo failure signature trên cùng 1 dòng danh sách:
     ```text
     • Timeout (30 máy): 01, 02, 14, 67, 68, 73, 76, 208, 211, 214, 217...
     • WIDGET_MISS (1 máy): 264
     ```
   - CẤM TUYỆT ĐỐI in loop `- Máy N: <Reason>` từng dòng một khi danh sách lỗi >= 3 máy.
