# Compensatory Feed Run Safety & Cadence Parity (Quy Trình Thẩm Định Chạy Bù Nuôi Acc)

## 1. Bối Cảnh & Vấn Đề
Khi vận hành Farm 80-160 máy Android (Samsung S7), các sự cố sụt nguồn Hub USB, rớt ADB kết nối hàng loạt, hoặc nghẽn Proxy 4G thường khiến một phiên nuôi acc (Row 1..8) bị văng nhiều máy (ví dụ chỉ 15–22/80 máy thành công, 58 máy failed).
Người vận hành thường có xu hướng muốn "chạy bù ngay bây giờ" (đặc biệt vào ban đêm hoặc giữa các ca).

Nếu Coordinator không nắm rõ chu kỳ và cấu trúc vận hành, rất dễ mắc 3 sai lầm nghiêm trọng:
1. Đọc trúng tài liệu cũ (lịch 4 ca có Ca 4 lúc 00:00/01:30) rồi phán đoán sai rằng farm đang chạy ca đêm.
2. Cho phép chạy bù đè vào Dead Zone (03:00 – 05:59) làm xung đột với cron dọn cache (`end-of-day-clear-tiktok-cache`), gây quá nhiệt phồng pin Samsung S7 và vỡ Ca 1 sáng (06:00).
3. Chạy lại toàn bộ 80 máy thay vì chỉ lọc máy lỗi, khiến nick đã thành công bị nuôi 2 lần (dễ dính spam/penalty của TikTok) hoặc chạy lại khi hạ tầng USB/Proxy chưa hồi phục dẫn đến kẹt lock diện rộng.

---

## 2. Quy Trình 4 Bước Thẩm Định Chạy Bù (Catch-Up Triage Protocol)

### Bước 1: Tra cứu Chu Kỳ 4 Ngày (Parity 96h) từ Base Date Chuẩn
Toàn farm đã chuẩn hóa sang **Chu kỳ cố định 4 ngày x 3 Ca x 2 Phiên / ngày (BỎ HOÀN TOÀN CA 0H ĐÊM)** áp dụng từ `2026-10-11`:
```python
import datetime

base_date = datetime.date(2026, 10, 11)
target_date = datetime.date.today()
cycle_day = (target_date.toordinal() - base_date.toordinal()) % 4
# cycle_day == 0 (Day 0): Ca 1 (Row 1) - Ca 2 (Row 3) - Ca 3 (Row 5)
# cycle_day == 1 (Day 1): Ca 1 (Row 2) - Ca 2 (Row 4) - Ca 3 (Row 6)
# cycle_day == 2 (Day 2): Ca 1 (Row 7) - Ca 2 (Row 8) - Ca 3 (Dưỡng sinh tối)
# cycle_day == 3 (Day 3): Dưỡng sinh xả tải toàn farm (pure feed / nghỉ ngơi)
```
- **Tuyệt đối KHÔNG suy đoán ngày chẵn/lẻ hay thứ trong tuần.**
- **Toàn bộ đêm từ 21:30 đến 05:59 sáng là vùng nghỉ (Dead Zone):** Không có ca nuôi chính thức nào hoạt động.

### Bước 2: Kiểm Tra 4 Chốt Chặn Khung Giờ & Xung Đột
1. **Chốt 1 — Khoảng nghỉ Dead Zone (03:00 – 05:59):**
   - 03:00 – 04:30 sáng là thời gian chạy đa luồng dọn dẹp cache TikTok toàn farm (`end-of-day-clear-tiktok-cache`).
   - Mọi tác vụ chạy bù ban đêm **BẮT BUỘC phải hoàn tất và nhả device lock trước 02:50 sáng**.
2. **Chốt 2 — Khoảng đệm Ca 1 Sáng (06:00):**
   - Ca 1 của ngày mới kích hoạt lúc 06:00.
   - Cần tối thiểu 60 phút nghỉ ngơi trước 06:00 để thiết bị hạ nhiệt, reset kết nối USB và tránh tranh chấp lock.
3. **Chốt 3 — Phục Hồi Hạ Tầng Trước Khi Chạy:**
   - Kiểm tra `adb devices` và trạng thái Proxy: nếu dải máy văng do `device is offline` hoặc `blocked-proxy-vpn` mà chưa cắm lại cáp/reset hub hoặc proxy chưa có IP mới, **TUYỆT ĐỐI KHÔNG CHẠY LẠI** vì sẽ lập tức fail tiếp và sinh ra hàng chục stale lock file `.lock.json`.
4. **Chốt 4 — Kỷ Luật Selective Re-run (CẤM Rerun 80 Máy):**
   - Đọc `summary.txt` của phiên văng để bóc tách:
     * Danh sách máy đã SUCCESS: **CẤM TUYỆT ĐỐI chạm vào**.
     * Chỉ lấy danh sách máy failed/skipped để chạy bù.
   - Chạy bù bắt buộc ở chế độ **Feed-only** (không upload hook, không follow dồn).

---

## 3. Quyết Định Mẫu Khi Nhận Yêu Cầu Chạy Bù
- **Trường hợp 1 (Khuyên dùng - Khuyến nghị an toàn): BỎ QUA CHẠY BÙ.**
  - Độ giãn cách Starve trong chu kỳ 4 ngày đã được thiết kế chịu được hụt 1 phiên không làm hỏng tài khoản.
  - Cho dàn S7 nghỉ ngơi, làm mát pin và dọn cache sạch sẽ trong đêm. Sáng hôm sau tập trung chạy chuẩn ca kế tiếp theo chu kỳ.
- **Trường hợp 2 (Nếu Operator yêu cầu chạy bù ngay):**
  - Giới hạn cứng: chỉ chạy các máy failed.
  - Set timeout chặt chẽ để kết thúc trước 02:50 sáng.
  - Giám sát tiến trình và dọn sạch device-lock ngay khi kết thúc.

---

## 4. Kỷ Luật Code Watchdog vs Đóng Phiên (Closeout Gate Invariant)
- **CẤM tùy tiện sửa code watchdog khi làm sạch tài liệu lịch:**
  - `feed_session_watchdog.py` cần giám sát 24/7 để bắt các phiên chạy bù on-demand / canary đêm nếu có phát sinh.
  - Nếu Coordinator tự ý xóa mốc `ca: 4 (00:00 - 06:00)` trong code watchdog mà không có hợp đồng nghiệp vụ rõ ràng, Closeout Gate (Sol Auditor) sẽ từ chối phê duyệt (REJECTED, < 85 điểm) vì tạo ra khoảng trống giám sát 8.5 giờ.
  - Phân định rõ ràng: Sửa tài liệu/skill để agent không hallucinate lịch ca nuôi, nhưng **GIỮ NGUYÊN cấu hình giám sát 24h của watchdog** trừ khi có chỉ đạo kiến trúc chuyên biệt.
