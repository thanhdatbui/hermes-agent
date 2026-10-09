# Triage Lỗi Step 7c OTP Timeout, Phân Loại Google Account Health & Chẩn Đoán Mạng Tức Thời

## 1. Kỷ Luật Triage Phân Tầng Khi Batch Reg TikTok Thất Bại Hàng Loạt
Khi một đợt chạy batch (`_run_all_targets.py` hoặc chuỗi đêm `night-chain-reg-pipeline`) có tỷ lệ thất bại cao (ví dụ 21–23/25 máy fail):
- **CẤM TUYỆT ĐỐI**: Đọc lướt vài dòng log lỗi mạng của một vài máy ở cuối file log tổng hợp `social_reg_log.txt` rồi vội vàng kết luận "toàn farm mất mạng / chết proxy".
- **BẮT BUỘC**: Kiểm tra O(1) trực tiếp vào thư mục artifact run của đợt chạy đó:
  `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/<run_id>/batch_<N>/stt_<XX>/stderr.log` (và `stdout.log`).
- **Phân loại chính xác từng nhóm nguyên nhân**:
  1. **Nhóm kẹt Step 7c (OTP Timeout / Gmail health)**: Thường chiếm đa số (>70%), proxy và app vẫn thông suốt đến bước nhập email và bấm gửi mã OTP.
  2. **Nhóm kẹt thiết bị / UI**: `MACHINE_FULL_8_ACCOUNTS`, `TRACKING_WORKBOOK_WRITE_LOCKED`, không tìm thấy nút "Thêm tài khoản".
  3. **Nhóm rớt mạng tức thời**: Chỉ xảy ra trên các cổng PPPoE/modem cụ thể khi có chu kỳ reconnect lúc rạng sáng.

---

## 2. Cơ Chế Tự Động Kiểm Tra Sống/Chết Của Gmail (Step 7c Google Health Check)
Trong `social_reg_v1.py`, khi bước `[7c]` chờ OTP TikTok từ inbox quá 150s và đã bấm "Gửi lại mã" mà vẫn không có OTP, hệ thống **bắt buộc và tự động** gọi hàm:
```python
health = check_google_account_health_from_gmail(device_id, email, stt=stt)
```

### 3 Trạng thái phân loại chuẩn:
1. **Google CAPTCHA / Relogin (Mail DIE thật)**:
   - **Dấu hiệu log**: `[gmail-health] EXIT reason=google_captcha_confirmed` hoặc `google_account_relogin_required header=Y security_code_card=Y signin_button=Y`.
   - **Xử lý tự động trong code**:
     * Tạo bản backup `gmail_clean_v2.xlsx`.
     * Tự động xóa dòng chứa email chết ra khỏi file nguồn `gmail_clean_v2.xlsx`.
     * Ghi nhận và cách ly email vào sheet `Audit Pending` trong master tracking `taikhoan_dat_v2_updated .xlsx` với ghi chú: `Google CAPTCHA confirmed after normal sign-in; source row removed. Backup: ...`.
     * Ném ngoại lệ `[7c][google_captcha_dead_mail] <email> removed from Gmail source`.
2. **Google Account VẪN SỐNG (Google LIVE 100%, TikTok không phát mã OTP)**:
   - **Dấu hiệu log**: `[gmail-health] EXIT reason=target_account_not_verified (Google Account vẫn LIVE, nhưng TikTok không phát OTP)`.
   - **Ý nghĩa**: Tài khoản Google trên điện thoại hoàn toàn khỏe mạnh, không bị khóa, không đòi xác minh, nhưng server TikTok bị rate-limit phương thức email hoặc nghẽn gửi OTP. Mail này vẫn an toàn và giữ nguyên trong kho `gmail_clean_v2.xlsx`.
3. **Mail chưa đồng bộ / chưa đăng nhập trên App Gmail**:
   - **Dấu hiệu log**: `[otp-gmail] account list chua thay <email> (attempt 4/4, expanded=N)`.
   - **Ý nghĩa**: App Gmail trên máy chưa được nạp profile Google này, script không có hòm thư active để đọc thư. Cần kiểm tra lại profile Gmail trên thiết bị.

---

## 3. Chẩn Đoán Lỗi Mạng Tức Thời (Giải thích hiện tượng "Lúc chạy lỗi, kiểm tra lại thì không lỗi")
- Khi một số máy (như M77, M78, M79 đi qua cổng MikroTik PPPoE `10005..10007`) báo lỗi `Khong co ket noi Internet` lúc rạng sáng (01:10 - 01:20):
  * **Bản chất**: Các đường truyền PPPoE Viettel/FPT hoặc router MikroTik có thể trải qua đợt đổi IP WAN / renegotiation trong 1-2 phút.
  * Khi script thực hiện lệnh tap và kiểm tra status bar đúng lúc icon Wi-Fi có chấm than (`Tín hiệu Wi-Fi đủ.,Không có Internet.`), script lập tức ghi nhận lỗi mạng và thoát an toàn.
  * Vài phút sau khi PPPoE quay số xong và LAN ổn định, proxy thông suốt trở lại. Khi Coordinator probe lại thì thấy proxy LIVE 100%.
  * Cần giải thích rõ ràng và minh bạch cho user: Đây là hiện tượng drop mạng tức thời do WAN renegotiation tại thời điểm chạy, không phải lỗi proxy hỏng vĩnh viễn hay ngụy tạo kết quả.
