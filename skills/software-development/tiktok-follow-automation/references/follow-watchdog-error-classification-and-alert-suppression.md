# Root Cause Analysis & Phân Loại Lỗi Follow Watchdog (2026-09-13)

## 1. Hiện Tượng & Dữ Liệu Hiện Trường (Run `row-1-080347/20260913-080426`)
- Tổng số máy: 80 máy.
- Feed: 68 Success, 12 Fail.
- Follow chéo Watchdog báo cáo:
  - Success: 6 máy
  - Nhả follow: 9 máy
  - **Lỗi script/xác minh: 22 máy**
  - Bỏ qua: 38 máy

## 2. Bản Chất 22 Máy Bị Phân Loại Vào "Lỗi script/xác minh"
Watchdog tổng hợp từ `follow_result.json` do flow `tiktok-follow` (`mode2_follow_followers.py`) tạo ra.

### Nhóm A: 12 máy dính `anchor @<uid> không có video — back ra bỏ qua`
- **Danh sách máy**: M7, M9, M17, M33, M34, M37, M44, M47, M48, M52, M65, M68.
- **Bản chất**: Đây là cơ chế **Video Gate Mode 2** an toàn chuẩn. Anchor được bốc ngẫu nhiên từ pool Tik1/Tik2. Nếu anchor chưa đăng video nào, flow chủ động dừng và back ra an toàn để tránh việc follow profile trần (dễ bị nhả / checkpoint).
- **Lý do bị Watchdog gom vào "Lỗi script/xác minh"**:
  - Trong `mode2_follow_followers.py` (`_ensure_anchor_followed`), khi không có video cover node, hàm return `None` nhưng `run_mode2` lại gán:
    ```python
    res.status = "MANUAL_REVIEW"
    res.failed = True
    ```
    với `exit_code: 1`.
  - Watchdog kiểm tra: `if status in {"OK", "SUCCESS"}` -> success/skipped, còn lại toàn bộ `MANUAL_REVIEW` / `failed=True` bị xếp vào `fl_error` ("Lỗi script/xác minh").
  - **Hệ quả**: Báo động giả (False Positive) cho 12 máy skip an toàn.

### Nhóm B: 7 máy dính `MANUAL_REVIEW: mở tab Đã follow fail cho <uid> sau ladder (lần 2)`
- **Danh sách máy**: M23, M26, M32, M35, M43, M60, M80.
- **Bản chất**: Sau khi vào trang cá nhân Anchor, runner bấm tab "Đã follow / Following" để lấy danh sách acc nội bộ trong farm. Do UI TikTok lag/mạng 4G chuyển tiếp hoặc selector tab Following bị lệch sau animation, script thử lại 2 lần (ladder retry) nhưng không vào được list, chủ động fail-closed về `MANUAL_REVIEW` để bảo vệ nick.

### Nhóm C: 2 máy dính `follow-timeout`
- **Danh sách máy**: M12, M59.
- **Bản chất**: Hết budget thời gian dành cho follow hook trong phiên.

### Nhóm D: 1 máy dính lỗi UI recovery
- **Danh sách máy**: M56 (`MANUAL_REVIEW: không khôi phục được UI sau lỗi mở tab anchor @trn.m.m620`).

---

## 3. Vì Sao Farm Alert Không Bắn Tin Cảnh Báo Telegram Cho 22 Máy Này?
1. **Chốt chặn Batch Aggregator (`AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT`)**:
   - Mặc định biến môi trường này là `0` (suppress immediate machine alert).
   - Trong `automation_core/alerts.py`, hàm `_should_suppress_immediate_machine_alert()` sẽ trả về `True`, ngăn chặn việc từng máy lẻ gửi alert đỏ làm tràn ngập Telegram (chống alert storm khi chạy batch 80 máy).
2. **Watchdog Session Ngưỡng Mass-Fail > 30%**:
   - Watchdog phiên (`feed_session_watchdog.py`) chỉ gửi RED ALERT khi tỷ lệ lỗi Feed session vượt quá 30% (`(manual + blocked_proxy + failed) / total > 30%`).
   - Phiên này Feed chỉ lỗi 12/80 máy (~15%), các lỗi Follow hook là sub-pipeline không kích hoạt ngắt khẩn cấp toàn farm.

---

## 4. Quy Tắc Chuẩn Hóa Status Cho Runner Follow (Fix False Positive)
- Khi Anchor không có video (`anchor không có video — back ra bỏ qua`):
  - Phải set `res.status = "SKIPPED"` và `res.failed = False`, `exit_code: 0`.
  - Lý do: Đây là hành vi Safe-Skip có chủ đích theo thiết kế hệ thống, không phải lỗi script hay lỗi máy.
  - Watchdog sẽ gom 12 máy này vào nhóm **"Bỏ qua"** (`fl_skipped`), phản ánh đúng thực tế và không gây hoang mang cho người vận hành farm.
