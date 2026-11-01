# Chi Tiết Đối Soát Mailbox & Lịch Sử Thử Nghiệm TikTok Lite

## 1. Dữ Liệu Thực Nghiệm MÁY 1 vs MÁY 79
- **MÁY 1 (Cấm đụng)**: Mang dàn nick cựu binh tháng 2–3/2026 (`@tranngan767`, `@lipsellczaw`, `@duongkien1202`). Việc cài app lạ lên máy này gây rủi ro tê liệt nguồn follow của farm. Đã khôi phục nguyên trạng.
- **MÁY 79 (Testbed chuẩn)**: Mang 8 nick non reg tháng 9/2026 (`hoangtuannam2602`, `lavincghb5r`, `liddiwad5cr`...). Tổng following = 2. Cài app thử nghiệm cô lập rủi ro 100%.

## 2. Truy Vấn Đối Soát Mailbox SSOT
```python
import sqlite3

conn = sqlite3.connect('D:/Taadaa/data/farm_master.db')
cur = conn.cursor()

# 1. Tổng mail
total = cur.execute('SELECT count(*) FROM mailboxes WHERE provider IN ("hotmail", "outlook")').fetchone()[0]

# 2. Đã gán cho TikTok
assigned = cur.execute('SELECT count(*) FROM tiktok_accounts WHERE email LIKE "%hotmail%" OR email LIKE "%outlook%"').fetchone()[0]

# 3. Chưa gán (Unassigned)
unassigned = cur.execute('''
    SELECT count(*) FROM mailboxes m
    LEFT JOIN tiktok_accounts t ON m.email = t.email
    WHERE t.email IS NULL AND m.provider IN ("hotmail", "outlook")
''').fetchone()[0]

print(f"Tổng: {total} | Đã gán: {assigned} | Chưa gán: {unassigned}")
# Luôn trừ 26 mail dự phòng cho 26 nick dính Gmail DIE (khớp báo cáo watchdog_hotmail_replacer.log)
free_actual = unassigned - 26
print(f"Khả dụng thực tế cho việc khác: {free_actual}")
```

## 3. Quy Trình Thanh Trừng Mail Bị Ban
Khi 1 email bị TikTok cấm tài khoản khi reg:
1. Xóa ngay khỏi `farm_master.db`:
   ```sql
   DELETE FROM mailboxes WHERE email = '<email_bi_ban>';
   ```
2. Không cố đăng nhập lại trên bất kỳ máy hay app nào khác kẻo làm bẩn thiết bị (Device Contamination).
