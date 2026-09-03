# Watchdog Session Cadence & FEED_SESSION_MAX_SWIPES Cap Alignment (2026-08-24)

## 1. Watchdog Cadence Contract (Anti-Spam Discipline)
### Bối cảnh & Quy tắc vận hành
- Farm vận hành theo lịch: **3 Ca / ngày (Sáng, Chiều, Tối)**, mỗi Ca gồm **3 Phiên (Phiên 1/3, Phiên 2/3, Phiên 3/3)**.
- Runner có thể dispatch nhiều đợt sóng nhỏ (sub-batch mỗi 15 phút) trong cùng một phiên để gom máy rảnh.
- **YÊU CẦU NGHIÊM NGẶT CỦA USER:**
  - Tuyệt đối KHÔNG gửi thông báo Telegram sau mỗi sub-batch 15 phút (gây spam liên tục).
  - Watchdog script (`feed_session_watchdog.py`) bắt buộc phải gom tất cả các sub-batch thuộc cùng một khung giờ Phiên (`Ca X - Phiên Y/3`).
  - Chỉ gửi **ĐÚNG 1 BÁO CÁO TỔNG KẾT DUY NHẤT** khi toàn bộ Phiên đó hoàn tất (hết khung giờ phiên).
  - Nội dung: Tên phiên + Số lượng & Danh sách máy Success / Fail.

---

## 2. Lỗi Lệch Hằng Số `FEED_SESSION_MAX_SWIPES` (Fleet-wide Config Error)
### Nguyên nhân Root Cause
- Trong `python_runner/flows/feed_swipe_smoke.py` và `run_tiktok.py`:
  - `SESSION_MAX_SWIPES_CAP = 15`
  - Guard check: `if not 1 <= int(args.max_swipes) <= 15: return CONFIG_ERROR`
- Khi worker khác commit nâng `FEED_SESSION_MAX_SWIPES = 16` trong `multi_machine_feed_session.py`:
  - Mọi sub-batch dispatch đều truyền `--max-swipes 16` vào child runner.
  - Kết quả: **Toàn bộ máy trong đợt bị dừng ngay lập tức ở trạng thái `config-error`** trước khi chạm vào thiết bị.
  - Do lỗi xảy ra ở tầng config validation, script không kích hoạt `send_farm_machine_alert` trên thiết bị $\rightarrow$ Không có ảnh banner đỏ gửi Farm Alerts.

### Quy chuẩn bắt buộc
- Hằng số `FEED_SESSION_MAX_SWIPES` trong `multi_machine_feed_session.py` bắt buộc phải đặt là **15** (khớp chính xác với trần validation `SESSION_MAX_SWIPES_CAP`).
- Bất kỳ thay đổi hằng số swipe targets nào cũng phải đối soát giữa `multi_machine_feed_session.py`, `run_tiktok.py`, và `feed_swipe_smoke.py`.

---

## 3. Fast Swipe vs Tổng Lượt Vuốt (Total Swipes Completed)
- Các lượt vuốt nhanh (Fast Swipe xem 2-5s, quẹt trực tiếp không dump XML) vẫn tăng `swipe_count` trong vòng lặp chính `for swipe_count in range(1, selected_total_videos + 1)`.
- Khi tổng kết phiên, `aggregate_feed_swipe_results()` lấy `max(swipe_count)` từ bảng kết quả $\rightarrow$ **Các lượt vuốt nhanh được tính đầy đủ 100% vào `total_swipes_completed`**.

---

## 4. Upload Hook Config Requirement (`Tiktok-video`)
- Khi kết thúc Phiên 3/3 (phiên cuối của ca), `_run_upload_hook` tự động đọc đúng workbook Tik theo Row (`Row 1 -> Tik1.xlsx`, `Row 2 -> Tik2.xlsx`...).
- Subprocess gọi `scripts.tiktok_workflow` bắt buộc yêu cầu tham số `--config <file.yaml>`.
- Thư mục `D:\Taadaa\Tiktok-video` bắt buộc phải có sẵn file `config.example.yaml` làm fallback, nếu thiếu sẽ gây lỗi `upload_subprocess_nonzero: Config file not found`.
- Kiểm tra `require_android_vpn(required=True)` fail-closed trước khi upload video để đảm bảo máy có VPN hợp lệ.
