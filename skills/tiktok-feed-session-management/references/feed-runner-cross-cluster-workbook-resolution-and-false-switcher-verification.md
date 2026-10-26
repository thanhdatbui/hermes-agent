# Cross-Cluster Auto-Login Recovery & False Switcher Verification Trap

## 1. Hiện Tượng & Triệu Chứng (Sự Cố Ca Nuôi Feed 2026-10-26)
Trong các ca nuôi feed đa cụm (Kibe: M1-80, Admin: M201-280):
1. **M261 báo `Lệch Profile/Nick TikTok`:**
   - Runner phát hiện thiếu nick `thuthanh2911` $\rightarrow$ Kích hoạt `auto_login_recovery`.
   - Fast login (`tiktok_login_v1.py`) bị timeout/văng $\rightarrow$ Fallback sang `reconcile_tiktok_accounts.py`.
   - `reconcile_tiktok_accounts.py` crash ngay giây đầu tiên với mã thoát 2:
     ```text
     CONFIG_ERROR: machine 261 has no serial in workbook
     ```
2. **M274 lướt 16 video trên nhầm nick:**
   - Nick yêu cầu là Row 1 (`chicun0910`), máy đang ở Row 2 (`khanhthu22751`).
   - `profile_preflight` tap Switcher nhưng UI chưa kịp render xong handle `@khanhthu22751`.
   - Bẫy code: `not recaptured_username` $\rightarrow$ Coi như đã switch thành công (`verified = True`).
   - Đến cuối phiên, `_verify_profile_after_session` phát hiện nick thực tế không khớp $\rightarrow$ Fail với `profile account mismatch` mà không có recovery handler.

---

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)

### Bẫy 1: Hardcoded Kibe Workbook Trong Feed Monolith (`flows/feed_swipe_smoke.py`)
Tại các dòng khởi tạo hằng số và fallback:
```python
DEFAULT_RECONCILE_WORKBOOK = Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx")
DEFAULT_RECONCILE_LOGIN_WORKBOOK = Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx")
DEFAULT_RECONCILE_PROXY_MAPPING = Path(r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx")
```
Khi gọi `_maybe_recover_missing_account_via_login(ctx, expected, machine_id=261)`:
- Runner không đối soát `machine_id >= 200` để trỏ vào `D:\OneDrive\TaadaaData\admin\...`.
- Lệnh Reconcile nhận file của Kibe, tìm serial của M261 không thấy $\rightarrow$ Báo lỗi `machine has no serial in workbook` và fail-closed.

### Bẫy 2: Bẫy `verified` Khi Màn Hình Profile Chưa Kịp Render Handle
Trong `flows/feed_swipe_smoke.py`:
```python
verified = (
    selected_account_by_exact_switcher
    and latest_identity.get("xml_available") is True
    and recaptured_xml
    and not _is_profile_account_switcher_xml(recaptured_xml)
    and (
        not recaptured_username          # <-- BẪY NGUY HIỂM: XML chưa render xong handle đã vội pass
        or username_matches
        or display_name_matches
    )
)
```
Nếu mạng hoặc máy lag 1-2s, `@handle` chưa xuất hiện trong XML dump $\rightarrow$ `not recaptured_username` là `True`, dẫn tới hệ thống bỏ qua việc verify và nuôi feed nhầm nick suốt toàn bộ ca.

---

## 3. Quy Tắc Chuẩn Hóa Bắt Buộc (Invariants)

1. **Host-Aware Workbook Resolution trong Reconcile Fallback:**
   Trước khi build command gọi `reconcile_tiktok_accounts.py` hoặc `tiktok_login_v1.py`:
   ```python
   is_admin = False
   try:
       is_admin = int(machine_id) >= 200
   except (ValueError, TypeError):
       pass
   cluster = "admin" if is_admin else "kibe"
   cluster_root = Path(f"D:/OneDrive/TaadaaData/{cluster}")
   safe_wb = cluster_root / "taikhoan_run_safe.xlsx"
   dat_wb = cluster_root / "taikhoan_dat_v2_updated .xlsx"
   proxy_map = cluster_root / "PROXYgandienthoai.xlsx"
   ```
   BẮT BUỘC gán `TAADAA_HOST_CONFIG` tương ứng (`admin.yaml` hoặc `kibe.yaml`) vào môi trường thực thi của subprocess.

2. **CẤM Cho Pass Switcher Khi Chưa Đọc Được Handle:**
   Tuyệt đối không dùng `not recaptured_username` làm điều kiện `verified`. Nếu sau khi tap Switcher mà XML chưa chứa handle hoặc username không khớp:
   - Chờ thêm 1.5s - 2s và dump lại XML một lần nữa.
   - Nếu vẫn không khớp hoặc handle rỗng: Coi là switch thất bại, thử lại lần 2/3 hoặc chuyển sang `auto_login_recovery`.

3. **Verify Profile Cuối Phiên Phải Có Actionable Hand-off:**
   Nếu `_verify_profile_after_session` phát hiện `profile account mismatch`:
   - Ghi nhận `profile_mismatch_detected` và trigger switch về đúng nick hoặc gọi recovery login thay vì chỉ đơn thuần đánh dấu manual-needed rồi thoát.

4. **Canary Validation Pitfall: False-Positive Pass Trên Default `--row 1` & Timeout Scaling:**
   - Khi chạy Canary kiểm chứng sau khi fix auto-login / recovery: CẤM TUYỆT ĐỐI dùng `--row 1` mặc định nếu nick ở `--row 1` đã có sẵn trên máy (vì `profile_preflight` sẽ match ngay và skip luồng login recovery, sinh false-positive pass). Bắt buộc tra cứu đúng `--row <N>` của tài khoản đang vắng mặt hoặc bị lỗi trên máy.
   - Timeout cho Canary login trên cụm remote Admin ($m \ge 200$) qua socket `192.168.110.119:5037` bắt buộc $\ge 720s$ (đặc biệt khi có luồng giải OTP Graph API và reconnect remote adb), cấm để 300s gây timeout oan uổng.

5. **Kỷ Luật Dữ Liệu Excel Cột PASS (User Rule 2026-08-16 - CẤM Ghi Bậy Pass Vào Excel):**
   - Tài khoản reg email-only (qua app Outlook) chưa hoàn tất bước tạo mật khẩu tĩnh trên TikTok: cột `PASS` trong Excel BẮT BUỘC để `None` (trống).
   - Tuyệt đối CẤM sinh pass ngẫu nhiên rồi điền bậy vào file Excel khi server TikTok chưa có mật khẩu đó. Việc điền bậy sẽ khiến mọi runner lầm tưởng tài khoản đã có pass, thử login bằng pass dẫn tới lỗi `Mật khẩu sai` và nguy cơ bị TikTok khóa nick / rate limit.
   - Khi gặp tài khoản cũ bị dính pass rác/ảo trong Excel dẫn tới `Mật khẩu sai`, bước đầu tiên là kiểm tra dữ liệu; nếu nick thuộc diện email-only, xóa sạch ô PASS về `None` để các kịch bản login nhận diện đúng và kích hoạt luồng OTP (Graph API) thay vì gõ pass sai.
