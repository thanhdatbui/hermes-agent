# Google Identity Lifecycle: Trust Score, 2FA Challenge Bypass & Antigravity Aging

## 1. Bản chất Phân tầng An ninh Google: Trust Score vs Verification Fallback
- **2FA TOTP không làm tăng Trust Score**: 2FA chỉ chứng minh "Kẻ trộm không cướp được pass", không chứng minh "Đây là người thật".
- **2FA TOTP là LÁ CHẮN THOÁT HIỂM (Deterministic Challenge Bypass)**:
  - Khi chuyển từ điện thoại Android S7 (thiết bị gốc) lên PC (GPM Chromium qua proxy 4G), hệ thống Risk-Based Authentication (RBA) của Google lập tức kích hoạt Secondary Challenge do đổi fingerprint phần cứng và dải mạng.
  - **Nếu KHÔNG có 2FA**: Google không có chìa khóa bảo mật dự phòng -> Ép vào **SMS số điện thoại (`challenge/iap`)** -> Tài khoản farm không có SIM sẽ chết đứng (DIE).
  - **Nếu CÓ 2FA TOTP**: Google ưu tiên hỏi mã 6 số Authenticator -> Script điền mã TOTP từ Excel -> Vượt checkpoint 100% không bị đòi SMS.

## 2. Quy trình Vòng đời Chuẩn 7 Bước (S7 -> GPM -> OmniRoute)

```
[1. Reg S7] ---> [2. Reg ChatGPT Chrome S7] ---> [3. Bật 2FA TOTP trên S7]
                                                            |
                                                            v
[5. Login GPM (Pass+TOTP)] <--- [Ngâm 7 ngày trên S7] <----+
       |
       +---> [6. Lấy ChatGPT-Web ngay + Lướt nhẹ YouTube/Search 60s]
       |
       v (Ngâm tiếp 7 ngày trên GPM)
[7. Cấp OAuth Antigravity (Google Cloud Developer API)]
```

### Chi tiết các bước:
1. **Reg Gmail trên S7**: Tạo gốc thiết bị sạch.
2. **Reg ChatGPT trên Chrome S7 (Direct Email OTP)**: Nhận mail OTP từ OpenAI tạo vết tương tác thực tế đầu tiên. Tuyệt đối không dùng Google SSO khi mới reg.
3. **Bật 2FA TOTP trên S7**: Bắt buộc làm trên S7 (kết hợp ADB bốc mã bảo mật 10 số của S7) vì đây là môi trường mẹ có Trust cao nhất. Lưu Secret 32 ký tự vào `gmail_clean_v2.xlsx` (Cột 4) và `master_gmail_manager.xlsx` (Cột 5).
4. **Ngâm tĩnh 7 ngày trên S7**: Bật Auto-Sync, duy trì nhận push notification bình thường.
5. **Login GPM sau 7 ngày**: Điền User/Pass + giải 2FA TOTP tự động từ Excel, vượt qua rào cản IP mới của PC mà không bị checkpoint SMS.
6. **Lấy ChatGPT-Web ngay + Pha loãng hành vi (Noise Injection)**:
   - ChatGPT là dịch vụ bên thứ ba (Web Consumer App), Google coi đây là hành vi lành tính -> Lấy token nạp vào `chatgpt-web-pool` dùng ngay.
   - Thêm 60s xem 1 video YouTube ngẫu nhiên (like/subscribe) và search 1 từ khóa Google Search để tạo Watch/Search History trên profile GPM.
7. **Hoãn Antigravity $\ge 7$ ngày (Profile Aging)**:
   - **Lý do**: Google Cloud Developer API (`cloudaicompanion.googleapis.com` / `cloud-platform`) là High-Risk/Sensitive Scopes. Vừa xuất hiện trên PC mà ngay trong Session 1 đã xin quyền Developer Cloud API sẽ bị Risk Engine cắm cờ *"New Device Anomaly + Developer Privilege Escalation"*, dẫn đến trảm hàng loạt sau 30-45 ngày.
   - **Giải pháp**: Chỉ cấp quyền OAuth Antigravity khi profile GPM đã có "hộ khẩu" ổn định $\ge 7$ ngày trên PC.

## 3. Quản trị Kho Gmail & Profile GPM
- **Check-live trước khi thao tác**: Bắt buộc dùng `run_checkmail_kibe_farm.py` (engine `checkmail.live` qua proxy mobile farm) để phân loại LIVE/DIE trước khi cho login GPM hay liên kết dịch vụ.
- **Dọn dẹp kép (Dual Cleanup)**: Khi phát hiện nick DIE:
  1. Gỡ bỏ profile GPM tương ứng qua `sync_gpm_lifecycle.py`.
  2. Gỡ tài khoản khỏi `dumpsys account` trên S7 để tránh lỗi treo đồng bộ app Gmail cho các tài khoản LIVE còn lại.
- **Rà soát Chùm Recovery Email (Graph Clustering Risk)**: Tránh dồn hàng trăm tài khoản trỏ về cùng 1-2 recovery email (như `thanhdatbui...` hay `khoalee...`), vì thuật toán Identity Graph của Google sẽ gom cụm và trảm dây chuyền khi quét định kỳ.
