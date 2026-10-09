# Quy Tắc Age Gate & Follow Gate Cho Nick Mới (Chốt 2026-09-17)

## 1. Bản chất & Sự phân tầng bảo vệ
- **Follow Gate (Tầng mở rộng tương tác - Social Expansion):**
  - **Điều kiện:** BẮT BUỘC tài khoản phải đăng thành công `>= 10 video` + không trúng ngày Dưỡng sinh (Organic Rest ~33%).
  - **Thực tế vận hành:** Farm chạy 80 máy, mỗi máy nuôi 8 nick (8 rows, 3 ca/ngày). Một tuần một nick chỉ lên sàn vài lần kết hợp Organic Rest, do đó để đăng đủ 10 video thực tế đã mất **30 đến 45 ngày (1.5 tháng)**. Trong suốt thời gian này, tài khoản đã có lịch sử đăng nhập, lướt feed, xem video, thả tim, đọc comment định kỳ. Khi chạm mốc 10 video, nick đã rất "già" và cứng cáp, hoàn toàn sẵn sàng đi follow chéo an toàn.
  - **Kết luận:** Follow Gate là rào cản sinh tử quan trọng nhất, giữ vững mốc `>= 10 video`.

- **Age Gate (Tầng xuất bản nội dung - Warm-up Publishing):**
  - Trước đây: Cấm đăng video khi tuổi nick < 10 ngày (`CREATION_COOLDOWN_DAYS = 10`). Điều này khiến tổng thời gian warm nick bị đội lên tới gần 2 tháng.
  - **Quy tắc mới:** Cooldown **3 ngày** (`CREATION_COOLDOWN_DAYS = 3`).
    - Ngày 0–2: Nick mới chỉ đăng nhập, ngâm máy, lướt feed giải trí nhẹ, hoàn thiện profile. Tuyệt đối không public video.
    - Từ ngày thứ 3 trở đi: Mở khóa cho phép đăng video đầu tiên và bắt đầu tích lũy mốc 10 video.

## 2. Pitfalls Kỹ Thuật (Hiện trường & Data Parsing)
- **Lỗi chuỗi ngày dính giờ trong Excel (`account_creation_date_unverifiable`):**
  - Cột `NGÀY TẠO` trong workbook `taikhoan_dat_v2_updated .xlsx` hoặc file Excel data thường được xuất kèm timestamp (ví dụ: `2026-09-13 00:05:25`).
  - Hàm `parse_date_safely` nếu chỉ dùng `strptime(s, "%Y-%m-%d")` sẽ ném ngoại lệ và trả về `None`.
  - Hậu quả: Script kích hoạt cơ chế fail-closed, tưởng nhầm tài khoản chưa có ngày tạo và chặn đăng video hàng loạt máy oan uổng (điển hình 10 máy dính `account_creation_date_unverifiable` trong Ca 4 Row 7).
  - **Quy chuẩn xử lý:** Luôn cắt chuỗi lấy phần date trước khoảng trắng `s_clean = s.split()[0] if " " in s else s` trước khi so khớp các định dạng ngày.
