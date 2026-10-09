# TikTok Registration Operations (Tiktok_Reg)

Vận hành batch đăng ký TikTok (reg) — detect target mail chưa reg, giành lock máy, chạy _run_all_targets.py, resume tại chỗ, debug DOB/OTP blockers. Dùng khi user yêu cầu "reg tiktok", "máy nào thiếu mail chưa reg", hoặc batch FAILED với lỗi DOB/OTP.

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪNG chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

> 📎 Refs: `token-otp-graph-reader-20260817.md` · `fresh-machine-signup-v2-20260817.md` · `magic-link-graph-fallback-20260817.md` · `parasite-account-reconcile-and-deferred-tracking-sync-20260917.md` (OTP: Back xóa code cũ; email-form type+Tiếp tục; mất ký tự=OCR ảo; magic-link Graph href; đối soát XML máy thật tìm nick ký sinh; auto-sync deferred tracking Excel)

⚠️ **NO-MANUAL-TAP bắt buộc:** script chạy đến hết, KHÔNG can thiệp tay giữa chừng.

---

## 📌 QUY TẮC CỐT LÕI (CORE RULES)

1. **Detect target**: Dùng `python _detect_clean.py` để lấy danh sách máy thiếu mail và mail chưa reg.
2. **Preflight Live Check**: Trước khi chạy batch, bắt buộc lọc mail DIE qua `checkmail.live` (`gmail_preflight_filter.py`). Mail DIE phải dọn kép khỏi file nguồn và gỡ khỏi S7.
3. **Phát hiện trần 8 tài khoản (MACHINE_FULL_8_ACCOUNTS)**:
   - TikTok obfuscate resource-id của danh sách tài khoản trong switcher thành `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]`.
   - Khi `_acc_count >= 8`, nút "Thêm tài khoản" bị ẩn hoàn toàn. Bắt buộc raise `MACHINE_FULL_8_ACCOUNTS` và bấm Back + Home thoát sheet.
4. **Auto-Sync Deferred Tracking vào Excel**:
   - Chạy batch dùng `--defer-tracking-write` để tránh xung đột file Excel.
   - Cuối batch `_run_all_targets.py` tự động gom các file `result_json` thành công và gọi `write_deferred_results_sequential` để ghi khóa tuần tự vào `taikhoan_dat_v2_updated .xlsx`.
   - Nếu dòng `tracking_row`/`tik` bị trôi lệch, writer tự động fallback tìm dòng trống hợp lệ tiếp theo của máy (`resolve_tracking_slot`).
5. **Đối soát Nick Ký sinh (Parasite Accounts)**:
   - CẤM chỉ đối soát nội bộ trên Excel.
   - BẮT BUỘC dump UI XML màn hình Switcher trên máy thật để so khớp ngược về Excel. Nick nào có trên máy thật nhưng không thuộc danh sách của máy đó trên Excel là nick ký sinh -> Dùng `watchdog_idle_parasite_reconcile.py` logout đơn lẻ khi máy rảnh.

---

## 🛠️ CÁC LỆNH VẬN HÀNH CHÍNH

- **Detect máy thiếu**:
  ```bash
  python _detect_clean.py
  ```
- **Chạy batch reg**:
  ```bash
  python _run_all_targets.py --max-workers 6 --max-targets 30
  ```
- **Sync thủ công các file deferred tracking JSON cũ vào Excel**:
  ```bash
  python scripts/apply_deferred_tracking_results.py <path_to_json>
  ```
- **Canh logout nick ký sinh khi máy rảnh**:
  ```bash
  python D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py
  ```
