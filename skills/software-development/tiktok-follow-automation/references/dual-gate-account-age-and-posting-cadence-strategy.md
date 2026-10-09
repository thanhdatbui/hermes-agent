# Dual Gate Follow Strategy & Posting Cadence (Taadaa Phone Farm)

Tài liệu chuẩn hóa chiến lược tần suất đăng video và điều kiện mở khóa Follow (Dual Gate) được đồng thuận bởi Sol High & Claude CLI (2026-09-24).

---

## 1. Bối cảnh thực tế Farm Taadaa
- **Nhịp đăng thực tế:** Do cơ chế quay vòng 8 slot/máy và phiên dưỡng sinh (1/3: 0 follow/up), nhịp đăng trung bình của farm là **2.3 – 3 ngày / 1 video / nick** (2 ngày nếu không dưỡng sinh, 3 ngày nếu có dưỡng sinh).
- **Cạm bẫy nhận thức:** CẤM áp dụng benchmark của creator thông thường (1-2 video/ngày) vào Farm Taadaa.
- **Mục đích gốc của Gate 10 video:** Với nhịp 2.3 - 3.5 ngày/video, 10 video thực chất tương đương với **35 – 40 ngày ngâm nick** và xây dựng trust score content trước khi cho đi follow.

---

## 2. Chiến lược Tần Suất Đăng Video (Posting Cadence)

### A. Nick đang cắn đề xuất (Viral / Trending / High View Velocity)
- **Hành động:** **Bỏ ngày dưỡng sinh $\to$ Khóa nhịp cố định 48h (2 ngày / 1 video).**
- **Quy tắc bất biến:** **TUYỆT ĐỐI KHÔNG TĂNG LÊN 1 VIDEO/NGÀY.**
  - *Cannibalization:* Thuật toán TikTok phân phối video theo từng làn sóng (wave). Đăng quá dồn dập sẽ khiến video mới cướp impression của video cũ đang bay.
  * *Farm Behavioral Anomaly:* Đột ngột tăng vọt tần suất đăng trên IP proxy phone farm sẽ kích hoạt cờ kiểm duyệt bot spam.
  - *Đặc biệt:* Nếu video đang viral cực mạnh (>10x median view), có thể giãn thêm 12-24h (tổng 60-72h) để vét hết long-tail distribution.

### B. Nick bình thường / Flop
- **Hành động:** Giữ nguyên nhịp cũ **2.3 – 3 ngày / 1 video** (xen kẽ dưỡng sinh 0 up/follow).
- Giảm tải cho farm, tiết kiệm tài nguyên render và tránh spam tài khoản kém chất lượng.

---

## 3. Chiến lược Follow Gate (Dual Gate / Hybrid Gate)

### A. Tại sao bỏ Gate 10 video cứng?
- Chờ đủ 10 video khiến nick bị "chết vốn" ngâm máy và proxy suốt 35-40 ngày mà không tạo ra network graph.
- Hệ thống Taadaa đã có sẵn **Watchdog đối soát 2 tầng** bắt nhả follow (Case UI-75) và cơ chế phạt cooldown `fail_streak`, nên rủi ro follow sớm đã có lưới an toàn kiểm soát.

### B. Tại sao không dùng Ngày tuổi thuần túy?
- Một nick 21 ngày tuổi nhưng chỉ có 0-2 video khi đi follow vẫn bị thuật toán TikTok nhận diện là tài khoản rác/bot spam follow chéo.

### C. Công thức chuẩn Dual Gate (Consensus Sol High & Claude)
$$\text{Được phép Follow} \iff (\text{Ngày tuổi} \ge 21\text{ ngày}) \;\mathbf{VÀ}\; (\text{Video Đã Đăng} \ge 6\text{ video})$$

*Ở nhịp 2.3 - 3 ngày/video, khi nick chạm mốc 21 ngày tuổi sẽ tự nhiên tích lũy được 6-7 video, tạo điểm hội tụ lý tưởng.*

### D. Phân tầng Budget Follow
1. **Giai đoạn Sandbox / Khóa hoàn toàn** ($< 21$ ngày HOẶC $< 6$ video):
   - `Budget = 0` (Chỉ lướt feed + like, tuyệt đối không follow).
2. **Giai đoạn Mồi nhẹ (Soft Follow)** ($21 - 30$ ngày tuổi VÀ $\ge 6$ video):
   - `Budget = 3 - 5 follow/phiên` (tương đương 5 - 10 follow/ngày).
   - Nếu Watchdog phát hiện Optimistic UI follow drop $\to$ kick cooldown ngay lập tức.
3. **Giai đoạn Trưởng thành (Full Scale)** ($> 30$ ngày tuổi VÀ $\ge 10$ video):
   - `Full Budget = 6 - 10 follow/phiên` (tối đa 20-30 follow/ngày).

---

## 4. Yêu cầu Hạ Tầng & Dữ Liệu
- File `taikhoan_run_safe.xlsx` hiện chỉ có 4 cột: `May`, `Device ID`, `ID`, `Video Đã Đăng`.
- Để áp dụng Dual Gate, pipeline build safe workbook cần đồng bộ thêm cột `NGÀY TẠO` từ master sheet `taikhoan_dat_v2_updated .xlsx` sang `taikhoan_run_safe.xlsx` (hoặc tính sẵn cột `Tuoi_Nick_Ngay`).
