# Quy Tắc Lọc Profile GPM (GroupId=10) & Chặn Blacklist "khoale"

## 1. Bối cảnh & Nguyên tắc cốt lõi
- **GroupId=10 (Nhóm chuẩn Farm Kibe)**:
  - Trên hệ thống GPMLogin Local API v3 (`127.0.0.1:19995`), chỉ các profile được gán thuộc `GroupId = 10` mới là các profile Gmail chuẩn của Farm dùng cho:
    + Watchdog bật 2FA ca sáng (`post_morning_gmail_2fa_watchdog.py`)
    + Cron nuôi Gmail định kỳ (`cron_gpm_gmail_nurture.py`)
    + Watchdog đăng nhập Google ca tối (`post_evening_gpm_login_watchdog.py`)
  - Các profile thuộc Group khác (GroupId=0, GroupId=1, hoặc nhóm test/rác) tuyệt đối KHÔNG được nạp vào candidate queue.

- **Blacklist tài khoản rác / dính trảm "khoale"**:
  - Các tài khoản chứa chuỗi `khoale` (như các tài khoản dính mail khôi phục `khoaleemagic...` bị Google trảm hàng loạt hoặc profile rác) gây ra hiện tượng:
    + Kẹt vòng lặp checkpoint danh tính / Google DIE làm delay watchdog.
    + Gây lỗi văng session liên đới hoặc lãng phí băng thông proxy.
  - Bắt buộc lọc cứng: `if "khoale" in email.lower(): continue` ngay tại bước quét SQLite `Profiles` hoặc API `/api/v3/profiles`.

## 2. Quy chuẩn Code Bộ Lọc trong Watchdog & Cron

### Trong `post_morning_gmail_2fa_watchdog.py` (Truy vấn SQLite GPM trực tiếp)
```python
conn = sqlite3.connect(GPM_DB_PATH)
c = conn.cursor()
c.execute("SELECT Id, Name, ProfilePath, GroupId FROM Profiles ORDER BY Id ASC")
rows = c.fetchall()
conn.close()

for pid, name, ppath, gid in rows:
    if not name or name.startswith("AMZ_") or "deleted" in name.lower():
        continue
    # Gate 1: Chỉ lấy GroupId == 10
    if gid != 10:
        continue
    em_match = re.search(r"([a-zA-Z0-9_.+-]+@gmail\.com)", name, re.IGNORECASE)
    if not em_match:
        continue
    email = em_match.group(1).lower()
    # Gate 2: Chặn tuyệt đối khoale
    if "khoale" in email:
        continue
```

### Trong `cron_gpm_gmail_nurture.py` (Lọc từ API `/api/v3/profiles`)
```python
for p in all_profiles:
    # Lọc group_id == 10
    gid = p.get("group_id") or p.get("GroupId") or 0
    try:
        if int(gid) != 10:
            continue
    except (ValueError, TypeError):
        continue

    name = p.get("name", "")
    email = extract_email(name)
    if not email:
        continue
    # Chặn blacklist khoale
    if "khoale" in email.lower():
        continue
```

## 3. Quy trình Dọn dẹp Profile Rác trên GPMLogin
- Khi xóa profile rác khỏi GPM:
  1. Gọi endpoint DELETE Local API: `DELETE http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}`.
  2. Xóa các mục tương ứng trong file state JSON (`gpm_gmail_nurture_state.json`, `post_evening_gpm_login_state.json`) để tránh orphan tracking.
  3. Dọn dẹp thư mục profile data trên ổ đĩa nếu GPM không tự xóa sạch cache.

## 4. Kỷ luật Đồng bộ Dual-Location
- Mọi sửa đổi script watchdog / cron liên quan đến GPM trên repo nguồn (`D:\Taadaa\tools\` hoặc `D:\Taadaa\GPM auto\scripts\`) BẮT BUỘC phải được copy đồng bộ ngay sang thư mục thực thi của Hermes:
  `C:\Users\Kibe\AppData\Local\hermes\scripts\`
- Không bao giờ chỉ sửa ở một nơi vì Hermes cron chạy từ thư mục `AppData\Local\hermes\scripts`.
