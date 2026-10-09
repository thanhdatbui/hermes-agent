# Gmail Reg & On-Device 2FA Operational Rules

## 1. Cơ Chế Cooldown & Chọn Máy Reg Gmail (BẮT BUỘC)
- **Cooldown 4 ngày (4d cooldown)**: Mỗi máy Samsung S7 sau khi reg thành công 1 tài khoản Gmail BẮT BUỘC phải ngâm/cooldown tối thiểu **4 ngày (>= 4 days)** mới được chọn để reg tài khoản tiếp theo.
- **CẤM TUYỆT ĐỐI**: Chọn lại máy vừa reg thành công trong ngày hoặc vi phạm cooldown 4 ngày (ví dụ: máy vừa reg buổi sáng thì tuyệt đối cấm chọn lại vào buổi trưa/tối).
- **Phân bổ Proxy**: Khi chạy batch nhiều máy, **BẮT BUỘC mỗi máy map 1 cổng Mobile Proxy khác nhau (khác IP egress)**, cấm chạy đồng thời 2 máy trên cùng 1 cổng proxy.
- **CẤM đổi IP trước khi Reg**: Giữ nguyên IP của cổng proxy được gán, không kích hoạt xoay/reconnect modem làm rớt phiên mạng thiết bị.

## 2. Kỷ Luật Dữ Liệu: CẤM BỊA / ĐOÁN MẬT KHẨU
- Khi tài khoản được tạo hoặc sinh ra, **BẮT BUỘC đọc từ payload/log thật (`[ACCOUNT_GEN]`)** do script in ra.
- **CẤM TUYỆT ĐỐI**: Tự ý suy đoán mật khẩu dựa trên công thức hàm sinh (`build_password`) rồi điền bậy vào file Excel (`gmail_clean_v2.xlsx`).
- Mọi trường hợp nghi ngờ mật khẩu chưa được ghi nhận vào file kết quả:
  + Phải kiểm tra file JSON trong `success_results/` hoặc log `[ACCOUNT_GEN]`.
  + Nếu không có log/artifact chứng minh mật khẩu thật, PHẢI THỪA NHẬN THỰC TẾ là mất mật khẩu, cấm tự bịa pass để điền.
  + Gỡ ngay tài khoản ma không rõ pass khỏi thiết bị để giải phóng slot sạch cho máy.

## 3. Fallback Lưu Excel Khi Chạy Đơn Lẻ / Canary
- Script `gmail_reg_v10.py` tại `persist_success_result(acc)` phải luôn có fallback `single_writer_workbook_update` ghi trực tiếp vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` khi chạy lẻ không truyền `--result-dir`.
- Hàm `merge_success_results.py` tại `write_success_row` luôn kiểm tra và lưu `item.get("secret_key")` vào cột 4 (`2FA`).

## 4. Hành Vi Bật 2FA Trên Gmail Mới Tạo (Fresh Account Restriction)
- Tài khoản Google vừa tạo trên Android OS sẽ bị Google áp đặt cờ bảo mật **"Fresh Account Security Delay / Loop Verification"** trong 24 giờ đầu:
  + Khi truy cập `Manage Google Account -> Security -> 2-Step Verification`, Google sẽ chặn ở màn hình WebView xác minh danh tính.
  + Kể cả khi nhập đúng 100% mật khẩu thật, Google sẽ reload lại chính màn hình đó (không báo sai pass nhưng không cho vào).
  + Bấm *Thử cách khác -> Passkey* cũng sẽ redirect ngược lại màn hình nhập mật khẩu.
- **Quy tắc vận hành**:
  + Không cố gắng spam nhập pass liên tục khi gặp hiện tượng Loop Verification này (dễ bị Google AI đánh dấu bot và khóa checkpoint).
  + Lưu email + password đầy đủ vào Excel, để tài khoản ngâm tối thiểu 24h trên thiết bị rồi mới kích hoạt luồng add 2FA hàng loạt.
