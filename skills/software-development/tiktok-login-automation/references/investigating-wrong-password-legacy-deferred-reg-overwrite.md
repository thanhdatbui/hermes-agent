# Điều tra nguyên nhân lỗi sai pass TikTok do ghi đè pass ảo trong lịch sử (Legacy Deferred Reg Overwrite)

## 1. Hiện tượng & Triệu chứng
- Khi đăng nhập tài khoản TikTok qua ADB (`tiktok_login_v1.py` hoặc runner), màn hình trả về: `"Mật khẩu sai"` / `"Incorrect password"`.
- Tài khoản trong Excel (`taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`) có lưu mật khẩu đầy đủ, không bị rỗng.
- Kiểm tra trạng thái mail: Hotmail/Outlook Graph API OAuth token vẫn hoạt động 100% (bên bán không đổi mật khẩu mail hay revoke token).

---

## 2. Nguyên nhân gốc rễ (Root Cause) & 3 Vị Trí Gây Mất Pass
Trước bản vá ngày 2026-09-29, hệ thống đăng ký và ghi nhận deferred tracking có 3 lỗ hổng khiến mật khẩu thật bị đè hoặc xóa:

### Lỗ hổng 1: Tự sinh pass ảo khi flow không có màn nhập pass (`social_reg_v1.py`)
Code cũ:
```python
tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")
```
Khi nick đăng nhập qua OTP email (passwordless), flow không đi qua màn hình password (`tiktok_pw = ""`). Code cũ tự động gọi `make_tiktok_password()` tạo ra một pass ngẫu nhiên mới $P_{fake}$ ghi vào file JSON artifact, sau đó merge đè mất pass thật $P_{real}$ trong Excel (Case điển hình: M53 `@mgpovhrgnnq` bị đè từ `kNXM@jTwq6e#` thành `xg2L&O74Zo&$s*o`).

### Lỗ hổng 2: Deferred Writer ghi None xóa trắng pass cũ (`scripts/deferred_tracking_writer.py`)
Trong hàm `apply_deferred_result(ws, result)`:
```python
# CODE CŨ:
values = [..., result.get("password") or None, ...]
```
Nếu `result["password"]` rỗng (do flow OTP), script ghi `None` đè vào cột D của Excel, làm mất mật khẩu thật đang có.

### Lỗ hổng 3: Bước 8 tự sinh pass khi email đã tồn tại (`social_reg_v1.py`)
Khi `detect_after_continue == "registered"`, nếu tracking chưa có pass, script lại gọi `make_tiktok_password(found_pw or pw)` sinh pass mới không khớp với TikTok.

---

## 3. Các Bản Vá Chuẩn Hóa Đã Triển Khai (2026-09-29)

1. **Bảo toàn mật khẩu trong Deferred Tracking Writer (`deferred_tracking_writer.py`)**:
   ```python
   resolved_pass = result.get("password") or existing_pass or None
   values = [
       int(result["stt"]),
       check.tik,
       result.get("tiktok_id") or "",
       resolved_pass,
       ...
   ]
   ```
2. **Bảo toàn mật khẩu trong Direct Tracking Writer (`social_reg_v1.py`)**:
   - Trong `ensure_profile_completed_and_track`: Khi `not tiktok_pw`, đọc lại pass từ `get_tracking_account_meta(email)` để bảo toàn.
   - Trong `upsert_tracking_account`: Trước khi ghi sheet, nếu `not tiktok_pw and ex_pass`, gán `tiktok_pw = str(ex_pass).strip()`.
3. **Cấm tuyệt đối sinh pass ngẫu nhiên cho nick đã đăng ký (`social_reg_v1.py` - Bước 8)**:
   ```python
   if not tiktok_pw:
       if detect_after_continue == "registered":
           log("   ⚠ [pw] Account đã tồn tại nhưng tracking không có password -> CẤM sinh pass ngẫu nhiên!")
           tiktok_pw = ""
       else:
           tiktok_pw = make_tiktok_password(found_pw or pw) if (found_pw or pw) else ""
   ```
4. **Che giấu credentials trong log/telemetry (`mask_secret`)**:
   - Sử dụng helper `mask_secret(secret)` đưa toàn bộ in pass ra dạng `abc***` hoặc `<EMPTY>`, chống lộ mật khẩu trong logs và đạt chuẩn audit của Sol Reviewer.
5. **Bộ unit test bảo vệ (`tests/test_password_preservation.py`)**:
   - 5 test case kiểm chứng cô lập: helper mask_secret, upsert_tracking_account, ensure_profile_completed, registered không gọi make_tiktok_password, và deferred writer.
   - **PITFALL CẦN TRÁNH KHI VIẾT TEST**: Bắt buộc mock `TRACKING_PATH` về file tạm (`tmp_path / "nonexistent.xlsx"`). Nếu quên mock, `openpyxl.load_workbook(TRACKING_PATH)` sẽ đọc file 25MB thật trên OneDrive gây treo/timeout pytest > 30s!

---

## 4. Quy trình điều tra & Khôi phục chuẩn xác

### Bước 1: Truy vết lịch sử Artifacts
Không vội kết luận nick bị hack hay đổi pass bừa bãi. Tìm tất cả file artifact theo email/STT:
```python
import os, json
from pathlib import Path

target_mail = "mgpoverdezm@hotmail.com"
runs_dir = Path("D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all")
artifacts = sorted(runs_dir.rglob(f"*{target_mail}*.json"), key=lambda p: p.stat().st_mtime)

for p in artifacts:
    data = json.loads(p.read_text(encoding="utf-8"))
    print(f"{data.get('written_at')} | Pass: {data.get('password')}")
```
- **Lần run đầu tiên** (lúc tạo nick): Chứa $P_{real}$ chuẩn ban đầu (ví dụ: `kNXM@jTwq6e#`).
- **Các lần run sau**: Chứa $P_{fake}$ do bug fallback ghi đè.

### Bước 2: Thử nghiệm phục hồi
1. **Ưu tiên 1:** Thử đăng nhập lại bằng $P_{real}$ từ artifact đầu tiên. Nếu thành công, cập nhật ngay vào `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`.
2. **Ưu tiên 2:** Nếu $P_{real}$ vẫn không được:
   - Mở màn hình đăng nhập TikTok -> Bấm "Quên mật khẩu?" -> Chọn Email.
   - Lấy mã OTP qua Microsoft Graph API (chỉ 3-5 giây trên PC).
   - Đặt mật khẩu mới chuẩn format TikTok (hoa, thường, số, ký tự đặc biệt).
   - Cập nhật mật khẩu mới đồng bộ vào cả hai file Excel.
