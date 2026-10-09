# Chiến Lược Chuyển Đổi Niche Khi Hết Kho Video, Xử Lý Video Cũ (Ẩn vs Giữ Public) & Tốc Độ Cạn Kho (Cadence Depletion)

> 📌 **Bối cảnh & Vấn đề thực tế Farm (2026-10-01)**:
> - Mỗi folder hiện tại được nạp đợt đầu 40–45 video. Chủ farm băn khoăn: Một nick tốn bao lâu thì cạn kho? Tốc độ lên follow hiện tại mới chạm trần ~250 follow, liệu có bị hết video trước khi đủ 1.000 follow?
> - Khi đăng hết 40–45 video của chủ đề cũ (thú cưng, đời sống...) chuyển sang chủ đề mới (gái xinh dance/OOTD thuần nhạc nền) thì có bắt buộc phải ẩn video cũ không? Thuật toán TikTok phản ứng thế nào?

---

## 1. Tốc Độ Cạn Kho Thực Tế & Nhịp Đăng Toàn Farm (Cadence Depletion Rate)

### Cơ Chế Điều Phối Nhịp Đăng
1. **Lịch xoay tua ngày Chẵn / Lẻ**:
   - Ngày Lẻ: Chạy Row Lẻ (Row 1, 3, 5, 7).
   - Ngày Chẵn: Chạy Row Chẵn (Row 2, 4, 6, 8).
   - *Hệ quả*: Mỗi nick chỉ được lên lịch chạy 1 lần mỗi 2 ngày (cách 1 ngày nghỉ 1 ngày).
2. **Khóa cứng số lượng theo Ca (`_ShiftUploadLedger`)**:
   - Mỗi ca chạy 2 phiên (P1 & P2), cơ chế sổ cái atomic chỉ cho phép đăng tối đa **1 video / ca / nick** (đã đăng ở P1 thì P2 tự động skip `already_uploaded_in_shift`).
3. **Bộ lọc ngày nghỉ dưỡng sinh (`_is_account_organic_rest_day`)**:
   - Thuật toán băm MD5 kiểm tra ngẫu nhiên: xác suất **1/3 số ngày chạy là ngày nghỉ dưỡng sinh**.
   - Vào ngày này, nick chỉ lướt feed ấm tài khoản, **0 Follow, 0 Upload** để tránh bị TikTok quét spam vì nhịp đăng quá dày.

### Thống Kê Ground-Truth (3.905 Lượt Đăng Thành Công Trong Sổ Cái)
- Khoảng cách giữa 2 lần upload liên tiếp của 1 nick:
  - **Cách 2 ngày**: Chiếm **53.4%** (lượt chạy kế tiếp đăng thành công).
  - **Cách 4 ngày**: Chiếm **27.4%** (lượt chạy kế tiếp dính ngày nghỉ dưỡng sinh).
  - **Cách 6 ngày**: Chiếm **8.5%** (dính 2 nhịp nghỉ / skip liên tiếp).
- 👉 **Trung bình thực tế toàn Farm**: **3.31 ngày / 1 video / nick** (~ **0.30 video/ngày**, tương đương **9 – 10 video/tháng/nick**).

### Thời Gian Cạn Kho Video
- **Kho mới tinh (40 – 45 video)**: Tốn **132 – 149 ngày (~4.5 – 5 tháng)** mới cạn.
- **Tính từ thời điểm hiện tại**:
  - Dàn Tik 1 (đã đăng TB 23.0 clip, còn TB 22.5 clip): Còn khoảng **74 ngày (~2.5 tháng)**.
  - Các nick sắp hết nhất (Máy 21 còn 13 clip, Máy 38 còn 13 clip): Còn khoảng **43 ngày (~1.4 tháng / 6 tuần)**.
  - Dàn Tik 2 (còn TB 33.6 clip): Còn khoảng **111 ngày (~3.7 tháng)**.
  - Dàn Tik 3 – Tik 4 (còn TB 36 – 38 clip): Còn khoảng **120 ngày (~4.0 tháng)**.
  - Dàn Tik 5 – Tik 8 (còn TB 39 – 42 clip): Còn khoảng **130 – 140 ngày (~4.5 tháng)**.

---

## 2. Giải Mã Hiện Tượng Follow Lên Chậm (~250 Follow) Giai Đoạn Đầu

### Nguyên Nhân: Rào Chắn An Toàn Farm 6 Video Gate (`video_count >= 6`)
- Theo quy chuẩn an toàn chống nhả follow: Nick mới dưới 6 video **tuyệt đối bị cấm đi follow** (`under-6-videos-follow-disabled`) vì nick chưa đủ Trust đi follow sẽ bị TikTok nhả follow hoặc gắn cờ.
- **Thống kê thực tế trên 1.252 nick toàn farm**:
  - **Đủ điều kiện đi follow (≥ 6 video)**: Chỉ có **330 nick (26.4%)** — chủ yếu là Row 1, Row 2, Row 3 và một phần Row 4.
  - **Bị khóa đi follow (< 6 video)**: Có tới **922 nick (73.6%)** — gồm toàn bộ Row 5, 6, 7, 8 (mới đăng 2–4 video) và dàn Admin (mới 0–1 video).
- 👉 **Kết luận**: Hiện tại mới chỉ có ~1/4 số nick trong farm tham gia "cày follow chéo". Khi chỉ có ~250 nick đi follow thì nick nhận tối đa cũng chỉ đạt tầm 200–250 follow là chạm trần nhóm 1.

### Cơ Chế Bùng Nổ Follow Sau 2 Tuần
- **Đòn bẩy 1**: Trong 1.5 – 2 tuần tới, khi toàn bộ 320 nick Dàn Tik 5 – Tik 8 cán mốc ≥ 6 video, lực lượng đi follow chéo tăng gấp đôi (lên 640 nick) $\rightarrow$ follow nhận được sẽ nhảy vọt lên 500–600.
- **Đòn bẩy 2**: Dàn Admin 80 máy (640 nick) tham gia sau khi nạp video sẽ đưa tổng lực lượng lên 1.252 nick $\rightarrow$ thừa sức đẩy từng nick cán mốc 1.000 follow.

---

## 3. Thuật Toán TikTok Khi Đổi Chủ Đề: Có Cần Ẩn Video Cũ?

### Trọng Số Item-Level vs Account-Level Trong Recommendation System
- Thuật toán phân phối hiện đại của TikTok (Two-Tower DNN / Monolith) ưu tiên cực mạnh **Item-Level Features** (âm thanh thịnh hành, visual embedding, hook 2–3 giây đầu, tương tác của nhóm người xem đầu tiên).
- Quá khứ 40 clip của Niche A **KHÔNG trói chân vĩnh viễn** tài khoản. Hệ thống liên tục cập nhật và chỉ mất **3–5 video mới** để hoàn tất re-clustering (định vị lại tệp người xem phù hợp cho Niche B).

### Đánh Giá 3 Lựa Chọn Xử Lý Video Cũ

| Phương án | Tác động thuật toán | Điểm Trust & Rủi ro | Đánh giá thực chiến Farm |
| :--- | :--- | :--- | :--- |
| **1. XÓA (Delete)** | Mất sạch retention graph, comment, social proof đã tích lũy. | **RỦI RO CAO NHẤT**: Xóa hàng loạt kích hoạt Anomaly Detection $\rightarrow$ dễ dính Shadowban / 0 view. | **CẤM TUYỆT ĐỐI**. Lựa chọn tệ nhất. |
| **2. ẨN (Private / Chỉ mình tôi)** | Mất traffic organic thụ động từ các video cũ có view. | An toàn, không bị phạt. Profile nhìn thuần 1 chủ đề sạch sẽ. | Không cần thiết trong lúc đang nuôi kéo follow. |
| **3. ĐỂ NGUYÊN (Public)** | Giữ nguyên 100% view, like, comment tích lũy. Video cũ tiếp tục kéo traffic thụ động. | **AN TOÀN TUYỆT ĐỐI**: Kênh có lịch sử dày dặn, giống nick người thật đã hoạt động lâu. | **LỰA CHỌN TỐI ƯU NHẤT CHO FARM SLL**. |

---

## 4. Quy Trình Vận Hành Chuẩn 2 Giai Đoạn (2-Phase Playbook)

### Giai Đoạn 1: Nuôi Kéo Đủ 1.000 Follow (Giai đoạn hiện tại)
1. **Cứ để nguyên 40–45 video cũ công khai**. Tuyệt đối không bấm xóa, không mất công vào từng nick ẩn sang Private.
2. **Nạp gối đầu Đợt 2 (Batch 2)**:
   - Khi nick chạm mốc 35–40 clip đã đăng (kho còn 5–10 clip): Cào tiếp 40 clip mới.
   - Chạy render với cờ `--start-seq <N+1>` (ví dụ: `--start-seq 46` để xuất ra `46.mp4`, `47.mp4`...).
   - Tuyệt đối giữ nguyên cột `Video Đã Đăng` trong Excel (không reset về 0).
   - Bot upload tự động bốc tiếp clip $N+1$ đăng mượt mà, không gián đoạn.
3. **Phân loại nguồn nạp gối đầu**:
   - Kênh có chủ đề cũ sạch & có tương tác (thú cưng, đời sống): Nạp tiếp đúng chủ đề đó để giữ audience graph.
   - Kênh chủ đề cũ flop / kém tương tác: Nạp đè Gái xinh dance / OOTD thuần nhạc nền để kích hoạt tệp người xem visual rộng hơn.

### Giai Đoạn 2: Sau Khi Đã Đủ 1.000 Follow (Bàn giao / Bán nick)
- Khi nick đã hoàn thành mục tiêu 1.000 Follow và chuẩn bị đem bán cho khách hoặc mở TikTok Shop / Affiliate:
  - Lúc này mới mở app trên điện thoại, vào từng video cũ chuyển sang **Chỉ mình tôi (Private)** trong vòng 1–2 phút.
  - Trang cá nhân lúc này sạch đẹp 100% theo đúng niche khách yêu cầu, trong khi tài khoản vẫn giữ trọn vẹn 1.000+ Follower và hàng nghìn Lượt thích đã tích lũy.
