# TikTok Change Linked Email Flow & Hotmail OAuth2 OTP Automation (2026-10-01)

## 1. Bối cảnh & Mục đích
- Khi tài khoản TikTok đang liên kết với email cũ bị mất mật khẩu/mất quyền truy cập hộp thư (ví dụ: Hotmail cũ tồn từ trước không có pass web), hoặc khi cần đổi sang Hotmail mới để phục vụ GPM automation (reg ChatGPT, v.v.).
- Thay vì bỏ tài khoản TikTok hoặc mò mật khẩu email cũ vô vọng, quy trình chuẩn là: **Đổi email liên kết trực tiếp trên TikTok app sang một Hotmail mới có Microsoft Graph API OAuth2 token**.

## 2. Bẫy Nghiệp Vụ & Kỷ Luật Điều Phối (User Correction 01/10/2026)
- **Bẫy "Báo Xong Ảo Khi Chỉ Mới Sửa Excel":** CẤM TUYỆT ĐỐI agent chỉ mới update cột email trong Excel/state mà đã vội vàng kết luận "đã hoàn tất", khi chưa thực sự thực hiện thao tác đổi email trên ứng dụng TikTok thật! (User nhắc nhở gay gắt: *"Là sao đã đổi mail liên kết tiktok qua hotmail ms chưa"*).
- **Bẫy "Email Này Đã Được Sử Dụng" (TikTok Duplicate Email Trap):**
  - Rất nhiều Hotmail mua ngoài hoặc còn tồn trong các file `latest_bought_*.txt` / `hotmail_input.txt` thực chất đã từng được farm dùng để đăng ký TikTok trong các đợt reg trước đó.
  - Khi nhập vào form "Thay đổi email" của TikTok, app sẽ hiện cảnh báo đỏ: `Email này đã được sử dụng` (`com.ss.android.ugc.trill:id/icn`).
  - **Cách xử lý:** Bắt buộc click nút "Xóa văn bản" (`[828,540][918,660]`) và thử Hotmail khác cho đến khi TikTok chấp nhận và chuyển sang màn hình `Xác minh email` (`com.ss.android.ugc.trill:id/f7l`).

## 3. Bản Đồ Điều Hướng UI TikTok v47.x (Samsung Galaxy S7 - 1080x1920)
1. **Chuyển Đúng Tài Khoản Cần Đổi Mail:**
   - Tại tab `Hồ sơ` (`[864,1794][1080,1920]`), tap vào tên hiển thị ở góc trên bên trái (`com.ss.android.ugc.trill:id/t7l`, khoảng `[36,280][325,364]`) để mở Account Switcher.
   - Chọn đúng tài khoản mục tiêu (ví dụ `@yobi1965`).
2. **Vào Cài Đặt Tài Khoản:**
   - Tap nút `Menu hồ sơ` (`[954,96][1056,204]`) $\rightarrow$ Tap `Cài đặt và quyền riêng tư` (`[204,1201][1038,1350]`, center `(595, 1273)`).
   - Tap `Tài khoản` (`[24,1704][1056,1878]`, center `(540, 1791)`).
3. **Mở Luồng Đổi Email:**
   - Tap `Thông tin tài khoản` (`[24,246][1056,402]`, center `(540, 324)`).
   - Tap `Email` (`[24,402][1056,558]`, center `(540, 480)`).
   - Dialog hiện `Email của bạn: <cũ>` $\rightarrow$ Tap `Thay đổi email` (`[120,1262][960,1405]`).
   - Dialog xác nhận "Thay đổi email? Email mới của bạn cũng sẽ được sử dụng cho xác minh 2 bước" $\rightarrow$ Tap `Tiếp tục` (`[541,1212][960,1355]`, center `(750, 1283)`).
4. **Nhập Email Mới & Submit:**
   - Tap ô `Nhập email` (`[162,567][918,632]`).
   - Nhập prefix của email mới qua ADB: `adb shell input text <prefix>`.
   - Tap nút đuôi gợi ý `@hotmail.com` (`[748,927][1069,1011]`, center `(908, 969)`).
   - Tap nút `Tiếp tục` (`[96,735][984,891]`, center `(540, 813)`).
   - Kiểm tra: Nếu hiện `Email này đã được sử dụng` $\rightarrow$ clear và đổi mail khác. Nếu chuyển sang `Xác minh email` $\rightarrow$ tiếp tục bước 5.

## 4. Tự Động Bắt OTP Qua Microsoft Graph API OAuth2
Khi tài khoản Hotmail có `refresh_token` và `client_id`:
```python
import urllib.request, urllib.parse, json, re

def get_tiktok_change_email_otp(refresh_token: str, client_id: str) -> str:
    # 1. Lấy access token
    token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "offline_access https://graph.microsoft.com/Mail.ReadWrite"
    }
    req = urllib.request.Request(token_url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp = urllib.request.urlopen(req, timeout=10)
    access_token = json.loads(resp.read().decode())["access_token"]
    
    # 2. Truy vấn thư mới nhất từ Microsoft Graph API
    graph_url = "https://graph.microsoft.com/v1.0/me/messages?$top=5&$select=subject,bodyPreview"
    req_msg = urllib.request.Request(graph_url, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    })
    resp_msg = urllib.request.urlopen(req_msg, timeout=10)
    messages = json.loads(resp_msg.read().decode()).get("value", [])
    
    # 3. Trích xuất mã OTP 6 số từ thư của TikTok
    for m in messages:
        subject = m.get("subject", "")
        preview = m.get("bodyPreview", "")
        if "tiktok" in (subject + preview).lower() or "mã" in (subject + preview).lower():
            match = re.search(r"\b(\d{6})\b", subject + " " + preview)
            if match:
                return match.group(1)
    return ""
```

## 5. Điền OTP, Hoàn Tất & Nghiệm Thu Bằng Chứng (Gate 6)
1. **Điền OTP trên thiết bị:**
   ```bash
   adb shell input text <otp>
   ```
2. **Đóng Prompt Tiếp Thị Của TikTok:**
   - Sau khi điền OTP thành công, TikTok hiện popup: *"Đã thêm email của bạn. Bạn muốn nhận nội dung thịnh hành...?"*
   - Tap nút `Không, cảm ơn` (`[38,1713][1043,1857]`, center `(540, 1785)`).
3. **Verify Màn Hình Email & Chụp Ảnh:**
   - Tap lại vào mục `Email` (`[24,402][1056,558]`).
   - Màn hình phải hiện: `Email của bạn: m***9@hotmail.com`.
   - BẮT BUỘC chụp ảnh `screencap` và gửi `MEDIA:<path>` ngay lập tức để chứng minh nghiệm thu.
4. **Đồng Bộ Dữ Liệu:**
   - Cập nhật Master Excel `taikhoan_dat_v2_updated .xlsx` (cột `GMAIL` và `PASS MAIL`).
   - Cập nhật GPM Supervisor State (`key`, `email`, `mail_password`, `stage: HOTMAIL_LOGIN`, `status: PENDING`).
