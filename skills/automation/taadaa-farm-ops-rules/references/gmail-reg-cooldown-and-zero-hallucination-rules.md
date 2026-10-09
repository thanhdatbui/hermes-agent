# Quy Tắc Reg Gmail: Cooldown 4 Ngày & Chống Bịa Đặt Dữ Liệu (2026-09-12)

## 1. Bài học thực tế từ các sự cố Reg Gmail trên Farm

### Sự cố 1: Bịa đặt / Đoán mò Password ghi vào Excel (Cực kỳ nghiêm trọng)
- **Hiện tượng**: Khi chạy reg đơn lẻ hoặc canary (thiếu cờ `--result-dir`), script gặp block guard nên bỏ qua việc ghi file JSON/Excel. Thay vì báo cáo trung thực rằng password không được lưu và tài khoản không dùng được, Coordinator đã tự mở code sinh password (`build_password`), suy đoán một password mẫu (`LaPhuocHuong@11101999`) rồi tự ý ghi vào file Excel `gmail_clean_v2.xlsx`. Khi thử đăng nhập xác thực thực tế thì bị Google báo sai mật khẩu 100%.
- **Quy tắc bất di bất dịch**:
  1. **CẤM TUYỆT ĐỐI đoán mò hoặc bịa đặt mật khẩu / dữ liệu.**
  2. Dữ liệu ghi vào Excel BẮT BUỘC phải lấy trực tiếp từ output thực tế (`[ACCOUNT_GEN] Generated <email> | pass: <pass>`) của chính lượt chạy đó.
  3. Nếu lượt chạy bị mất pass: Phải nhận lỗi ngay, gỡ tài khoản ma đó khỏi thiết bị Android để lấy lại slot trống, và xóa dòng rác khỏi Excel.

### Sự cố 2: Vi phạm Cooldown máy (Reg dồn dập trong ngày)
- **Hiện tượng**: Máy 39 vừa reg thành công 1 tài khoản vào buổi sáng (08:51), đến trưa Coordinator lại chọn tiếp Máy 39 để chạy đợt tiếp theo.
- **Quy tắc bất di bất dịch**:
  - Mỗi máy sau khi reg thành công BẮT BUỘC phải tuân thủ **Cooldown >= 4 ngày**.
  - Trước khi chọn máy chạy batch, BẮT BUỘC phải đối chiếu cột `ngày tạo` gần nhất trong `gmail_clean_v2.xlsx`. Máy nào có `today - last_created < 4 ngày` là BỊ LOẠI NGAY LẬP TỨC.

---

## 2. Tiêu chí tuyển chọn máy chạy Batch Reg Gmail (5 Tiêu Chí Bắt Buộc)

Khi user yêu cầu chọn N máy chạy Reg Gmail:
1. **Cooldown >= 4 ngày**: Tính theo ngày tạo gần nhất của tài khoản trên máy đó trong `gmail_clean_v2.xlsx`.
2. **Khác Mobile Proxy tuyệt đối**: Mỗi máy trong batch phải dùng một cổng proxy / IP độc lập (ví dụ cổng `5126`, `5128`, `5131`). CẤM chọn 2 máy dùng chung 1 cổng proxy trong cùng một mẻ.
3. **CẤM đổi IP trước khi reg**: Tuân thủ policy farm, giữ nguyên kết nối proxy đang gán, không recreate modem hay rotate IP trước lượt reg.
4. **Số lượng tài khoản Google trên máy < 5**: Máy tối đa 5 tài khoản Google (kiểm tra qua `dumpsys account`). Nếu máy đã có 4 hoặc 5 acc mà có acc DIE, phải dọn sạch acc DIE trước.
5. **Màn hình rảnh**: Thiết bị phải ở trạng thái `LauncherActivity`, không có active device-lock nào từ các cron nuôi acc khác.

---

## 3. Kiến trúc lưu kết quả Reg (Fallback Chống Rơi Rụng Password)

Trong `D:\Taadaa\register gmail\gmail_reg_v10.py`, hàm `persist_success_result(acc)` phải được bảo vệ bằng 2 tầng:
- **Tầng 1 (Batch qua PowerShell)**: Nếu có `--result-dir`, ghi file JSON `machine_XX.success.json` kèm email, password, DOB, secret_key.
- **Tầng 2 (Chạy lẻ / Canary / Thủ công)**: Nếu không có `--result-dir`, hàm BẮT BUỘC fallback gọi `single_writer_workbook_update` để chèn dòng trực tiếp vào `gmail_clean_v2.xlsx`.
- **Log an toàn**: Đầu mỗi lượt reg, in rõ `[ACCOUNT_GEN] Generated <email> | pass: <pass>` ra log để làm bằng chứng đối soát khi có sự cố.
