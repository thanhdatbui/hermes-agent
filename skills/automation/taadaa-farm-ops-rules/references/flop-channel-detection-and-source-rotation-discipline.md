# Kỷ Luật Quét Kênh Flop, Xoay Nguồn Cào & Chống Khai Tử Acc (Farm Taadaa)

## 1. Nguyên Tắc Cốt Lõi: Không Bỏ Acc Khi Flop (Zero Account Abandonment)
- **CẤM TUYỆT ĐỐI BỎ ACC HOẶC HẠ CẤP THÀNH SEEDING-ONLY KHI FLOP:**
  * Nick bị flop (view thấp, tim lẹt đẹt) vẫn BẮT BUỘC duy trì lịch upload bình thường theo đúng nhịp độ farm.
  * CẤM dừng đăng, cấm xóa nick, cấm cậy kênh cũ để đổi niche (đổi bio/avatar/niche khác dòng làm loạn tệp khán giả và ăn gậy spam reach).
- **GIẢI PHÁP DUY NHẤT CHO FLOP: XOAY NGUỒN CÀO (SOURCE ROTATION):**
  * Flop phần lớn do nguồn video cũ bị trùng lặp (*multimodal duplicate*), creator gốc mất phong độ hoặc tệp video thiếu giữ chân người xem.
  * Thay thế nguồn video bằng cách hoán đổi sang creator sạch khác cùng ngách hoặc ngách hot viral (Douyin visual, Thú cưng cute, ASMR/Satisfying, Gái xinh Việt nhảy trend).
  * **Bắt buộc render tiếp nối (`start_seq = video_da_dang + 1`):** Sử dụng `swap_single_folder_pipeline.py --start-seq <video_da_dang + 1> --min-videos 40 --clean-old` để bảo toàn lịch sử số lượng clip đã đăng trong Master Excel, không đè số cũ, không đứt nhịp upload của bot.

## 2. Nguy Cơ Bùng Phát Tự Động Cào (Unbounded Auto-Scrape Hazard)
- **TẠI SAO CẤM CHO BOT TỰ ĐỘNG BÙNG PHÁT ĐI CÀO HÀNG LOẠT:**
  * Quy trình cào 1 kênh (40–45 clip) + render bằng FFmpeg tốn khoảng **15–30 phút CPU 100%** và **~2–3 GB dung lượng đĩa**.
  * Nếu trong 1 đợt quét phát hiện 20–30 kênh flop và bot tự động kích hoạt cào toàn bộ $\rightarrow$ hơn 1.000 clip dồn về sẽ **tràn sạch ổ D: Admin** (lỗi `0 MB free` làm sập render chain), nghẽn mạng proxy MikroTik và treo CPU.
- **MÔ HÌNH BÁN TỰ ĐỘNG 1 CHẠM (SEMI-AUTO VIA CRON 07:15):**
  * Tích hợp công cụ `flop_channel_scanner.py` vào cronjob **`daily-stale-upload-accounts-watchdog`** (07:15 sáng).
  * Bản tin buổi sáng tổng hợp sẵn Top kênh flop nặng nhất (sắp xếp tăng dần theo `heart_per_video` và `heart_count`) kèm sẵn câu lệnh swap O(1) đã tính sẵn `start_seq`.
  * User/Coordinator chỉ cần duyệt và copy lệnh chạy là máy tự động tải, render nối tiếp và sync Excel/DB sạch sẽ.
- **ĐIỀU KIỆN TIÊN QUYẾT NẾU TỰ ĐỘNG HÓA 100% (FULL-AUTO THROTTLE):**
  * Bắt buộc có **Cổng điều tiết (Throttle Gate):** Tối đa chỉ xoay **1–2 kênh/ngày**, chạy vào ban đêm (sau ca tối khi máy rảnh).
  * **Chỉ lấy từ Bể Nguồn Đã Kiểm Định (Curated Hot Pool):** Tuyệt đối cấm bot tự do search bừa bãi ngoài YouTube/TikTok tránh dính clip có tiếng nói nước ngoài (Trung/Anh) hoặc clip có mặt idol triệu follow.

## 3. Quy Chuẩn Kỹ Thuật GuardGate & Closeout Gate Khi Sửa Code Scanner
- **Invariant Step Comment (`check_step_by_step_structure`):** Mọi file Python mới thêm $\ge 15$ dòng code bắt buộc phải có ít nhất 1 dòng comment định danh bước rõ ràng matching regex:
  `#.*(buoc|bước|step|phase|stage|checkpoint)|#\s*={3,}`
- **Ngưỡng Cắt Tròn Diff (< 28.000 Chars):** Reviewer Sol High (:20129) sẽ trả `NEED_CONTEXT` hoặc trừ điểm kiến trúc/logic nếu diff bị cắt (`[truncated]` khi diff > 30.000 chars). Bắt buộc viết code cô đọng, súc tích để giữ diff toàn vẹn.
- **Closeout v2 Deterministic Fast-Pass:** Phiên sửa code có thể dùng `python D:/Taadaa/tools/closeout_v2.py --repo <repo> --target-file <file> --json-output` để kiểm tra deterministic `py_compile` + `pytest` focused mà không phụ thuộc vào chấm điểm cảm tính.
