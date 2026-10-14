# Watchdog Alert Storm & Retry Denominator Governance (2026-10-15)

## 1. Context & Triệu chứng Sự Cố
Vào lúc 04:50 sáng, kênh Farm Alert (`telegram:-5373649734`) bị xả hàng loạt tin nhắn và danh sách 31 máy lỗi, kéo theo việc Hermes Gateway tự động kích hoạt phiên phản ứng sự cố chạy 95 tool calls ngầm:
1. **Tin nhắn 1 (`🚨 FARM ALERT: LỖI SCRIPT / PIPELINE`)**: Báo `Đa số máy dọn cache thất bại/timeout (31/36 máy fail): ...`
2. **Tin nhắn 2 (`Cronjob Response`)**: Xả tiếp bài báo cáo stdout `[BÁO CÁO DỌN DẸP CACHE TIKTOK] • Đã hoàn tất: 123 máy` kèm 31 dòng lỗi đơn lẻ `- Máy N: Timeout` choáng toàn bộ màn hình Telegram.

## 2. Phân Tích Nguyên Nhân Gốc Rễ (3 Lỗi Kỹ Thuật Cộng Dồn)
1. **Double Delivery Loop (Kênh nhận tin trùng lặp giữa Script & Cron Engine)**:
   - Script watchdog `cron_clear_tiktok_cache.py` tự gọi hàm nội bộ `_send_clear_cache_alert()` bắn tin vào Telegram `DEFAULT_ALERT_CHAT_ID = "-5373649734"`.
   - Cùng lúc đó, cron job Hermes (`end-of-day-clear-tiktok-cache`) cấu hình `deliver: telegram:-5373649734`. Khi script hoàn thành và in báo cáo ra stdout, Hermes cron engine lại bắt stdout này gửi tiếp vào đúng kênh Alert đó.
2. **Batch Retry Denominator Drift (Lệch mẫu số đợt retry sinh cảnh báo giả)**:
   - Script chạy theo nhịp: Đợt 1 chạy toàn farm (154 máy), đợt cuối chỉ retry 36 máy còn sót.
   - Khi tính tỷ lệ lỗi để quyết định giật chuông báo động:
     ```python
     if total_attempted > 0 and f_count >= 5 and f_count > (total_attempted * 0.3):
         alert_msg = f"Đa số máy dọn cache thất bại/timeout ({f_count}/{total_attempted} máy fail): ..."
     ```
     Biến `total_attempted` trong đợt retry chỉ bằng 36 (thay vì 154 toàn farm). Kết quả là chuỗi text `(31/36 máy fail)` (~86%), tạo ra ảo giác farm sập nặng nề, trong khi thực tế toàn farm đã hoàn tất 123/154 máy (80% thành công).
3. **Uncollapsed Failure Lines (Xả danh sách dòng đơn lẻ làm rác Telegram)**:
   - Thay vì gom các máy cùng mã lỗi vào một dòng (ví dụ: `• Timeout (30 máy): M01, M02...`), script in lặp 31 dòng `- Máy N: Timeout`, chiếm dụng chiều cao màn hình Telegram, gây spam kênh điều hành và kích hoạt session loop ngầm.

## 3. Quy Chuẩn Kỹ Thuật Cưỡng Chế (Hard Technical Governance)

### A. Quy tắc Deliver Governance (Chống Double Alert)
- Mọi cronjob Hermes nếu script thực thi đã có logic tự gửi alert (`send_farm_script_alert` / `send_farm_machine_alert`) thì cấu hình cron BẮT BUỘC đặt `deliver: local`.
- Chỉ cấu hình `deliver: telegram:<chat_id>` cho watchdog thuần (no-agent watchdog) khi script KHÔNG có logic tự bắn Telegram và chỉ in ra stdout khi có biến động.

### B. Quy tắc Fleet Denominator Invariant (Chống Lệch Mẫu Số Retry)
- Mọi công thức đánh giá ngưỡng Farm Alert (>30% lỗi hoặc >= 8 máy) BẮT BUỘC tính trên tổng quy mô online toàn farm (`cleared / fleet_total` hoặc `failed / fleet_total`).
- **CẤM TUYỆT ĐỐI** dùng `total_attempted` của riêng nhịp retry làm mẫu số đánh giá tỷ lệ sập farm.

### C. Quy tắc Collapsed Grouping Invariant (Nén Danh Sách Báo Cáo)
- Trong mọi bản tin báo cáo stdout / Telegram, các máy gặp cùng mã lỗi (Timeout, WIDGET_MISS, Offline) BẮT BUỘC phải gom nhóm theo failure signature trên cùng 1 dòng danh sách:
  ```text
  • Timeout (30 máy): 01, 02, 14, 67, 68, 73, 76, 208, 211, 214, 217...
  • WIDGET_MISS (1 máy): 264
  ```
- **CẤM TUYỆT ĐỐI** in loop `- Máy N: <Reason>` từng dòng một khi danh sách lỗi >= 3 máy.
