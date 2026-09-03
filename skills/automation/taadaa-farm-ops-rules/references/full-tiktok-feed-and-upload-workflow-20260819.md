# Full TikTok Feed, Follow & Upload Hook Workflow (19/08/2026)

## 1. Tổng Quan Lịch Chạy 3 Ca / Ngày
- **Ca 1 (Sáng):** `06:00 – 10:00`
- **Ca 2 (Trưa/Chiều):** `12:30 – 16:30`
- **Ca 3 (Tối):** `19:00 – 23:00`
Mỗi ca gồm 3 phiên chạy (Session 1, 2, 3) cách nhau 45–60 phút.

---

## 2. Chuỗi Xử Lý Tự Động 4 Bước Trong 1 Phiên
1. **Preflight & Prepare**:
   - Check VPN `tun0` (bắt buộc cho máy có proxy, bỏ qua nếu unmapped direct IP).
   - Mở TikTok, vào Account Switcher chọn đúng Nick theo Row của ca (`account_row_index`).
   - Tự động từ chối quyền hệ thống Android (`packageinstaller`): Tick "Không hỏi lại" + Bấm "TỪ CHỐI".
2. **Feed Session Smoke (Lướt Nuôi)**:
   - Phân bổ 3 Tab: Dành cho bạn (85%), Đang theo dõi (8%), Bạn bè (7%).
   - Tỉ lệ tương tác: Like FYP 8%, Following 15%, Friends 25%; Follow FYP 6%.
   - Xử lý popup in-app:
     - Phòng Live: Dừng 6–14s rồi bấm X thoát.
     - TikTok Shop: Dừng 3–7s rồi bấm X thoát.
     - Bài đăng lại: Dừng 2–4s rồi bấm X thoát.
     - Lượt xem hồ sơ / Tìm kiếm / Lưới sản phẩm: Bấm phím BACK.
     - Thẻ gợi ý kết bạn: Bấm nút "Follow lại".
     - Khảo sát quảng cáo / CTA: Vuốt lướt dứt khoát qua video kế tiếp.
   - Kết thúc swipe: Bấm Tab Hồ sơ đối soát Username TikTok trong Excel (`ctx.account`).
3. **Follow Hook (`tiktok-follow`)**:
   - Sau khi lướt feed hoàn tất:
     - Nếu nick đã bị nhả follow trong ngày (`follow_state_<m>_row_<r>.json`) -> Tự động BỎ QUA follow.
     - Nếu bình thường -> Chạy follow theo target. Nếu bị nhả follow sau vuốt -> Dừng ngay và ghi nhận cooldown cả ngày cho riêng nick đó.
4. **Upload Hook (`upload-hook` — Đăng Video Phiên Cuối)**:
   - Chỉ kích hoạt ở **Phiên cuối cùng của ca (`session_index == 3`)**.
   - Đọc workbook theo Row (`Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`...), tìm thư mục video và index `posted_count + 1`.
   - Kiểm tra video đã render sẵn tại `D:\TIKTOK-videonuoinick\<folder_video>\<next>.mp4`.
   - Chạy `tiktok-video` upload bài tự động.
   - Dọn dẹp ứng dụng chạy ngầm, đưa thiết bị về màn hình Home.

---

## 3. Nguyên Tắc Báo Cáo & Xử Lý Hiện Trường Lỗi
- Báo lỗi bắt buộc ghi đích danh lý do kỹ thuật từ ảnh `vision_analyze` và XML (CẤM mẫu câu chung chung).
- Giữ nguyên hiện trường lỗi để AI vá script trước -> Test thử tại chỗ -> Báo cáo kết quả.
