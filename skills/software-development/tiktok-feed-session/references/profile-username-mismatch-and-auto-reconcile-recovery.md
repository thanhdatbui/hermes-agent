# Xử lý lỗi "profile username still mismatched after switch" & Mở rộng Auto-Reconcile Fallback (06/09/2026)

## 1. Hiện tượng & Triệu chứng
- **Alert:** `🚨 [FARM ALERT: MÁY N] DỪNG PHIÊN`
- **Triệu chứng:** `profile username still mismatched after switch`
- **Hiện trường:** Điện thoại đang ở tab Hồ sơ (Profile), nhưng username hiển thị trên header là nick cũ (hoặc nick khác, ví dụ `khoa4597`), trong khi nick mục tiêu được phân công là nick khác (ví dụ `lamnhu3003`).

---

## 2. Nguyên nhân gốc rễ (Root Cause)

1. **Settle Time sau khi chọn switcher option quá ngắn:**
   - Trong `verify_and_switch_profile` (`feed_swipe_smoke.py`), sau khi tap row của tài khoản đích trong bottom sheet switcher:
     * TikTok cần thời gian tải session token từ máy chủ qua proxy/mạng farm và render lại thông tin Profile.
     * Code cũ chỉ chờ `time.sleep(random.uniform(2.0, 3.0))` rồi lập tức gọi `_navigate_profile_for_preflight` và đọc XML.
     * Mạng farm chậm hoặc máy phản hồi chậm khiến XML chụp được vẫn mang username của tài khoản cũ.

2. **Thiếu cơ chế Auto-Reconcile cho lỗi Mismatch:**
   - Khi đã thử switch đủ `attempts` (3 lần) mà username vẫn không khớp, flow gán:
     ```python
     last_reason = "profile username still mismatched after switch"
     ```
   - Tại đoạn kiểm tra kích hoạt auto-login recovery:
     ```python
     if allow_auto_reconcile and _is_account_switcher_missing_expected_reason(last_reason):
         if _maybe_recover_missing_account_via_login(...):
             ...
     ```
   - Hàm `_is_account_switcher_missing_expected_reason` ban đầu chỉ kiểm tra:
     ```python
     return "account-switcher-missing-expected" in str(reason or "").lower()
     ```
   - Do đó, khi gặp `profile username still mismatched after switch` (tài khoản bị out phiên, session hỏng hoặc switcher không chuyển được), hệ thống **KHÔNG kích hoạt reconcile** mà ném thẳng ra lỗi dừng phiên `ExitStatus.MANUAL_NEEDED`.

---

## 3. Bản vá chuẩn (Canonical Fix)

### Điểm 1: Mở rộng `_is_account_switcher_missing_expected_reason`
Tại `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\feed_swipe_smoke.py` (dòng ~16220):
```python
def _is_account_switcher_missing_expected_reason(reason: str | None) -> bool:
    r = str(reason or "").lower()
    return "account-switcher-missing-expected" in r or "profile username still mismatched after switch" in r
```
*Tác dụng:* Khi switch thất bại do mismatch, hệ thống tự động kích hoạt `reconcile_tiktok_accounts.py` để login lại tài khoản mục tiêu và thử lại flow nuôi thay vì dừng phiên farm.

### Điểm 2: Tăng thời gian settle sau khi tap switch option
Tại `verify_and_switch_profile` (dòng ~16980):
```python
# Tăng thời gian chờ settle từ 2.0-3.0s lên 3.5-5.0s cho TikTok kịp transition & load profile mới
time.sleep(random.uniform(3.5, 5.0))
```

---

## 4. Quy trình kiểm chứng (Verification)
1. **Kiểm tra cú pháp:**
   ```bash
   python -m py_compile "D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\feed_swipe_smoke.py"
   ```
2. **Canary Test B4 trên máy bị alert:**
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
3. **Tiêu chuẩn pass:** `final_status: success`, hoàn thành số swipe test chỉ định, không còn blocker `profile username still mismatched after switch`.

---

## 5. Bài học điều phối (Coordinator & Worker)
- **Cấm tin tưởng mù quáng summary subagent:** Khi Worker 1 kết thúc báo cáo "đã phân tích xong", Coordinator phải chạy `git status --short` để xác nhận file có thực sự được patch trên đĩa hay không.
- **Xử lý dứt điểm khi Worker dính Analysis Paralysis:** Nếu worker bị chạm trần 35 turns mà chưa ghi đĩa, Coordinator cần dispatch worker tiếp theo với chỉ thị Scope Lock cực kỳ hẹp (Tier 1 Hotfix: chỉ định rõ file, số dòng, đoạn code thay thế và lệnh canary) để kết thúc task trong <= 10 turns.
