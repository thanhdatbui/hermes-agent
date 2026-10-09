# Bẫy Cache UI XML Cũ Trong /data/local/tmp & Cơ Chế Auto-Login Recovery Timeout Trong Batch (2026-09-24)

## 1. BẪY CACHE UI XML CŨ TRONG `/data/local/tmp` (STALE DUMP COLLISION)

### Hiện tượng & Sự cố thực tế (User Correction 24/09/2026)
- **Tình huống:** Khi nhận cảnh báo Farm Alert Máy 1 bị lỗi, Coordinator chạy kiểm tra hiện trường:
  ```bash
  adb shell uiautomator dump /data/local/tmp/uidump.xml
  adb pull /data/local/tmp/uidump.xml D:/Taadaa/reports/m1_current.xml
  ```
- **Hậu quả:** Lệnh `uiautomator dump` không ghi đè thành công (do màn hình chuyển trạng thái hoặc service bận), lệnh `pull` sau đó đã kéo lại một file `uidump.xml` cũ rác từ phiên cấu hình Wi-Fi trước đó. Agent đọc file XML này và vội vã báo cáo: *"Hiện trạng tức thời của Máy 1: Đang bị che bởi popup kết nối Wi-Fi mạng kibe 1 (yêu cầu nhập mật mã)"*.
- **Phản ứng của User:** *"máy 1 t có thấy dính pop up wifi gì đâu???"*. Thực tế màn hình thiết bị đang ở Launcher HOME bình thường!

### Kỷ luật Thẩm định Hiện trường ADB Bắt Buộc (Invariant)
1. **Xóa sạch trước khi Dump hoặc dùng Unique Filename:**
   - TUYỆT ĐỐI CẤM dùng static path `/data/local/tmp/uidump.xml` mà không xóa trước.
   - Bắt buộc xóa trước: `adb shell rm -f /data/local/tmp/uidump.xml && adb shell uiautomator dump /data/local/tmp/uidump.xml`.
   - Tốt nhất là dùng timestamp: `TMP_XML="/data/local/tmp/dump_$(date +%s).xml"`.
2. **Kiểm tra Return Code & Stdout của `uiautomator dump`:**
   - Lệnh thành công bắt buộc phải in ra: `UI hierachy dump: /data/local/tmp/...`. Nếu stdout rỗng hoặc báo lỗi -> KHÔNG ĐƯỢC pull file.
3. **Cross-Check 3 Lớp Bắt Buộc (Tam Giác Chứng Minh):**
   - Lớp 1: `mCurrentFocus` từ `dumpsys window windows | grep -E 'mCurrentFocus'`.
   - Lớp 2: Ảnh `screencap` thực tế (chụp bằng `screencap -p`).
   - Lớp 3: UI XML dump.
   *Nếu mCurrentFocus là LauncherActivity nhưng XML lại là Dialog Wi-Fi/Settings -> ĐÂY LÀ XML RÁC (STALE CACHE). CẤM TUYỆT ĐỐI phát ngôn khi chưa khớp giữa Focus và XML.*

---

## 2. TRIAGE BATCH ALERT & CƠ CHẾ AUTO-LOGIN RECOVERY TIMEOUT

### Câu hỏi phổ biến của User
*"Văng tài khoản tại sao không gọi hàm tiktok login chạy login lại?"*

### Cơ chế kỹ thuật ngầm trong Runner Batch (`feed_swipe_smoke.py`)
1. **Runner ĐÃ tự động gọi cứu phiên:**
   Khi kiểm tra Account Switcher trước phiên lướt feed mà phát hiện thiếu tài khoản mục tiêu (`account-switcher-missing-expected`), runner tự động kích hoạt:
   ```python
   # feed_swipe_smoke.py -> _trigger_auto_login_recovery
   fast_cmd = [
       python_exe,
       "D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py",
       machine_id,
       "--email", expected_account,
       "--ss",
       "--allow-parent-lock"
   ]
   ```
2. **Nguyên nhân thất bại trong batch: Trúng trần Timeout bảo vệ Fleet!**
   - Trong batch chạy đồng loạt 160 máy, để tránh 1 máy bị kẹt làm treo toàn bộ worker thread, runner mẹ đặt trần `fast_login_timeout_seconds = 180.0` (3 phút).
   - Quy trình login TikTok: Nhập ID -> Tiếp tục -> Nhập Password -> Xác minh challenge thiết bị / Captcha (`[auth] round 1/6`, `round 2/6`).
   - Nếu mạng lag hoặc TikTok challenge kéo dài quá 180s, runner mẹ bắt buộc phải kill subprocess login (`timed out after 180.0 seconds`).
   - Fallback tiếp theo sang `reconcile_tiktok_accounts.py` cũng bị timeout 300s, dẫn đến máy bị chốt trạng thái `manual-needed`.

### Quy trình Điều phối & Cứu phiên Ngoài Batch (Coordinator Protocol)
1. **Kiểm tra `log.jsonl` tại bước `auto_login_recovery` trước khi trả lời:**
   - Trích xuất log xem script login đã chạy đến bước nào (nhập email, nhập pass hay kẹt captcha/challenge).
   - Báo cáo rõ ràng cho User: Hệ thống đã tự động login nhưng bị timeout 180s do trần bảo vệ batch.
2. **Dispatch Worker Cứu phiên Độc lập (Uncapped Timeout):**
   - Khi chạy cứu phiên cho 1 máy đơn lẻ ngoài batch, dispatch worker chạy trực tiếp `tiktok_login_v1.py` với budget thời gian thoải mái (không bị bóp timeout 180s):
     ```bash
     cd /d/Taadaa/Tiktok_Reg
     env -u PYTHONPATH "D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" tiktok_login_v1.py <M> --email <id> --ss
     ```
   - Nghiệm thu bắt buộc: Account Switcher đủ 8 nick active trước khi teardown.
