# Quy Tắc Vận Hành Reg Gmail Trên S7 Farm & Cơ Chế Bảo Mật Google

## 1. Cơ Chế Cooldown Bắt Buộc & Lựa Chọn Máy Reg
- **Cooldown cứng >= 4 ngày**: Một máy vừa reg Gmail thành công BẮT BUỘC phải nghỉ tối thiểu 4 ngày trước khi reg tài khoản tiếp theo. Tuyệt đối cấm reg liên tiếp cùng ngày hoặc cách nhau < 4 ngày.
- **Phân bổ Proxy**: Pick máy reg bắt buộc mỗi máy phải nằm trên một cổng Mobile Proxy độc lập, khác subnet/IP ra ngoài. Cấm dồn nhiều máy cùng chạy trên 1 proxy trong cùng một thời điểm.
- **Cấm đổi IP trước khi reg**: Giữ nguyên kết nối IP tự nhiên của máy và proxy.

## 2. Kỷ Luật Dữ Liệu: Tuyệt Đối Cấm Đoán Mò Mật Khẩu
- **Bắt buộc lưu password thực tế**: Bất kể chạy đơn lẻ, canary hay batch, password sinh ra phải được lưu ngay vào file kết quả / Excel nguồn (`gmail_clean_v2.xlsx`).
- **Nghiêm cấm tự bịa / đoán pass**: Không được dùng công thức sinh mật khẩu để đoán pass điền vào Excel khi script không lưu. Nếu không có pass thực tế được ghi nhận từ runtime, phải báo thẳng là mất pass và tiến hành gỡ bỏ tài khoản khỏi máy, tuyệt đối không điền pass đoán mò.

## 3. Rào Cản Bảo Mật Của Google Với Tài Khoản Vừa Tạo (Fresh Account)
- **Fresh Account Security Delay**: Tài khoản Google vừa tạo trên Android sẽ bị Google khóa truy cập vào các tính năng bảo mật cấp cao (Security Settings / 2-Step Verification) trong vòng vài giờ đến 24 giờ đầu.
- Khi truy cập vào mục "Xác minh 2 bước" ngay sau khi reg, Google sẽ yêu cầu nhập lại mật khẩu nhưng sau đó tự động reset trang hoặc chỉ cho phép chọn Passkey/Password lặp lại vô tận.
- **Quy trình chuẩn**: Tài khoản cần được ngâm tối thiểu 24h trên thiết bị trước khi thực hiện các tác vụ quản trị bảo mật (như bật 2FA Authenticator).

## 4. Kiểm Tra Trạng Thái Sống Của Gmail (Checklive)
- **Bắt buộc dùng web checklive (`checkmail.live`)**: Tuyệt đối không dựa vào trạng thái on-device trong app Gmail Android (app Gmail không hiện cảnh báo khi tài khoản bị khóa ngầm từ máy chủ).
- Khi checkmail.live báo DIE: Lập tức gỡ tài khoản khỏi Android OS (`Settings -> Accounts -> Google -> Remove account`) và xóa khỏi file Excel nguồn để tránh kẹt slot.
