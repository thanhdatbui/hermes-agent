# Quy Tắc Upload & Follow Hook Trong Lịch 4 Ca x 2 Phiên (Chốt 12/09/2026)

## 1. Khung giờ & Phân ca (HCMC)
- **Ca 4 (Đêm):** P1 `00:00` | P2 `01:30` — Row 8 (ngày chẵn) / Row 7 (ngày lẻ)
- **Ca 1 (Sáng):** P1 `06:00` | P2 `08:00` — Row 2 (ngày chẵn) / Row 1 (ngày lẻ)
- **Ca 2 (Trưa):** P1 `12:00` | P2 `14:00` — Row 4 (ngày chẵn) / Row 3 (ngày lẻ)
- **Ca 3 (Tối):**  P1 `18:00` | P2 `20:00` — Row 6 (ngày chẵn) / Row 5 (ngày lẻ)
- **Dead zone:** 02:30 đến 05:59 (không spawn phiên mới).

## 2. Quy tắc Upload Hook (Mở cả Phiên 1 và 2, Max 1 lần/ca)
- **Cơ chế:** Cả Phiên 1 và Phiên 2 đều truyền cờ `--allow-upload-hook`.
- **Phiên 1:** Sau khi lướt feed, máy tự động tìm file video MP4 theo Row trong workbook Tik tương ứng và tiến hành đăng bài.
- **Phiên 2 (Cơ chế fallback/retry tự động):** 
  - Nếu Phiên 1 **đã đăng thành công**: Sổ cái nguyên tử `_ShiftUploadLedger` phát hiện ca này đã hoàn thành $\rightarrow$ Safe-Skip ngay trong 0.1s (`already_uploaded_in_shift`), cam kết tuyệt đối không bao giờ đăng 2 lần.
  - Nếu Phiên 1 **chưa có video hoặc bị lỗi** (mạng rớt, proxy đóng, thiết bị bận): Phiên 2 tự động bù đăng ngay sau khi lướt feed.

## 3. Quy tắc Follow Hook (Thống nhất ngưỡng tối thiểu 5 video)
- **Điều kiện duy nhất:** Tài khoản phải có **tối thiểu 5 video (`video_count >= 5`)** mới được phép kích hoạt follow hook.
- **Đã gỡ bỏ chặn cứng Row 3..6:** Bất kỳ Row nào (1..8) nếu tài khoản có $\ge 5$ video đều được đi follow chéo theo Mode 2.
- **Tài khoản < 5 video:** Tự động safe-skip (`under-5-videos-follow-disabled`) để tránh bị TikTok nhả nút follow và dính shadow-ban do nick chưa đủ độ uy tín (trust).

## 4. Báo cáo Chốt Phiên & Watchdog
- **BẮT BUỘC:** Báo cáo sau mỗi phiên hoặc khi chốt phiên điều phối BẮT BUỘC phải thể hiện đầy đủ cả 3 trụ cột:
  1. **Lướt Feed:** Success / Fail / Số swipes.
  2. **Upload Video:** Số video đã đăng thành công, lý do skip/lỗi theo sổ cái.
  3. **Follow Chéo:** Số lượt follow thành công, nhả follow, lỗi hoặc bỏ qua do chưa đủ 5 video.
- Tuyệt đối không được gửi báo cáo khuyết một trong ba trụ cột trên.
