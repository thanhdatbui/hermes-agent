# Kiến Trúc 4 Ca x 2 Phiên & Quy Tắc Vận Hành TikTok Farm (Cập nhật 2026-09-11)

## 1. Cấu Trúc Lịch Trình (4 Ca x 2 Phiên / Ngày)
Hệ thống nuôi acc TikTok tự động chạy **4 Ca/ngày**, mỗi Ca gồm **2 Phiên**. 
Toàn bộ runner chạy theo mô hình **O(1) thuần túy**: `tiktok_runner.py` đọc giờ hệ thống -> xác định Row (theo ngày chẵn/lẻ) -> gọi trực tiếp `run-feed-session.ps1`.
**CẤM TUYỆT ĐỐI** gắn lại hệ thống picker, cohort, manifest trung gian.

### Timeline 8 slot chuẩn:
| Ca | Phiên | Giờ chạy | Row (Ngày Lẻ) | Row (Ngày Chẵn) | Nội dung phiên |
|---|---|---|---|---|---|
| **Ca 1 (Sáng)** | Phiên 1 | **06:00** | Row 1 | Row 2 | Lướt Feed (8-11 video) + Follow đợt 1 (15-18 lượt) |
| | Phiên 2 | **08:00** | Row 1 | Row 2 | Lướt Feed + Follow đợt 2 + ĐĂNG VIDEO (Upload Hook) |
| **Ca 2 (Trưa)** | Phiên 1 | **12:00** | Row 3 | Row 4 | Lướt Feed (8-11 video) + Follow đợt 1 (15-18 lượt) |
| | Phiên 2 | **14:00** | Row 3 | Row 4 | Lướt Feed + Follow đợt 2 + ĐĂNG VIDEO (Upload Hook) |
| **Ca 3 (Tối)** | Phiên 1 | **18:00** | Row 5 | Row 6 | Lướt Feed (8-11 video) + Follow đợt 1 (15-18 lượt) |
| | Phiên 2 | **20:00** | Row 5 | Row 6 | Lướt Feed + Follow đợt 2 + ĐĂNG VIDEO (Upload Hook) |
| **Ca 4 (Đêm)** | Phiên 1 | **00:00** | Row 7 | Row 8 | Lướt Feed (8-11 video) + Follow đợt 1 (15-18 lượt) |
| | Phiên 2 | **01:30** | Row 7 | Row 8 | Lướt Feed + Follow đợt 2 + ĐĂNG VIDEO (Upload Hook) |

- **Dead zone:** Từ sau `02:30` đến trước `06:00` sáng (nhường thời gian cho dọn cache toàn farm lúc 04:00, backup và làm nguội dàn máy).

---

## 2. Quy Tắc Vận Hành Cốt Lõi (Invariants)

### 2.1. Gap A (trong Ca) BẮT BUỘC NGẮN HƠN Gap B (chuyển giao Ca)
- **Gap A (Nghỉ giữa 2 phiên trong 1 ca):** ~60 - 80 phút.
  - Phù hợp với hành vi người dùng thật mở app 2 lần trong 1 buổi sinh hoạt.
  - Đủ thời gian cho SoC điện thoại Samsung hạ nhiệt nền sau phiên 1.
- **Gap B (Nghỉ giữa 2 ca khác nhau):** ~3 giờ - 3.5 giờ.
  - **Chống Co-location / Account Linking:** Tránh trường hợp vừa tắt Nick A thì Nick B lập tức vào chạy trên cùng 1 máy và cùng dải IP. Khoảng cách >3 tiếng giúp tách biệt dấu chân thiết bị giữa các tài khoản khác nhau trên cùng máy.
  - Cho phép máy sạc bù pin, tản nhiệt sâu và phục hồi tài nguyên ADB server.

### 2.2. Tuyệt đối KHÔNG chuyển tài khoản trước (Switch Account Boundary)
- **Quy tắc:** BẮT BUỘC chỉ chuyển tài khoản (switch account / login) vào **ĐẦU CA MỚI**, tuyệt đối không switch trước ở cuối ca cũ rồi để idle hàng giờ.
- **Lý do rủi ro IP/VPN:** Nếu login trước từ cuối ca trước, trong 3 tiếng idle nếu proxy/VPN xoay IP thì session sẽ hoạt động trên IP khác với lúc login -> TikTok đánh cờ **Session Hijack** (cướp phiên) -> checkpoint / văng acc / shadowban.
- **Trình tự bất biến tại boundary đổi ca:**
  `Rotate IP / Kiểm tra VPN` -> `Mở / Switch đúng Nick` -> `Warm-up 30s` -> `Bắt đầu Phiên 1`.

### 2.3. Jitter Khởi Động & Randomize Máy
- **Jitter máy:** Bắt buộc duy trì `-RandomizeMachineOrder` (xáo trộn thứ tự máy ngẫu nhiên) và `-MachineStartStaggerMs "2000,8000"` (mỗi máy cách nhau 2-8s) trong lệnh gọi `run-feed-session.ps1` để 80 máy không bao giờ vào app đồng loạt cùng 1 giây.
- **Jitter giờ ca:** Cron `phase9-runner-tiktok-feed` chạy chu kỳ 15 phút (`*/15 * * * *`). Runner tự động đối soát `window_key` (ví dụ `2026-09-11T06`, `2026-09-11T08`, `2026-09-11T0130`) qua `runner_simple_state.json` để chỉ chạy đúng 1 lần duy nhất cho mỗi window.
