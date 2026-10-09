# Kiến trúc 4 Ca × 2 Phiên & Vận hành Farm An toàn (Chốt 2026-09-11)

## 1. Cấm tuyệt đối tái diễn Cohort/Manifest/Picker (Frustration Signal)
- Runner chuẩn là **O(1) thuần túy**: `tiktok_runner.py` đọc giờ → xác định Row (theo ngày chẵn/lẻ) → spawn trực tiếp `run-feed-session.ps1` với `taikhoan_run_safe.xlsx`.
- **CẤM TUYỆT ĐỐI** gắn lại `picker`, `cohort`, `assignment-manifest` hay các cơ chế dispatch nhiều tầng phức tạp vào `tiktok_runner.py` hoặc PS1.
- `_session_index` (1 hoặc 2) chỉ đóng vai trò identity nội bộ nhẹ để gate upload hook (`upload_eligible = session_index == 2`), hoàn toàn không phụ thuộc cohort.

## 2. Lịch trình chuẩn: 4 Ca × 2 Phiên (8 Slot/ngày)
| Ca | Phiên 1 | Phiên 2 (kèm Upload video) | Khoảng nghỉ chuyển Ca (Gap B) |
|---|---|---|---|
| **Ca 1 (Sáng)** | **06:00** – 06:45 | **08:00** – 08:50 | 08:50 – 12:00 (nghỉ ~3h10) |
| **Ca 2 (Trưa)** | **12:00** – 12:45 | **14:00** – 14:50 | 14:50 – 18:00 (nghỉ ~3h10) |
| **Ca 3 (Tối)**  | **18:00** – 18:45 | **20:00** – 20:50 | 20:50 – 00:00 (nghỉ ~3h10) |
| **Ca 4 (Đêm)**  | **00:00** – 00:45 | **01:30** – 02:20 | 02:20 – 06:00 (nghỉ ~3h40; dọn cache 04:00) |

- **Chỉ tiêu Follow:** 15–18 lượt/phiên (giãn cách 60–150s có jitter) → Đạt 30–36 follow/ngày/nick sạch, an toàn, không bị nhả follow (ghost/shadow unfollow).
- **Upload video:** Đăng ở **Phiên 2** (sau khi nick đã warm-up tương tác ở Phiên 1).
- **Dead-zone:** Khoảng từ 02:30 đến 05:59 sáng và các kẽ giờ giữa 2 phiên (ví dụ 07:00, 09:00...) không spawn lại.
- **Watchdog:** Khai báo 8 window `SESSION_WINDOWS` tương ứng; `session_key` bắt buộc có dạng `{date}_ca{ca}_phien{phien}` để phân tách rành mạch 2 phiên trong cùng 1 ca.

## 3. Nguyên tắc Gap & Chuyển đổi tài khoản (Account Switch)
- **Gap A (trong Ca) < Gap B (chuyển Ca):**
  - **Gap A (cùng nick):** ~75–90 phút (ca đêm ~45 phút). Đủ thời gian cho SoC máy Samsung nguội về nhiệt nền; mô phỏng tự nhiên thói quen người dùng thật mở app 2 lần trong 1 buổi sinh hoạt.
  - **Gap B (đổi nick):** ~150–180 phút (>3 tiếng). Bắt buộc phải dài để xóa mờ dấu chân thiết bị (device fingerprint) và tránh nguy cơ bị TikTok liên đới tài khoản (**Co-location / Account Linking**) khi 2 nick khác nhau chạy trên cùng một máy.
- **Switch account ở đầu Ca tiếp theo:**
  - **TUYỆT ĐỐI KHÔNG switch nick sớm ở cuối Ca trước** rồi để app/session treo idle nhiều giờ.
  - Switch/mở nick đúng vào thời điểm bắt đầu Ca tiếp theo (kèm warm-up 30–90s + health-check đúng @handle).
  - *Lưu ý về IP trên farm:* Dàn farm dùng IP proxy/VPN cố định (chỉ thỉnh thoảng ISP tự xoay). Việc switch đúng đầu ca đảm bảo session không bị treo qua các thời điểm mạng chập chờn hay đứt kết nối.
