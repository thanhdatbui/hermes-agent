# Chu kỳ Vận Hành 6 Ngày & Opportunistic Upload (Chốt 15/09/2026)

## 1. Bản chất & Nguyên lý Thuật toán TikTok
- **Không bào follow liên tục:** Việc cày follow mỗi ngày khiến điểm nghi vấn (anomaly score) tích lũy trên server TikTok và dễ kích hoạt án phạt nhả (follow release / soft action-block).
- **Ngày Nghỉ Dưỡng Sinh (Rest Day / Zero Follow):** Nick vẫn vào app lướt video giải trí bình thường nhưng tuyệt đối 0 follow và 0 upload. Hành vi tiêu thụ nội dung thuần túy này kích hoạt cơ chế xóa dần điểm phạt tích lũy (decay penalty) và phục hồi trust score.
- **Tần suất đăng video thực tế:** Cứ 2 đến 4 ngày đăng 1 video (trung bình 3 ngày/video ~ 10 video/tháng) là nhịp tự nhiên của một nhà sáng tạo nội dung thật (Casual Creator).

---

## 2. Bảng Phân Bổ Chu Kỳ 6 Ngày (Modulo 6)
Mỗi máy khớp 4 Ca/ngày (Ca 1 Sáng, Ca 2 Trưa, Ca 3 Tối, Ca 4 Đêm — mỗi ca chạy 1 slot -> 4 slot/ngày).
Toàn farm 80 máy chạy theo công thức: `day_cycle = (now.date() - date(2026, 9, 1)).days % 6`:

| Chu kỳ | Ca 1 (Sáng) | Ca 2 (Trưa) | Ca 3 (Tối) | Ca 4 (Đêm) | Tính chất ngày chạy | Hành vi thực tế |
| :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **Day 0** | Row 1 | Row 3 | Row 5 | Row 7 | **CÀY CHÍNH** | 2 phiên follow (10-20 follow/phiên) + Upload video cơ hội |
| **Day 1** | Row 2 | Row 4 | Row 6 | Row 8 | **CÀY CHÍNH** | 2 phiên follow (10-20 follow/phiên) + Upload video cơ hội |
| **Day 2** | Row 1 | Row 3 | Row 5 | Row 7 | **DƯỠNG SINH** | **100% CHỈ LƯỚT FEED, TUYỆT ĐỐI 0 FOLLOW, KHÔNG UPLOAD** |
| **Day 3** | Row 2 | Row 4 | Row 6 | Row 8 | **CÀY CHÍNH** | 2 phiên follow (10-20 follow/phiên) + Upload video cơ hội |
| **Day 4** | Row 1 | Row 3 | Row 5 | Row 7 | **CÀY CHÍNH** | 2 phiên follow (10-20 follow/phiên) + Upload video cơ hội |
| **Day 5** | Row 2 | Row 4 | Row 6 | Row 8 | **DƯỠNG SINH** | **100% CHỈ LƯỚT FEED, TUYỆT ĐỐI 0 FOLLOW, KHÔNG UPLOAD** |

- **Xét trên từng tài khoản:** Cứ cày 1 ngày follow sẽ có **48h Action Cooldown** (1 ngày không đụng tới + 1 ngày vào app chỉ lướt feed rửa trust).
- **Xét trên toàn farm:** Ngày nào cũng có đúng 4 slot hoạt động mượt mà, lưu lượng mạng/proxy phẳng 100%, không bị hiện tượng toàn farm cùng ngưng thở hay cùng spike.

---

## 3. Cơ Chế Opportunistic Upload (Đăng Video Cơ Hội Cả Phiên 1 & 2)
- **Vấn đề:** Nếu chỉ cố định đăng ở Phiên 2, khi Phiên 2 bị lỗi (mạng, popup) thì phải 4 ngày sau nick mới cày lại, dẫn tới nguy cơ 6–8 ngày mới có video mới, vỡ tiến độ nuôi mồi.
- **Giải pháp:**
  - Kích hoạt cờ `-AllowUploadHook` cho cả Phiên 1 lẫn Phiên 2 (vào ngày cày, NOT rest_day).
  - Tận dụng sổ cái `shift_upload_history.json`:
    - **Phiên 1:** Lướt feed xong thử đăng video ngay. Thành công -> ghi nhận vào sổ cái.
    - **Phiên 2:** Kiểm tra sổ cái thấy đã đăng trong ngày -> Tự động BỎ QUA (`already_uploaded_in_shift`).
    - **Nếu Phiên 1 lỗi:** Phiên 2 tự động phát hiện chưa có video thành công và đăng bù ngay lập tức.
  - Ngày dưỡng sinh (`is_rest_day`): Tắt cờ upload 100%.

---

## 4. Ngưỡng Budget & Quản Lý State An Toàn
- **Budget:** 10 – 20 follow / phiên (tối đa 20 – 40 follow/ngày active).
- **Hard Gate Video:** Chỉ nick $\ge 10$ video mới được chạy follow hook. Dưới 10 video -> budget = 0 (chỉ lướt feed nuôi mồi ~30 ngày đầu).
- **Pure Read Cooldown Check:** Hàm `is_account_in_follow_cooldown()` chỉ đọc (read-only), không mutate file JSON để chống race condition. Chuẩn hóa 100% UTC và bắt buộc match cặp `(machine, row)`, cấm fallback cấp máy.
- **Clear Cache App:** Chỉ dọn dẹp cuốn chiếu hoặc cuối ngày (04:00 sáng) qua cron để giải phóng bộ nhớ máy S7. CẤM xóa cache trước mỗi lần switch nick vì tạo signature bot lặp lại.
