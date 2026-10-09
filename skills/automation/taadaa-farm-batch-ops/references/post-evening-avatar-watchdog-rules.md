# Quy chuẩn Watchdog Upload Avatar Sau Ca Tối & Kỷ Luật Báo Cáo (Cập nhật 13/09/2026)

## 1. Bối cảnh & Yêu cầu Kỷ luật của User
- **Khung giờ thực thi chuẩn (Ngay sau Ca Tối):** **21:00 – 23:30** hàng ngày.
- **Quy chuẩn tốc độ Worker (MaxParallel = 40):**
  - Mặc định cũ để 20 workers khiến danh sách 78 máy phải chia 4 lượt queue (mỗi lượt 10 phút) mất tới ~40 phút/batch.
  - **BẮT BUỘC để `-MaxParallel 40`** (mức trần an toàn của batch runner), giảm thời gian chạy 50% chỉ còn ~15–20 phút/batch.
- **Kỷ luật Báo cáo Farm Alert ("YÊU CẦU CHẠY XONG HẾT R MS ĐC BÁO, MÀ 40PH BÁO TIẾP V"):**
  - **CẤM TUYỆT ĐỐI** gửi tin nhắn báo cáo sau từng batch cuốn chiếu lẻ tẻ khi hệ thống vẫn đang retry máy chưa hoàn tất.
  - Các đợt chạy retry trong ca tối hoàn toàn **IM LẶNG trong background**.
  - **CHỈ BÁO CÁO 1 LẦN DUY NHẤT** khi:
    1. Toàn bộ các nick cần up avatar của toàn ca đã hoàn tất 100%.
    2. HOẶC khi hết hẳn khung giờ ca tối (sau 23:30): Bắn 1 tin tổng kết chốt hạ toàn ca duy nhất (thành công/còn thiếu).
    3. Tránh hoàn toàn việc spam tin nhắn lắt nhắt mỗi 40 phút.

---

## 2. Các Gate an toàn trước khi kích hoạt
1. **Khung giờ:** 21:00 đến 23:30.
2. **Feed Activity:** Không có runner nuôi nick nào đang hoạt động.
3. **Device Locks:** Số device-locks active $\le 5$.
4. **Batch Concurrency:** Không có batch upload avatar nào đang chạy.

---

## 3. Thứ tự ưu tiên & Danh mục mục tiêu
- Xử lý tuần tự: **Tik 5 $\rightarrow$ Tik 6 $\rightarrow$ Tik 7 $\rightarrow$ Tik 8 $\rightarrow$ Tik 3 $\rightarrow$ Tik 4**.
- Lọc ground truth từ workbook: Chỉ bốc các máy có ID hợp lệ và cột `Avatar != 'OK'`.
- Sau khi xong ca tối, đánh dấu `reported_date` để không phát cảnh báo lặp lại.
