# Active Shift Window Cutoff & Device Lock Preemption Invariants

## 1. Bối Cảnh Sự Cố Thực Tế (Khung Giờ 14h20 - Ca 2 Nuôi Farm)
Trong phiên chuẩn hóa Máy 244 (Slot Tik 3), khi đến 14h20:
- User chất vấn: `? h 2L19 r ? 2h19`.
- Lúc này, hệ thống Farm đã bước vào **Ca 2 Nuôi Feed (14:00 - 17:30)**, trong đó Slot Tik 3, 4, 8 đang chạy tiến trình tự động lướt video, follow và tương tác.
- Việc Agent tiếp tục can thiệp thủ công (chạy ADB, mở app, tap chuyển nick) khi đã quá 14h00 đã dẫn đến:
  1. **Xung đột tài nguyên (State Collision):** Cronjob nuôi feed tự động chạy ngầm, liên tục chiếm focus màn hình và chuyển đổi account trong app.
  2. **Account Drift:** Màn hình Profile bị chuyển sang nick khác (`@votu4084`) thay vì `@angthanhkhoa5528`, làm Agent bối rối, cố gắng tap account switcher và lặp lệnh vô ích.
  3. **Nguy cơ kẹt Device Lock:** Ôm lock hoặc cố force-preempt giữa ca nuôi làm gián đoạn lịch nuôi acc của toàn bộ Slot Tik 3.

---

## 2. Quy Tắc Cắt Giờ Cứng (Active Shift Cutoff Invariant)

### Lịch 3 Ca Nuôi Acc Cố Định Của Farm:
- **Ca 1 (Sáng):** `08:30 – 11:30` $\rightarrow$ Dành cho Slot **{Tik 1, Tik 2, Tik 7}**.
- **Ca 2 (Chiều):** `14:00 – 17:30` $\rightarrow$ Dành cho Slot **{Tik 3, Tik 4, Tik 8}**.
- **Ca 3 (Tối):** `19:30 – 22:30` $\rightarrow$ Dành cho Slot **{Tik 5, Tik 6}**.

### Các Bước Thực Thi Bắt Buộc (Mandatory Actions Khi Chạm Khung Giờ Ca Nuôi):
1. **Kiểm tra đồng hồ trước khi thao tác:** Trước khi can thiệp vào bất kỳ máy Farm nào, BẮT BUỘC đối soát giờ host và Slot của máy:
   - Nếu máy thuộc Slot của ca đang chạy (ví dụ Máy 244 thuộc Tik 3, giờ hiện tại $\ge$ 14:00 và $\le$ 17:30): **TUYỆT ĐỐI CẤM THAO TÁC THỦ CÔNG.**
2. **Dừng ngay lập tức khi chạm mốc thời gian:**
   - Nếu đang dở việc mà đồng hồ chạm mốc bắt đầu ca nuôi (14:00): **DỪNG NGAY.**
   - Không cố "làm nốt 1-2 bước", không cố chấp sửa ADB hay kéo ảnh.
3. **Quy trình nhả máy sạch (Clean Hand-off):**
   - Đưa TikTok về HOME (`input keyevent 3` hoặc `am force-stop com.ss.android.ugc.trill`).
   - Tắt màn hình an toàn (`input keyevent 223`).
   - Giải phóng toàn bộ `device_lock` ngay lập tức để cron nuôi acc của Farm vào việc.
   - Báo cáo rõ ràng cho User: Hiện tại đã vào khung giờ Ca nuôi, đã nhả toàn bộ lock để farm tự động vận hành an toàn.
