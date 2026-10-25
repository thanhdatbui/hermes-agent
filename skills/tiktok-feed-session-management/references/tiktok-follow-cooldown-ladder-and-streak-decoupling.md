# TikTok Follow Cooldown Ladder & Streak Decoupling Specification

## 1. Bản Chất Phân Định Giữa Hai Hệ Thống (Decoupling)

Hệ thống theo dõi follow TikTok (`tiktok-follow` và `tiktok-luot nuoi acc`) bắt buộc phải bóc tách hoàn toàn 2 cơ chế độc lập:

### A. Hệ thống `fail_streak` (Chuỗi thất bại liên tiếp)
- **Mục đích:** Đo lường xem tài khoản có đang bị server TikTok áp đặt lệnh chặn cứng tương tác hay không.
- **Quy tắc vàng:**
  1. **Reset ngay khi có thành công:** Trong hàm `mark(uid, STATUS_FOLLOWED)`, hễ tài khoản follow thành công $\ge 1$ người $\rightarrow$ `self._data["fail_streak"] = 0` ngay lập tức! Bẻ gãy hoàn toàn chuỗi thất bại cũ.
  2. **Chạm trần phiên (`used >= 1` rồi mới bị nhả):** Coi là hoàn thành phiên chạm trần, ghi nhận **`Streak 1` (nhả lần đầu)**, cooldown đúng **24 giờ**. Tuyệt đối **CẤM** leo thang lên Streak 2, 3, 4.
  3. **Tái phạm 0 follow (`used == 0`):** Chỉ khi tài khoản vừa vào phiên đã bị nhả ngay từ lượt đầu tiên (`used == 0`) thì mới tính là lỗi phiên và leo thang streak nếu cữ trước cũng fail liên tiếp.

### B. Hệ thống Quota Dưỡng Nick (Probation / Graduation Ladder)
- **Mục đích:** Điều tiết van tải (số lượt follow/phiên) để nick không bị sốc lưu lượng sau khi hết hạn cách ly.
- **Quy tắc độc lập:**
  - Điều khiển độc quyền qua `probation_clean_days` và `graduated`, **KHÔNG** phụ thuộc vào `fail_streak`.
  - **Hồi phục 1:** Cấp quota 2–4 lượt.
  - **Hồi phục 2:** Cấp quota 4–6 lượt.
  - **Khỏe (Graduated):** Cấp quota full 10–15 lượt.
  - Khi nick mãn hạn cách ly ra chạy, dù `fail_streak` đã về 0 sau lượt follow đầu tiên, thuộc tính `is_post_cooldown_warmup` vẫn giữ nick chạy đúng quota dưỡng an toàn trong ngày và ngày hôm sau cho đến khi tốt nghiệp.

---

## 2. Thang Phạt Cooldown Chuẩn Toàn Farm

| Cấp độ | Định nghĩa | Thời hạn Cooldown | Hành vi sau khi hết hạn |
| :--- | :--- | :---: | :--- |
| **`Streak 1`** | Bị nhả lần đầu (hoặc chạm trần `used >= 1`) | **24 giờ (1 ngày)** | Tự động mở follow, vào diện Hồi phục 1 |
| **`Streak 2`** | Nhả 2 cữ liên tiếp (`used == 0`) | **3 ngày** | Tự động mở follow, vào diện Hồi phục 1 |
| **`Streak 3`** | Nhả 3 cữ liên tiếp (`used == 0`) | **5 ngày** | Tự động mở follow, vào diện Hồi phục 1 |
| **`Streak >= 4`** | Tái phạm nặng $\ge 4$ cữ liên tiếp (`used == 0`) | **15 ngày** | Tự động mở follow, vào diện Hồi phục 1 |

---

## 3. Kỷ Luật Điều Phối Worker Trong Sửa Chữa Mã Nguồn

1. **Sàn Timeout Worker (Worker Floor 300s):**
   - Khi gọi các tool runner / worker (`dispatch_worker.py`, `sol_worker.py`), Coordinator tuyệt đối **CẤM** tự ý truyền timeout ngắn (như `--timeout 30`) trong foreground terminal làm ngắt ngang tiến trình stream của model.
2. **Kỷ Luật On-Demand Đối Với Claude / Advisor:**
   - Claude Worker và Advisor là **100% On-Demand**. Tuyệt đối **CẤM** Coordinator theo quán tính buột miệng đòi gọi Claude Worker khi User chưa yêu cầu đích danh.
   - Ưu tiên hàng đầu cho sửa chữa O(1) là **Sol Web Worker (`sol_worker.py` qua `:20129`)** hoặc sửa trực tiếp trong ngân sách Emergency Surgery L2.
