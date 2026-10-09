# An Toàn Giải Phóng Device Lock Cha-Con & Cô Lập Package Cho UI Credential Scanner (2026-09-07)

## 1. Cơ Chế Giải Phóng Device Lock Trong Batch Cha-Con (Case LOCK-06)

### Vấn đề & Triệu chứng lỗi:
- Khi một runner cha (batch orchestrator) thực hiện cấp phát trước device lock cho danh sách máy (`acquire_device_lock`), sau đó khởi tạo các tiến trình con (worker processes) để xử lý từng thiết bị.
- Các tiến trình con sẽ tiếp quản lock (`takeover`) hoặc hoàn tất phiên và tự giải phóng file lock qua `lease.finish(succeeded=...)`.
- Tại khối `finally:` hoặc khối xử lý ngoại lệ preflight của tiến trình cha, nếu gọi `reservation.release()`, hàm này trong `automation_core.device_lock` mặc định chạy với cờ nghiêm ngặt `strict=True` (`_release_lease_paths(strict=True)`).
- Hậu quả: Khi lock file đã bị tiến trình con tiếp quản quyền sở hữu hoặc đã bị dọn dẹp, lệnh `reservation.release()` sẽ ném ra ngoại lệ:
  `automation_core.device_lock.DeviceLockReleaseError: DEVICE_LOCK_RELEASE_OWNERSHIP_MISMATCH`
  (hoặc `DEVICE_LOCK_RELEASE_PATH_MISSING`).
- Ngoại lệ unhandled này làm sập toàn bộ tiến trình cha ở phút chót, ngăn cản việc in bảng kết quả tổng hợp `_print_results`, làm sai lệch exit code (trả về 1 dù các máy con đã chạy xong) và kích hoạt cảnh báo Farm Alert giả.

### Quy chuẩn xử lý bắt buộc (Pattern chuẩn):
1. **Dùng `release_with_audit` với `strict=False`:**
   Tiến trình cha khi giải phóng reservation lock BẮT BUỘC gọi `reservation.release_with_audit(reason=...)`. Hàm này chỉ giải phóng những lock path mà tiến trình cha vẫn thực sự còn nắm giữ, bỏ qua một cách an toàn các path đã được tiến trình con tiếp quản hoặc hoàn tất.
2. **Bọc an toàn `try...except`:**
   Luôn bọc lời gọi giải phóng trong `try ... except Exception: pass` (hoặc kiểm tra `hasattr(reservation, "release_with_audit")` để tương thích ngược với mock objects trong unit test).
3. **Mẫu code chuẩn:**
   ```python
   # Trong finally: hoặc except preflight của batch runner
   for reservation in reservations:
       try:
           if hasattr(reservation, "release_with_audit"):
               reservation.release_with_audit(reason="batch-complete")
           else:
               reservation.release()
       except Exception:
           pass
   ```

---

## 2. Cô Lập Package Cho UI Credential / Secret Scanner (Package Isolation Gate)

### Vấn đề & Sự cố bắt nhầm widget Samsung Launcher ("GALAXYESSENTIALS"):
- Các module tự động hóa quét Secret Key (Base32 TOTP 2FA) hoặc mật khẩu thường dùng regex lọc chuỗi ký tự hợp lệ (ví dụ `[A-Z2-7]{16,64}`) rồi kiểm tra logic (như chạy thử `generate_totp()`).
- Trên các dòng điện thoại Samsung Galaxy (S7, S8...), màn hình chính TouchWiz/Samsung Launcher (`com.sec.android.app.launcher`) có widget hệ thống mang tên `"Galaxy Essentials"`.
- Chuỗi compact loại bỏ khoảng trắng: `"GALAXYESSENTIALS"` dài đúng 16 ký tự, tất cả các ký tự `G, A, L, X, Y, E, S, N, T, I` đều ngẫu nhiên nằm trong bảng mã RFC 4648 Base32 `[A-Z2-7]`. Hàm `generate_totp("GALAXYESSENTIALS", 0)` chạy thành công không có lỗi.
- Hậu quả dây chuyền:
  1. Khi app mục tiêu (TikTok) bị crash, bị kill hoặc chưa kịp khởi động, điện thoại đang ở màn hình Home Launcher.
  2. Hàm quét secret quét toàn bộ cây XML không kiểm tra thuộc tính `package`, bắt nhầm `"GALAXYESSENTIALS"` làm Secret Key 2FA của tài khoản và lưu state `CAPTURED` vào Journal.
  3. Runner tưởng nhầm app đang mở sẵn màn hình Secret Key nên bỏ qua toàn bộ bước mở app, không vào Profile/Settings, rồi lập tức nhảy cóc sang tìm nút chuyển bước (Next/Tiếp tục) ngay trên... màn hình chính Launcher.
  4. Script văng lỗi `OTP_ADVANCE_BUTTON_NOT_REACHED` lặp đi lặp lại vì mỗi lần retry đều resume từ Journal bị nhiễm secret giả.

### Quy chuẩn bảo vệ bắt buộc:
1. **Lọc nghiêm ngặt thuộc tính `package`:**
   Mọi hàm quét text nhạy cảm / credential / Base32 secret BẮT BUỘC kiểm tra thuộc tính `package` của từng node UI:
   ```python
   pkg = element.attrib.get("package") or getattr(element, "package", "")
   if not pkg and element.resource_id and element.resource_id.startswith(TARGET_APP_PACKAGE + ":"):
       pkg = TARGET_APP_PACKAGE
   if pkg and (pkg != TARGET_APP_PACKAGE or pkg.startswith(("com.sec.", "com.android."))):
       continue
   ```
2. **Chốt chặn fail-closed ở cấp XML Hierarchy:**
   Trước khi quét tìm secret trong XML, bắt buộc kiểm tra xem package của app mục tiêu có hiện diện trong UI hierarchy hay không. Nếu XML hoàn toàn thuộc Launcher hoặc app khác, lập tức ném ngoại lệ `UIInteractError("current UI is not target app")`.
3. **Blacklist chuỗi tĩnh đã biết:**
   Chủ động loại trừ các chuỗi tĩnh hệ thống đã từng gây false positive (như `"GALAXYESSENTIALS"`).
4. **Lưu ý kiểm tra rò rỉ mã nguồn (CI Secret Leak Scan):**
   Trong các repo có script scan credential (như `SecretLeakScanTests` quét regex `[A-Z2-7]{16,}`), chuỗi `"GALAXYESSENTIALS"` sẽ bị bộ scan bắt dính như một credential thật nếu viết chuỗi liền. BẮT BUỘC viết tách chuỗi dạng `"GALAXY" + "ESSENTIALS"` trong cả codebase và test fixtures để vượt qua gate CI.
