# Gmail-app magic-link tap thủ công — máy 34 (2026-08-08)

Session: verify email `truongthuy111034@gmail.com` đăng ký TikTok mới, máy 34
(ce031603b3158b0b02, SM-G930K). Runner đã fix giữ email ở màn magic-link
("Kiểm tra hộp thư" + "Gửi lại email sau N giây" = `verify_email_pending`,
commit 6615ac4 + 9803b8c) nhưng tự fail ở bước 7c ("OTP screen unavailable")
— còn lại phải làm tay: mở mail → bấm nút đỏ verify.

## Flow đầy đủ (verified từng bước)

1. TikTok gửi magic link → Gmail inbox mail đầu "Hoàn tất đăng ký bằng cách
   xác minh email" (thread group ~22 mail cùng chủ đề).
2. Vào Gmail app → tap mail đầu (thread). Lưu ý: tap list có thể cần
   **swipe nhẹ dọc (540,800→540,700) TRƯỚC tap** thì mới ăn (máy 34 hay nuốt
   tap đầu tiên trên ConversationList — uiautomator treo E=136/137 dai dẳng).
3. Kéo xuống cuối thread (2× `input swipe 540 1300 540 400 400`).
4. Mail mới nhất (vd "04:03") hiện link xanh "Hiển thị văn bản được trích
   dẫn" → tap link ĐÚNG mail này (tọa độ thay đổi theo scroll; xác định bằng
   screenshot+vision, KHÔNG tap link mail cũ phía trên — mail cũ cũng có link).
5. Link chuyển "Ẩn văn bản được trích dẫn" → kéo xuống HẾT
   (`input swipe 540 1300 540 400 400` ×2) → nút đỏ "Xác minh email" hiện.
6. Tap nút đỏ tại tọa độ pixel-scan → focus đổi sang
   `com.ss.android.ugc.trill/.account.login.v2.ui.SignUpOrLoginActivity`
   (dấu hiệu link đã mở).

## Pixel-scan tìm nút đỏ (chính xác hơn vision)

```python
from PIL import Image
img = Image.open(r"C:\Users\Kibe\AppData\Local\Temp\m34_gm5.png").convert("RGB")
w, h = img.size  # 1080x1920
red_rows = {}
for y in range(0, h, 4):
    count = 0
    for x in range(0, w, 4):
        r, g, b = img.getpixel((x, y))
        if r > 180 and g < 120 and b < 130:  # TikTok red
            count += 1
    if count > 15:
        red_rows[y] = count
ys = sorted(red_rows.keys())
clusters = []
if ys:
    start = prev = ys[0]
    for y in ys[1:]:
        if y - prev > 20:
            clusters.append((start, prev)); start = y
        prev = y
    clusters.append((start, prev))
for c in clusters:
    y_mid = (c[0]+c[1])//2
    xs = [x for x in range(0, w, 4) if (lambda p: p[0]>180 and p[1]<120 and p[2]<130)(img.getpixel((x, y_mid)))]
    if xs:
        print(f"tap=({(min(xs)+max(xs))//2},{y_mid}) x_range={min(xs)}..{max(xs)}")
# Kết quả thật: clusters [(724, 852)] → tap=(538,788) x_range=252..824
```

Kết quả: nút đỏ ổn định tại **(538,788)** — tap ăn NGAY. Các lần tap theo
vision: (540,414), (540,594), (540,871) — chỉ (540,871) tình cờ ăn 1 lần vì
màn scroll khác (email cũ layout khác), (538,788) ăn 2/2 trên mail mới.

## Expiry + resend

- Link valid **20 phút** ("Liên kết có hiệu lực trong 20 phút").
- Timeline thật: mail 04:03 hết hạn lúc 04:23; tap 04:25 → TikTok "Kiểm tra
  hộp thư" (từ chối). Tap "Gửi lại email" (540,1350) 04:28 → mail mới 04:28
  (hết hạn 04:48); tap 04:47 → verify OK 04:49-04:52.
- Sau tap resend, TikTok có cooldown gửi (~46-60s giữa các lần); chờ 15-20s
  rồi vào Gmail tìm mail mới.

## Sau tap link — verify thành công ≠ màn đổi ngay

Tap link xong TikTok HIỆN LẠI "Kiểm tra hộp thư của bạn" (màn chờ cũ) — KHÔNG
phải fail. Mở lại MainActivity:
`am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.main.MainActivity`
→ splash kẹt vài giây → vào **profile account MỚI**: banner "Hoàn tất hồ sơ
của bạn", follower 1 / following 0, chưa avatar, username tự đặt `@yobi1965`.
Account mới verified = email đã có TK → workbook/runner tiếp theo sẽ coi email
này là "đã đăng ký".

## Pitfalls session

- **uiautomator dump treo E=136/137 toàn phiên** trên máy 34 (kể cả sau
  pkill -9 atx) — dùng screenshot + pixel-scan + tap coordinate làm fallback.
- **Gmail swipe ngang = archive** (user: "m swipe ngang ms lỗi") — chỉ swipe
  dọc. Tôi từng swipe (540,600→540,300) dọc an toàn, nhưng tap sai vùng
  archive → mail mới nhất bị archive → user gỡ tay. KHÔNG tự mò quanh icon
  archive/delete top bar.
- **Tap menu ⋮ Gmail**: icon thật ở (960,144) không phải (940,85) — vision
  ước y lệch ~60px; sau back/scroll tọa độ đổi. Menu này không có "Mở trong
  trình duyệt" — nút đỏ tap trực tiếp được, không cần browser.
- **Settings TikTok tọa độ**: vision ước "Tài khoản" y~940 nhưng đó là LIVE;
  items cách ~146px, section Account ở ~y1500+ cần scroll. Đừng tin vision
  coordinate cho settings list — kẹt thì báo user.
