# Target Eligibility & Daily Registration Reservation Policy

## 1. Quy tắc lọc máy & mail chạy Reg (Target Selection Policy)

Chỉ cấp phát target cho máy khi thỏa mãn đồng thời cả 3 điều kiện:
1. **Giới hạn cứng tối đa 6 TikTok ID / máy (`max_accounts_per_machine = 6`):**
   - Quét cột `ID` trong tracking workbook (`taikhoan_dat_v2_updated .xlsx`).
   - Đếm số lượng TikTok ID không rỗng thuộc về `Máy` (STT).
   - Nếu `count >= 6` $\rightarrow$ **Loại bỏ vĩnh viễn** khỏi mọi đợt reg tiếp theo, tuyệt đối không cấp thêm mail thứ 7.
2. **Bắt buộc còn Mail nguồn hợp lệ chưa dùng:**
   - Quét nguồn `gmail_clean_v2.xlsx` cho STT đó.
   - Lọc các mail có password và domain hợp lệ (`@gmail.com`, `@hotmail.com`, `@outlook.com`, `@live.com`).
   - Mail được coi là "còn dư" khi email đó **chưa từng xuất hiện** trong tracking workbook.
   - Nếu máy còn $< 6$ acc nhưng đã hết mail nguồn chưa dùng $\rightarrow$ **Bỏ qua**.
3. **Không vướng Device Lock & Daily Cooldown:**
   - Không có lock vật lý active (`status=running`, `handoff`, `blocked`).
   - Không bị chặn bởi `is_machine_reg_cooldown_active(stt)` của ngày hôm nay.

---

## 2. Cơ chế Check-and-Reserve & Khóa liên tiến trình (Inter-Process Lock)

1. **Check-and-Reserve khi bắt đầu chạy:**
   - Hàm `reserve_machine_reg_slot(machine, serial=...)`:
     - Kiểm tra nguyên tử (atomic) xem máy có đang trong cooldown hay có tiến trình khác đang xử lý không.
     - Sinh một `token` UUID độc nhất và lưu trạng thái `"status": "in_progress"`.
     - Trả về `token` nếu thành công, trả về `None` nếu bị chặn.
2. **Giải phóng an toàn bằng Token:**
   - Mọi luồng đăng ký (`register()`, `--resume`) phải bọc trong `try ... finally`.
   - Nếu đăng ký không thành công (`not reg_success`): Gọi `release_machine_reg_reservation(stt, token=res_token)`.
   - Hàm bắt buộc token khớp chính xác thì mới xóa `in_progress` reservation, tuyệt đối không xóa nhầm reservation của process khác.
3. **Ghi nhận thành công (`SUCCESS`):**
   - Khi hoàn tất profile và tracking thành công: Gọi `record_machine_reg_success(stt, serial=...)`.
   - Ghi nhận `reg_success_date: today`, `cooldown_until: today + 1 day`, `status: success`.
4. **Nguyên tắc Fail-Closed:**
   - Nếu file `reg_daily_cooldowns.json` bị corrupt, unreadable hoặc schema không hợp lệ (`machines` không phải dict) $\rightarrow$ Tự động coi là active cooldown (chặn chạy tiếp) và từ chối ghi đè để bảo vệ an toàn cho thiết bị.
5. **Phân biệt Cooldown Record với Báo cáo ngày:**
   - Tuyệt đối không dùng số lượng bản ghi trong file cooldown để báo cáo "số máy thành công hôm nay". Cooldown lưu lịch sử đợt chạy trước (1-2 ngày trước).
   - Muốn báo cáo thành công trong ngày: Phải đối soát timestamp artifact thật của batch run hôm nay.
