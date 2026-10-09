# Tiêu Chuẩn Báo Cáo Batch Tiến Trình Farm (Watchdog & Batch Summary)

## 1. Nguyên Tắc Cốt Lõi: Đầy Đủ Mẫu Số & Tỷ Lệ Hoàn Thành
Khi xây dựng template báo cáo tổng kết tiến độ (upload avatar, 2FA, checklive, render, đăng ký...), **TUYỆT ĐỐI KHÔNG** chỉ liệt kê danh sách các máy thất bại hoặc máy còn tồn (`missing_machines`).
Báo cáo chỉ có số máy thiếu gây thiếu hụt ngữ cảnh: người dùng không biết tổng đàn có bao nhiêu acc, đã hoàn thành được bao nhiêu acc và tiến độ chung ra sao.

## 2. Cấu Trúc Bắt Buộc Của Report Template
Mỗi báo cáo tổng kết theo đàn / theo Tik phải gồm đủ 4 thành phần:
1. **Đã đạt được:** Số lượng tài khoản đạt trạng thái mục tiêu (`done_count` / `ok_count`).
2. **Tổng số lượng:** Tổng số tài khoản có ID hợp lệ trong workbook / inventory (`total_accounts`).
3. **Tỷ lệ %:** `(done_count / total_accounts) * 100`.
4. **Còn thiếu:** Số lượng máy còn thiếu kèm danh sách máy (nếu số lượng máy thiếu > 15 thì cắt gọn `... (+N)`).

### Ví dụ chuẩn hóa (HTML format cho Telegram Farm Alert):
```html
⏰ <b>[FARM REPORT][KIBE] BÁO CÁO UP AVATAR: HẾT KHUNG GIỜ</b>
• <b>Thời gian:</b> 23:40:53 14/09/2026
• <b>Trạng thái:</b> Hết khung giờ ca tối (sau 23:30) — Đã có: 210/377 acc (55.7%), còn 160 máy chưa up
• <b>Chi tiết từng Tik:</b>
• <b>Tik 5:</b> Đã có 36/78 (46.2%) — còn 42 máy (4,5,8,10,12,13... (+27))
• <b>Tik 6:</b> Đã có 71/79 (89.9%) — còn 8 máy (21,22,30,32,62,68,72)
• <b>Tik 7:</b> Đã có 28/45 (62.2%) — còn 17 máy (3,4,11,18... (+7))
```

## 3. Quy Tắc Khi Viết Script Trích Xuất Dữ Liệu Workbook
- Không chỉ lọc mỗi `unuploaded = []`.
- Luôn duyệt qua các dòng hợp lệ (bỏ qua header và dòng trống), đếm đồng thời:
  - `total_accounts`: dòng có ID tài khoản hợp lệ (`id not in (None, '', 'missing_id')`).
  - `uploaded_count`: dòng có cột mục tiêu (`Avatar`, `2FA`,...) đạt giá trị hợp lệ (`'ok'`, `'present'`, `'true'`, `'done'`).
  - `unuploaded`: danh sách máy có acc chưa đạt.
- Trả về dictionary/dataclass chứa cả 3 trường thông tin để format báo cáo chuẩn.
