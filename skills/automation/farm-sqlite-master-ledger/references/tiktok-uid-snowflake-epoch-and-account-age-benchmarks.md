# TikTok UID Snowflake Epoch Extraction & Account Age Benchmarks

## 1. Công thức Trích xuất Timestamp Tạo Nick O(1) từ TikTok Snowflake UID

TikTok (ByteDance) sử dụng định dạng 64-bit Snowflake ID cho UID người dùng. Trong đó, 32 bit cao nhất đại diện cho Unix epoch timestamp tính bằng giây:

```python
import datetime

def extract_tiktok_creation_datetime(uid: str | int) -> datetime.datetime:
    """Trích xuất ngày giờ đăng ký chính xác (UTC) từ TikTok UID mà không cần tra log.
    
    Zero-IO, xác định tuyệt đối thời điểm ByteDance cấp phát tài khoản.
    """
    uid_int = int(uid)
    epoch_seconds = uid_int >> 32
    return datetime.datetime.fromtimestamp(epoch_seconds, tz=datetime.timezone.utc)
```

### Ứng dụng trong Truy vấn SQLite Farm
Truy vấn trực tiếp trên `D:/Taadaa/data/tiktok_tracker.db` hoặc `farm_master.db`:
```python
import sqlite3, datetime

con = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db')
cur = con.cursor()
rows = cur.execute('''
    SELECT username, uid, min(following), max(following)
    FROM snapshots 
    WHERE uid IS NOT NULL AND uid != ''
    GROUP BY username
''').fetchall()

for username, uid, min_f, max_f in rows:
    reg_dt = datetime.datetime.fromtimestamp(int(uid) >> 32, tz=datetime.timezone.utc)
    # Xác định tuổi tài khoản chính xác theo ngày
```

---

## 2. Dữ liệu Thực tế: Trust Score & Ngưỡng Tuổi Đi Follow (1.269 Tài khoản Farm)

Đối soát thực nghiệm trên cơ sở dữ liệu Phone Farm (`tiktok_tracker.db`, thời điểm tháng 10/2026):

| Nhóm tuổi tài khoản | Tháng Reg | Tổng số acc | Tỷ lệ Following > 0 | Following TB | Đánh giá Trust Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cựu binh (7 - 8 tháng)** | 02 - 03/2026 | 123 acc | **96%** (118 acc) | **118.5** | Động cơ bơm follow nòng cốt, tỷ lệ giữ follow tuyệt đối. |
| **Trưởng thành (3 - 4 tháng)**| 06 - 07/2026 | 97 acc | **74%** (72 acc) | **14.3** | Bắt đầu follow được, cần giãn cách nhịp follow. |
| **Bắt đầu ngấm (2 tháng)** | 08/2026 | 200 acc | **52%** (105 acc) | **1.2** | Chỉ follow được 1-2 người, dễ dính shadow-unfollow. |
| **Non (< 1.5 tháng)** | 09/2026 | 829 acc | **12%** (100 acc) | **0.2** | **729/829 acc (88%) giữ Following = 0**, chưa thể follow. |

👉 **Quy luật:** Nick dưới **2.5 – 3 tháng tuổi (75 – 90 ngày)** bị thuật toán ByteDance siết cực chặt hành vi follow chéo. Ép chạy follow sớm sẽ dẫn đến tình trạng "nhả follow" (giao diện báo thành công nhưng reload bị mất) hoặc action block.

---

## 3. Kiến trúc Vận hành Slot & Xoay vòng Tài khoản (Anti-Blackout)

### Cạm bẫy Factory Reset sau khi bán lô 8 acc
- Khi bán sạch 8 acc trên 1 máy rồi khôi phục cài đặt gốc:
  1. **Đóng băng công suất 3 tháng:** Cả máy biến thành máy "chết" vì lô mới phải mất ~3 tháng mới bắt đầu có khả năng follow.
  2. **Device Fingerprint Trap:** Factory Reset thay đổi Android ID và hardware serial hash. Khi đăng nhập lại lô nick đã ngâm (từ TikTok Lite/tool ngâm), TikTok nhận diện là "Thiết bị mới hoàn toàn" -> Dễ dính checkpoint OTP / xác minh danh tính.

### Giải pháp Chuẩn Farm: Rolling Slots 50/50 & Dual-App TikTok Lite Soak
1. **Bảo tồn Động cơ Follow:** Mỗi máy luôn giữ lại **3 – 4 nick cựu binh** cố định để duy trì năng lực bơm follow cho toàn farm.
2. **Xuất bán Cuốn chiếu:** Khi 4 nick đạt 1.000 follow, chỉ tiến hành logout/`pm clear` trên 4 nick đó, **tuyệt đối không Factory Reset máy**.
3. **Gối đầu Nick non:** Nạp 4 nick non vào vị trí trống để ngâm và nuôi dưỡng sinh song song với 4 nick cựu binh đang chạy.
4. **Ngâm song song bằng Dual-App (TikTok Lite):**
   - Dùng TikTok Lite (`com.zhiliaoapp.musically.go` v47.6.1 chuẩn CH Play lưu tại `D:\OneDrive\apk-bank\com_zhiliaoapp_musically_go\tiktok_lite_latest.apk`) chạy song song với TikTok chính (`com.ss.android.ugc.trill`) trên cùng máy S7 mà không cần root hay Work Profile.
   - **CẠM BẪY CHẾT NGƯỜI: Gõ Hotmail thủ công = Instant-Ban 100%:** Gõ thủ công webmail `@hotmail.com` trên TikTok Lite khi máy đã có 8 nick chính bị ByteDance Security SDK gắn cờ bot/auto-reg và kích hoạt cấm tài khoản ngay tại bước tạo Profile (`Tài khoản của bạn đã bị cấm`).
   - **PHƯƠNG PHÁP CHUẨN XÁC: Google One-Tap SSO ("Tiếp tục với Google"):** Tận dụng các tài khoản Gmail LIVE vừa đăng ký xong đang nằm sẵn trên máy (`com.google` trong Account Manager). Bấm "Tiếp tục với Google", chọn Gmail -> Vượt qua toàn bộ bảo mật, bỏ qua bước mật khẩu, tạo nick thành công 100% (**ZERO CAPTCHA, ZERO BAN**).
   - **Lưu ý Re-authentication:** Nếu Gmail mới reg khi bấm Google SSO có hiện màn hình *"Google - Xác minh danh tính của bạn"*, chỉ cần bấm Tiếp tục và nhập lại mật khẩu Gmail 1 lần là Google nhả quyền cho TikTok Lite đăng nhập bình thường.
