# Quy Chuẩn Định Dạng Báo Cáo Telegram (Anti-Ugly Reporting & Dual-Cluster Standard)

## 1. Tránh Raw HTML Tags trong Watchdog / Cron Stdout
- Tuyệt đối không hard-code các thẻ HTML như `<b>`, `</b>`, `<i>`, `<div>`, `<br>` trong chuỗi output stdout của script khi delivery qua Telegram API.
- Các thẻ HTML thô nếu không được escape hoặc platform không xử lý HTML entity sẽ in nguyên văn ra màn hình chat gây phản cảm ("nhìn như loz").
- Sử dụng văn bản thuần (plain text) kèm bullet chuẩn hoặc markdown tự nhiên của platform.

## 2. Quy Tắc Rút Gọn Hạng Mục Hoàn Tất 100%
- Không in từng dòng lặp lại cho các hạng mục đã hoàn thành 100% (ví dụ: Tik 1 xong, Tik 2 xong, Tik 3 xong...).
- Gom nhóm lại trên một dòng duy nhất:
  ```text
  • Hoàn tất 100%: Tik 3, Tik 5, Tik 8
  ```

## 3. Ẩn Hạng Mục Trống (Zero Accounts)
- Những Tik/hạng mục chưa gán nick (`total_accounts == 0`) phải bỏ qua, không in ra các dòng thừa như `• Tik 4: chưa gán nick (0/80 acc)`.

## 4. Format Preview Danh Sách Máy Còn Thiếu
- Giới hạn tối đa 10 máy hiển thị trong danh sách máy thiếu/lỗi.
- Bắt buộc có dấu cách sau dấu phẩy: `(201, 202, 205, 208...)` thay vì dính liền `(201,202,205,208...)`.
- Nếu danh sách dài hơn 10 máy, gắn suffix `... (+N)` để giữ tin nhắn súc tích.

## 5. Cấu Trúc Báo Cáo Gộp Toàn Farm (Dual-Cluster)
Báo cáo toàn farm (Kibe Master) phải phân chia rành mạch 2 cụm:
```text
⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO: <TIÊU ĐỀ>
• Thời gian: HH:MM:SS DD/MM/YYYY
• Trạng thái: <Tổng kết toàn farm: Đã có X/Y (Z%), còn W máy>

🏢 【FARM KIBE - MÁY 1-80】: Đã có A/B (C%), còn D máy
  • Tik X: Đã có ... — còn ... máy (...)
  • Hoàn tất 100%: Tik Y, Tik Z...

🏢 【FARM ADMIN - MÁY 201-280】: Đã có E/F (G%), còn H máy
  • Tik M: Đã có ... — còn ... máy (...)
  • Hoàn tất 100%: Tik N...
```
