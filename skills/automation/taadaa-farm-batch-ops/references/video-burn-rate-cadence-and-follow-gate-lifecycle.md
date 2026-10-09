# Quy Chuẩn Nhịp Đăng Video, Vòng Đời Cạn Kho & Cơ Chế Mở Van Follow (6-Video Gate)

> 📌 **Tóm tắt cốt lõi**:
> - Nhịp đăng thực tế toàn farm: **3.31 ngày / 1 video / nick** (~0.30 video/ngày, tức 9–10 video/tháng).
> - Kho video 40–45 clip dùng được **4.5 – 5.0 tháng** mới cạn.
> - **Cạn kho không phải là hết**: CẤM reset `Video Đã Đăng` về 0. Nạp gối đầu bằng cách render từ `N+1` (`--start-seq N+1`).
> - **Nguyên nhân follow chững ở ~250**: Rào chắn an toàn `video_count >= 6` đang khóa 73.6% số nick toàn farm chưa cho đi follow chéo. Khi các dàn sau vượt 6 video, lực lượng follow sẽ tăng gấp đôi lên 640–1252 nick để đẩy cán mốc 1.000 follow.

---

## 1. Thông Số Nhịp Đăng Video Thực Tế Toàn Farm (Cadence Ground Truth)

Dựa trên dữ liệu kiểm đếm từ sổ cái `shift_upload_history.json` (hơn 3.900 lượt đăng thành công) và scheduler `tiktok_runner.py`:

1. **Lịch xoay tua ngày Chẵn / Lẻ (Row Parity)**:
   - Ngày **Lẻ**: Chạy Row Lẻ (**Row 1, 3, 5, 7**).
   - Ngày **Chẵn**: Chạy Row Chẵn (**Row 2, 4, 6, 8**).
   - 👉 Mỗi nick chỉ được lên lịch chạy **1 lần mỗi 2 ngày** (cách 1 ngày nghỉ 1 ngày).

2. **Khóa cứng số lượng theo Ca (Strictly 1 Upload / Shift)**:
   - Mỗi ca gồm 2 phiên (P1 & P2).
   - Cơ chế sổ cái `_ShiftUploadLedger` khóa nguyên tử: Nếu nick đã đăng thành công ở P1 thì sang P2 tự động skip với lý do `already_uploaded_in_shift`.
   - Mỗi ngày nick chạy tối đa đúng **1 video**.

3. **Bộ lọc Ngày nghỉ dưỡng sinh (Organic Rest Day Gate)**:
   - Thuật toán băm MD5 kiểm tra ngẫu nhiên: `(int(hashlib.md5(f"{date_str}:{machine}:{row}").hexdigest()[:8], 16) % 3) == 0`.
   - Tỷ lệ **1/3 số ngày chạy là ngày nghỉ dưỡng sinh**.
   - Vào ngày này, nick chỉ lướt feed ngắm tương tác, **0 Follow, 0 Upload** để tránh bị TikTok quét spam do nhịp đăng quá dày.

4. **Phân bố khoảng cách thực tế giữa 2 lần đăng liên tiếp của 1 nick**:
   - **Cách 2 ngày**: Chiếm **53.4%** (lần chạy kế tiếp đăng thành công).
   - **Cách 4 ngày**: Chiếm **27.4%** (lần chạy kế tiếp dính 1 ngày nghỉ dưỡng sinh).
   - **Cách 6 ngày**: Chiếm **8.5%** (dính 2 nhịp nghỉ / skip liên tiếp).
   - **Tốc độ trung bình toàn farm**: **3.31 ngày / 1 video / nick** (~ **0.30 video/ngày/nick**).

---

## 2. Vòng Đời Cạn Kho Video & Quy Trình Nạp Gối Đầu (Replenishment)

### A. Thời gian cạn kho của 1 nick
- **Kho mới tinh (40–45 clip)**:
  - Với nhịp 3.31 ngày/clip: Tốn **132 – 149 ngày** (~ **4.4 đến 5.0 tháng**).
  - Với kịch bản nhanh nhất (2 ngày/clip, bypass nghỉ dưỡng sinh): Tốn **80 – 90 ngày** (~ **2.7 đến 3.0 tháng**).
- **Hiện trạng tồn kho theo từng dàn Tik (đến 10/2026)**:
  - **Tik 1 (chạy sớm nhất)**: Đã đăng TB 23.0 clip ➔ Còn TB 22.5 clip (min 13, max 40). Top nick nhanh nhất còn 13 clip ➔ Còn ~43 ngày (~1.5 tháng).
  - **Tik 2**: Đã đăng TB 11.7 clip ➔ Còn TB 33.6 clip ➔ Còn ~3.7 tháng.
  - **Tik 3**: Đã đăng TB 9.8 clip ➔ Còn TB 35.7 clip ➔ Còn ~3.9 tháng.
  - **Tik 4**: Đã đăng TB 8.1 clip ➔ Còn TB 38.0 clip ➔ Còn ~4.2 tháng.
  - **Tik 5 – Tik 8**: Đã đăng TB 3–4 clip ➔ Còn TB 40–42 clip ➔ Còn ~4.5 tháng.
  - **Dàn Admin (Tik 1..Tik 8)**: Mới đăng 0–1 clip ➔ Còn nguyên 100% kho (~4.5 tháng).

### B. Quy tắc nạp gối đầu khi sắp cạn kho (Không bao giờ để nick dừng nuôi)
- **Cột mốc cảnh báo**: Khi nick chạm mốc **35 video đã đăng** (kho còn 8–10 clip).
- **Quy chuẩn thực thi**:
  1. **Bảng tính Excel (Tik*.xlsx)**: **CẤM TUYỆT ĐỐI** reset cột `Video Đã Đăng` về 0. Giữ nguyên mốc $N$.
  2. **Tải & Render nguồn mới**:
     - Cào thêm 35–40 video từ Douyin thuần BGM hoặc kênh TikTok gái xinh mới vào `D:\video goc\<folder>`.
     - Kích hoạt render với cờ `--start-seq <N+1>` (ví dụ: `--start-seq 41` hoặc `--start-seq 46`).
     - File render mới xuất ra thư mục `D:\TIKTOK-videonuoinick\<folder>` bắt đầu từ `41.mp4`, `42.mp4`...
  3. **Kết quả**: Bot upload tiếp tục đọc `Video Đã Đăng = N` và bốc tiếp clip $N+1$ mới tinh, dòng chảy nuôi nick không bị đứt đoạn.

---

## 3. Rào Chắn 6-Video Gate & Cơ Chế Mở Van Bùng Nổ Follow

### A. Tại sao follow hiện tại chững ở mức ~250 follow?
1. **Rào chắn 6-Video Gate (`video_count >= 6`)**:
   - Để bảo vệ nick khỏi bị nhả follow do chưa đủ Trust, core quy định: **Nick < 6 video CẤM TUYỆT ĐỐI đi follow** (`under-6-videos-follow-disabled`).
   - Ground truth toàn farm (1.252 nick trong `taikhoan_run_safe_combined.xlsx`):
     - **Nick đủ điều kiện (≥ 6 video)**: Chỉ có **330 nick (26.4%)** — chủ yếu thuộc Tik 1, Tik 2, Tik 3 và một phần Tik 4.
     - **Nick bị khóa đi follow (< 6 video)**: Chiếm **922 nick (73.6%)** — gồm toàn bộ Tik 5, 6, 7, 8 và dàn Admin.
   - 👉 **Hệ quả**: Hiện tại mới chỉ có ~1/4 số nick trong farm tham gia "cày follow chéo" cho người khác. Khi chỉ có ~250 nick đi follow thì nick nhận cũng chỉ tối đa chạm trần 200–250 follow!

### B. Lộ trình mở van follow đạt 1.000 follow
1. **Giai đoạn 1 (1–2 tuần tới)**: Tik 5, 6, 7, 8 hiện đã có 3–4 video, sắp chạm mốc 6 video. Khi đó toàn bộ 640 nick trên host Kibe sẽ đồng loạt đi follow chéo, lượng follow dội ngược lại sẽ tăng gấp đôi (đẩy dàn đầu lên 500–600 follow).
2. **Giai đoạn 2 (Dàn Admin tham gia)**: Dàn Admin 80 máy (640 nick) khi qua mốc 6 video sẽ nâng tổng số thợ follow lên 1.252 nick. Bản thân mạng lưới follow nội bộ 1.252 nick đã thừa sức đẩy từng nick chạm và vượt ngưỡng 1.000 follow.
3. **Giai đoạn 3 (Organic FYP từ Video Gái Xinh BGM)**: Nội dung thuần nhạc nền (Dance, OOTD, biến hình) có tỷ lệ xem lặp lại (Loop Rate) cao, giúp nick cắn đề xuất tự nhiên (điển hình như nick `@tuantuannguyen56` chỉ 5 video đã kéo 244 follow và 4.903 tim tự nhiên). Luồng follow organic sẽ bù đắp mạnh mẽ song song với follow chéo nội bộ.
