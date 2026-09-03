# Quy Tắc Giới Hạn 6 Acc/Máy, Điều Tiết Worker & Preflight Token

## 1. Giới Hạn Cứng 6 Acc TikTok / Máy
- **Nguyên tắc:** Mỗi máy chỉ nuôi tối đa 6 tài khoản TikTok (tương ứng 80 máy = 480 accs).
- **Kiểm tra:** Đếm số lượng TikTok ID hợp lệ đã được ghi vào bảng tracking (`taikhoan_dat_v2_updated .xlsx`) cho từng STT máy.
- **Loại bỏ (Ineligible):** Máy nào đã có $\ge 6$ TikTok ID phải bị loại vĩnh viễn khỏi `_detect_clean.py` và runner, tuyệt đối không cấp thêm mail nguồn. Chỉ tái sử dụng sau khi đã xuất tài khoản và reset máy sạch sẽ.

## 2. Điều Kiện Target Kép
Một máy chỉ được đưa vào danh sách đăng ký khi thỏa mãn đồng thời cả 2 điều kiện:
1. `machine_account_count < 6` (máy chưa đủ 6 acc TikTok).
2. Có ít nhất 1 mail nguồn hợp lệ (Gmail hoặc Hotmail có password/token) trong `gmail_clean_v2.xlsx` mà chưa xuất hiện trong bảng tracking.

## 3. Điều Tiết Worker & Capping Ca Chạy (Tránh Rate-Limit TikTok)
- **Capping:** Mỗi ca đêm chỉ chạy tối đa 30 máy (`--max-targets 30`).
- **Concurrency:** Giảm worker xuống 6 workers cuốn chiếu song song (`--max-workers 6`, stagger delay 2–8s). Tuyệt đối không chạy 40 máy ào ạt cùng lúc vì gây nghẽn proxy, nghẽn ADB bridge và kích hoạt hệ thống phát hiện bot của TikTok (*"Bạn truy cập dịch vụ của chúng tôi quá thường xuyên"*).
- **Chuỗi thực thi:** Pipeline đêm chạy tuần tự hoàn toàn (Phase 1 Reg Gmail chạy xong 100% -> nghỉ 10s flush file -> Phase 2 Reg TikTok), không dùng trigger giờ cứng làm đụng độ.

## 4. Preflight Test Token Microsoft Graph API Khi Mua Hotmail
- Khi mua Hotmail từ các web shop (boxtaikhoan, clonefbig, taphoammo...):
  1. Mua thử nghiệm 1–2 tài khoản trước khi mua số lượng lớn.
  2. Dùng hàm `exchange_refresh_token(refresh_token, client_id)` gọi trực tiếp Microsoft OAuth2 endpoint `https://login.microsoftonline.com/common/oauth2/v2.0/token`.
  3. Nếu Microsoft trả lỗi `AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid` (dấu hiệu lô token bị chết hoặc bị nhà cung cấp gán đuôi giả như `-CqHaQs6MPmfx...`) -> **DỪNG LẠI NGAY**, cách ly lô hàng và không nạp vào `gmail_clean_v2.xlsx`.
  4. Chỉ nạp vào kho khi token exchange trả về `access_token` hợp lệ và đọc được tin nhắn inbox từ Graph API.
