# GPM Profile Online Backup, Retention & Core 142 Upgrade Patterns

Tài liệu kỹ thuật tổng hợp quy trình sao lưu trực tuyến (online backup), phục hồi (restore), xoay vòng dữ liệu (retention) và nâng cấp nhân trình duyệt Chromium Core 142 cho hệ thống GPMLogin v3 (Port 19995).

---

## 1. Cơ chế Sao lưu Database SQLite Trực tuyến (Online Snapshot)

### Vấn đề:
Khi GPMLogin đang mở hoặc các profile đang chạy, file `profile_data.db` liên tục bị lock hoặc có các transaction dở dang. Nếu dùng `shutil.copy2` hoặc `cp` thông thường sẽ dẫn đến:
- File bản sao bị rách (split-read / partial write).
- Khi mở lại báo lỗi `database disk image is malformed`.

### Giải pháp chuẩn:
Sử dụng trực tiếp `sqlite3.backup` API qua URI chế độ Read-Only (`mode=ro`), cho phép chụp snapshot nhất quán 100% mà không gây nghẽn tiến trình GPM:

```python
def safe_backup_db(src_path: str, dst_path: str, max_retries: int = 3) -> bool:
    uri = f"file:{os.path.abspath(src_path)}?mode=ro"
    for attempt in range(1, max_retries + 1):
        try:
            src_conn = sqlite3.connect(uri, uri=True, timeout=10)
            dst_conn = sqlite3.connect(dst_path)
            with dst_conn:
                src_conn.backup(dst_conn, pages=100, sleep=0.01)
            dst_conn.close()
            src_conn.close()
            return True
        except Exception as e:
            if os.path.exists(dst_path):
                try: os.remove(dst_path)
                except Exception: pass
            if attempt < max_retries:
                time.sleep(1.0)
    return False
```

---

## 2. Quy ước Schema GPMLogin & Lọc Profile Active

Trong cơ sở dữ liệu `profile_data.db` của GPMLogin:
- **`GroupId == 0`**: Là profile nằm trong **Thùng rác (Trash / Recycled)**. Khi gọi API update các profile này sẽ trả về lỗi `PROFILE_IN_TRASH`.
- **Active Profiles**: Có `GroupId IS NULL` hoặc `GroupId > 0` (hoặc `GroupId != 0`).
- **Schema Fallback**: Luôn kiểm tra `PRAGMA table_info(Profiles)` trước khi truy vấn để tương thích nếu GPM thay đổi phiên bản database.

```sql
SELECT Id, Name, ProfilePath FROM Profiles WHERE (GroupId IS NULL OR GroupId != 0);
```

---

## 3. Danh mục Tệp Thiết yếu vs Bỏ qua Cache Rác

Một profile Chrome thông thường nặng từ 150MB đến 400MB do chứa cache đồ họa và binary rác. Khi sao lưu hàng trăm profile, việc nén toàn bộ thư mục sẽ làm phình đĩa tới 40GB-100GB và làm chậm tiến trình nén (> 20 phút).

### Danh mục tệp thiết yếu (Bảo toàn 100% session, cookie, mật khẩu, tiện ích):
- **Tệp gốc profile**: `Local State` (chứa master key giải mã DPAPI), `First Run`, `Last Version`.
- **Tệp trong Default/**:
  - `Preferences`, `Secure Preferences`: Cấu hình vân tay, proxy, zoom, theme.
  - `Login Data`, `Login Data-journal`: Mật khẩu lưu trong trình duyệt.
  - `Web Data`, `Web Data-journal`: Dữ liệu autofill form.
  - `History`, `History-journal`: Lịch sử duyệt web.
  - `Network/Cookies`, `Network/Cookies-journal`: Toàn bộ session đăng nhập Google, ChatGPT, TikTok...
- **Thư mục lưu trữ**:
  - `Default/Local Storage` & `Default/Session Storage`: Token web app và session state.
  - `Default/IndexedDB`: Cơ sở dữ liệu client-side.
  - `Default/GPMSoft`: Dữ liệu đồng bộ mở rộng của GPM.
  - `Default/Extension State` & `Default/Sync Data`.

### Bỏ qua (Skip list):
`Cache`, `Code Cache`, `DawnWebGPUCache`, `DawnGraphiteCache`, `GPUCache`, `Crashpad`, `Service Worker/ScriptCache`, `WasmTtsEngine`.

👉 **Hiệu quả thực tế:**
- 254 profiles active giảm từ **~40 GB** xuống còn **~970 MB raw** $\rightarrow$ Nén zip lại chỉ còn **~376 MB** (tỷ lệ nén 38.6%).
- Thời gian nén toàn bộ 254 profiles: chỉ **~60 giây**.

---

## 4. Quy tắc Xoay vòng Lưu trữ (Retention)

- Lưu trữ trên OneDrive tại `D:\OneDrive\backup\GPM\`.
- Sắp xếp dựa trên cặp `(os.path.getmtime, filename)` tăng dần để xử lý chính xác kể cả khi chạy nhiều lần trong cùng một ngày.
- **Chỉ xoay vòng khi bản backup mới đạt trạng thái SUCCESS và vượt qua `testzip()` 0 file hỏng**. Nếu backup fail, giữ nguyên bản cũ.
- Duy trì tối đa 2 bản gần nhất (2 tuần), tự động dọn bản thứ 3 trở đi.

---

## 5. Nâng cấp Hàng loạt & Khóa Mặc định Chromium Core 142

### Nâng cấp profile cũ qua Local API v3:
Gọi endpoint `POST http://127.0.0.1:19995/api/v3/profiles/update/{id}` với payload:
```json
{
  "browser_version": "142.0.7444.163"
}
```
*Lưu ý:* Bỏ qua các profile có `GroupId == 0` (sẽ nhận `PROFILE_IN_TRASH`).

### Khóa mặc định trong code client (`src/gpm_client.py`):
Mọi hàm tạo profile mới phải có fallback mặc định:
```python
payload["browser_version"] = browser_version or "142.0.7444.163"
```
Đảm bảo 100% profile tạo mới không bao giờ bị rơi về nhân Chromium cũ (như v127).

---

## 6. Xử lý Lỗi ChatGPT-Web Sentinel 403 & Phòng ngừa Banned

- **Hiện tượng:** Khi OpenAI phát hiện request từ script/API ngoài giao diện web, họ trả về HTTP `403 Sentinel / Turnstile required`.
- **OmniRoute Behavior:** Tự động gán `testStatus = "banned"` và tắt `isActive = 0`.
- **Kỷ luật vận hành:**
  - **CẤM TUYỆT ĐỐI** retry dồn dập khi gặp 403 Sentinel. Nếu spam tiếp, OpenAI sẽ chuyển từ chặn tạm thời sang **vô hiệu hóa/xóa vĩnh viễn tài khoản** (`auth.openai.com/error?payload=...`).
  - **Bắt buộc kích hoạt:** `rate_limit_protection = 1` trên bảng `provider_connections` cho toàn bộ tài khoản ChatGPT-Web.
  - Cho tài khoản cooldown tối thiểu 24h-48h, hoặc mở trực tiếp trên browser GPM để giải quyết Turnstile/Proof-of-Work trước khi kích hoạt lại.
