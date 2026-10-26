# Cross-Cluster TikTok App Version Parity & Safe Keep-Login Upgrade

## 1. Triệu Chứng & Dấu Hiệu Lệch Cụm (Symptom & Cluster Drift)
Khi chạy ca nuôi/đăng video trên Farm phân tán (Cụm Kibe M1-80 vs Cụm Admin M201-280):
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN - MÁY 201-280】
• Quy trình / Script: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
❌ Signature: UploadScriptError:UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control
   - Tỷ lệ trên toàn batch: 94.9% (74/78 máy lỗi đồng loạt)
```

## 2. Phân Tích Nguyên Nhân Gốc (Root Cause)
- **Lệch phiên bản ứng dụng giữa các cụm (Cluster Version Drift):**
  - Cụm Kibe đã được nâng cấp lên **TikTok v47.0.3** (`versionCode=470003`, 53 split APKs).
  - Cụm Admin vẫn kẹt ở bản cũ **TikTok v46.6.3** (`versionCode=460603`, 55 split APKs).
- **Cơ chế fail-closed của State Machine (`Tiktok-video/scripts/tiktok_workflow/state_machine.py`):**
  - Hàm `_find_bounded_create_button()` tìm nút `+` / tạo video ở thanh điều hướng đáy với tiêu chuẩn nghiêm ngặt: `clickable=true`, `content-desc` hoặc `text` thuộc `["+", "quay", "tạo", "create"]`, nằm ở giữa màn hình (40% - 60% width) và sát đáy (>= 88% height).
  - Khác biệt cấu trúc giao diện giữa v46.6.3 và v47.0.3 khiến nhánh nhận diện thất bại. Nhánh phục hồi `_recover_video_pick_create_entry()` kích hoạt chốt chặn an toàn `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]` và đưa thiết bị về `LauncherActivity` để chống thao tác sai.

## 3. Quy Trình Nâng Cấp Chuẩn Hóa An Toàn (Safe Keep-Login Upgrade Workflow)

### A. Kho APK Chuẩn Hóa (APK Bank)
- Toàn bộ split APKs của bản TikTok đồng bộ nằm tại:
  `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\` (gồm `base.apk` và các `split_*.apk`, tổng ~53 files, ~260MB).

### B. Lệnh Cài Đặt Giữ Phiên Bắt Buộc
- **CÚ PHÁP BẮT BUỘC:**
  ```bash
  adb -H 192.168.110.119 -P 5037 -s <serial> install-multiple -r -d base.apk split_*.apk
  ```
- **QUY TẮC SỐNG CÒN:**
  - BẮT BUỘC dùng `-r -d` (reinstall, keep data/allow downgrade or same-version update).
  - CẤM TUYỆT ĐỐI `pm clear` hay `pm uninstall` — làm mất toàn bộ 8 tài khoản đăng nhập trên mỗi máy farm.
  - Sau khi cài: gọi `am force-stop com.ss.android.ugc.trill` và `input keyevent 3` (HOME) để trả máy về màn hình chính.

### C. Cơ Chế Kết Nối Cụm Admin
- Dàn máy Admin (M201+) nằm trên host remote qua ADB server socket:
  - Host: `192.168.110.119`, Port: `5037`.
  - Thiết lập child subprocess: `env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"` hoặc truyền `-H 192.168.110.119 -P 5037` trực tiếp vào lệnh ADB.

## 4. Các Cạm Bẫy Vận Hành Kỹ Thuật (Operational Pitfalls)

### A. Bẫy Nghẽn Băng Thông USB / ADB Socket Khi Nâng Cấp Đồng Loạt (Bandwidth Choke)
- **Sai lầm:** Chạy 20–30 worker đồng thời tải 260MB APK xuống hàng chục máy qua 1 USB hub / switch mạng nội bộ.
- **Hậu quả:** ADB client nghẽn pipe socket, timeout 240s-300s hàng loạt (`FAIL_PUSH`, `connect error for fin`, thiết bị rớt sang `offline`).
- **Quy chuẩn:** Giới hạn concurrency tối đa **6 – 8 workers** song song. Băng thông ổn định (~15-20MB/s/worker) giúp toàn bộ cụm hoàn tất an toàn trong 15–20 phút mà không gây rớt kết nối.

### B. Bắt Buộc Device Lock Trước Khi Cài Đặt
- Mọi thao tác can thiệp thiết bị (kể cả canary hay batch) BẮT BUỘC giữ `operator_device_lock` hoặc bọc qua:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
  ```

### C. Quy Trình Canary Trước Rollout
1. Nâng cấp thử nghiệm duy nhất trên 1 máy đại diện (ví dụ M201).
2. Kiểm tra `dumpsys package com.ss.android.ugc.trill`:
   - Xác nhận `versionName=47.0.3` và split count >= 50.
3. Khởi chạy TikTok 5–8s, chụp màn hình xác nhận phiên đăng nhập và tài khoản vẫn hiển thị bình thường.
4. Sau khi Canary đạt chuẩn mới bắt đầu rollout toàn fleet.
