# Bẫy Báo Cáo Ảo 6H Nuôi Gmail GPM & Quy Chuẩn Phân Định Cookie Văng Mới vs Hàng Đợi Re-login

Tài liệu chuẩn hóa kiến trúc báo cáo 6H (`cron_gpm_gmail_nurture_6h_report.py`), loại bỏ cảnh báo ảo (False Alarm Trap) và chống nghẽn hàng đợi nuôi định kỳ (`cron_gpm_gmail_nurture.py`).

---

## 1. Bản Chất Sự Cố "Báo Cáo Ảo 79 Acc Văng Cookie" (19/10/2026)

### Hiện tượng
Bản tin cron 6H định kỳ gửi về Telegram:
```text
📊 [BÁO CÁO 6H: TIẾN ĐỘ NUÔI GMAIL GPM]
• Tổng số profile Group 10 (Google Live Ready): 77
• Đã nuôi trong 6h qua: 20 lượt (5 workers cuốn chiếu)
• Tài khoản giữ session ấm (<48h): 22/77 profile (28.6%)
• Tiến độ trần an toàn hôm nay: 0/30 profile
⚠️ Acc phát hiện văng cookie (79 acc, đã đẩy re-login miễn trừ cooldown):
  - quyphuoc090565@gmail.com
  - vantieu011159@gmail.com
  ... và 74 acc khác
```

### Nghịch lý & Gốc rễ kỹ thuật
1. **Nghịch lý toán học:** Group 10 chỉ có 77 profile, nhưng báo cáo lại in 79 profile văng cookie!
2. **Không lọc theo GroupId:** Script báo cáo quét toàn bộ `gpm_gmail_nurture_state.json`. Trong đó có 29 tài khoản thuộc các nhóm cũ/đã xóa từ lịch sử tháng trước vẫn tồn lưu trạng thái `NEEDS_LOGIN`.
3. **Không lọc theo cửa sổ thời gian 6H (`WINDOW_HOURS`):**
   - Lượt nuôi trong 6h thực tế đạt 20/20 profile thành công (0 acc nào mới văng cookie).
   - Tuy nhiên, biến đếm `needs_login` gom toàn bộ acc từng dính `NEEDS_LOGIN` từ ngày 08/10 về trước mà không kiểm tra `(now_ts - last_checked) <= WINDOW_HOURS * 3600`.
   - Kết quả: Báo cáo biến toàn bộ hàng đợi tồn đọng thành "văng cookie trong ca này", gây hoang mang và bức xúc cho người vận hành.

---

## 2. Kiến Trúc Khắc Phục Bắt Buộc Trong `cron_gpm_gmail_nurture_6h_report.py`

### 2.1. Lọc Tập Hợp Group 10 Trực Tiếp Từ GPMLogin DB
BẮT BUỘC truy vấn danh sách email Group 10 trực tiếp từ `profile_data.db` (`GroupId = 10`):
```python
def get_group10_emails(db_path: Optional[Path] = None) -> Set[str]:
    path = db_path or GPM_DB_PATH
    if not path.exists():
        return set()
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        rows = conn.execute("SELECT Name FROM Profiles WHERE GroupId = ? OR GroupId = ?", (GROUP_ID, str(GROUP_ID))).fetchall()
        conn.close()
    except Exception:
        ...
    return {m.group(1).lower() for (name,) in rows if (m := EMAIL_RE.search(name or ""))}
```

### 2.2. Tách Bạch: Cookie Văng Mới Trong 6H vs Hàng Đợi Chờ Re-login
Khi duyệt `state`:
- **Chỉ xét profile thuộc Group 10:** `if group10_emails and em.lower() not in group10_emails: continue`
- **Tách 2 danh sách rõ ràng:**
  1. `dropped_6h`: Các acc có `status == "NEEDS_LOGIN"` VÀ `(now_ts - last_checked) <= (WINDOW_HOURS * 3600)`.
  2. `pending_relogin`: Toàn bộ acc Group 10 đang có `status == "NEEDS_LOGIN"`.

### 2.3. Quy Chuẩn Hiển Thị Minh Bạch
```python
if pending_relogin:
    if dropped_6h:
        report.append(f"⚠️ Acc văng cookie trong {WINDOW_HOURS}h qua: {len(dropped_6h)} acc")
        for em in dropped_6h[:5]:
            report.append(f"  - {em}")
        if len(dropped_6h) > 5:
            report.append(f"  ... và {len(dropped_6h) - 5} acc khác")
    else:
        report.append(f"• Trạng thái session {WINDOW_HOURS}h qua: ✓ Không có acc mới văng")
    report.append(f"⚠️ Tổng acc đang chờ re-login (Group {GROUP_ID}): {len(pending_relogin)} acc")
else:
    report.append("• Trạng thái session Google: ✓ 100% cookie sống tốt, không có acc văng")
```

---

## 3. Khắc Phục Bẫy Nghẽn Hàng Đợi Nuôi Vĩnh Viễn Trong `cron_gpm_gmail_nurture.py`

### Bẫy ngầm cũ
```python
# CŨ: Bỏ qua vô điều kiện, profile dính NEEDS_LOGIN bị kẹt vĩnh viễn không bao giờ được bốc nuôi
if info.get("status") == "NEEDS_LOGIN":
    continue
```

### Quy chuẩn Cooldown 24h Mới
```python
NEEDS_LOGIN_COOLDOWN_SECONDS = 86400  # 24 giờ cooldown

# MỚI: Chỉ bỏ qua nếu lần kiểm tra gần nhất chưa đủ 24h (để watchdog login xử lý)
if info.get("status") == "NEEDS_LOGIN" and (now_ts - info.get("last_checked", 0)) < NEEDS_LOGIN_COOLDOWN_SECONDS:
    continue
```
- Khi đã qua 24h hoặc khi profile được watchdog login cập nhật `LOGIN_RECOVERED`, profile tự động đủ điều kiện tham gia vòng lọc `due_profiles` để preflight cookie guard kiểm tra lại, chấm dứt tình trạng acc bị đóng băng nuôi vĩnh viễn.
