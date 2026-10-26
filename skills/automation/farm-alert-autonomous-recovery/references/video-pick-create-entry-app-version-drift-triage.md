# Video Pick Create Entry Unconfirmed & Cluster App Version Drift Triage

## 1. Triệu Chứng & Mẫu Cảnh Báo (Symptom & Alert Pattern)
Khi chạy ca nuôi feed kèm hook đăng video (`_run_upload_hook`) và nhận cảnh báo lỗi hàng loạt trên toàn cụm:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN - MÁY 201-280】
• Quy trình / Script: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
• Quy mô batch: 78 máy | Thành công: 0 | Thất bại: 78
• Signature: UploadScriptError:UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control
   - Tỷ lệ: ~95% (74/78 máy cùng dính 1 lỗi)
```

## 2. Phân Tích Nguyên Nhân Gốc (Root Cause Analysis)
1. **Lệch Phiên Bản App Giữa Các Cụm (Cluster Version Drift):**
   - Cụm Kibe (Máy 1–80) đã được cập nhật **TikTok v47.0.3** (`versionCode=470003`, 53 split APKs).
   - Cụm Admin (Máy 201–280) vẫn chạy **TikTok v46.6.3** (`versionCode=460603`).
2. **Cơ Chế Fail-Closed Của State Machine (`Tiktok-video`):**
   - Trong `scripts.tiktok_workflow.state_machine.py`, hàm `_find_bounded_create_button()` tìm nút `+` / Tạo video ở thanh điều hướng đáy màn hình theo whitelist nhãn cứng (`["+", "quay", "tạo", "create"]`) và giới hạn tọa độ chặt chẽ (tâm X ở 40%–60% chiều rộng, tâm Y >= 88% chiều cao).
   - Trên bản cũ v46.6.3, bố cục thanh điều hướng hoặc thuộc tính `content-desc` khác biệt khiến selector không khớp, dẫn tới kích hoạt fail-closed `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` để tránh tap nhầm.

## 3. Quy Trình Kiểm Chứng Hiện Trường O(1)
1. **Kiểm tra trạng thái máy qua inspect:**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
   Xác nhận máy đã fail-safe về `LauncherActivity` (Home screen) hoặc đang ở màn hình an toàn.
2. **Kiểm tra so sánh phiên bản TikTok giữa 2 máy Kibe và Admin:**
   ```bash
   # Máy Kibe (vd M1):
   python D:/Taadaa/tools/with_device_lock.py --machine 1 -- adb -s <serial_m1> shell dumpsys package com.ss.android.ugc.trill | grep versionName
   # Máy Admin (vd M201 qua socket 192.168.110.119:5037):
   python D:/Taadaa/tools/with_device_lock.py --machine 201 -- adb -H 192.168.110.119 -P 5037 -s <serial_m201> shell dumpsys package com.ss.android.ugc.trill | grep versionName
   ```

## 4. Quy Chuẩn Nâng Cấp An Toàn Giữ Nguyên Phiên (Safe Keep-Login Upgrade)
- **Kho APK chuẩn:** `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\` (gồm `base.apk` và 52 split APKs `split_df_*.apk`).
- **Lệnh cài đặt bắt buộc cờ `-r -d`:**
  ```bash
  adb install-multiple -r -d base.apk split_*.apk
  ```
- **KỶ LUẬT AN TOÀN TUYỆT ĐỐI:**
  - **CẤM TUYỆT ĐỐI** dùng `pm clear` hay gỡ cài đặt (`uninstall`): sẽ làm mất toàn bộ phiên đăng nhập (8 nick/máy x 78 máy = 600+ tài khoản).
  - Cờ `-r` (reinstall giữ nguyên data) kết hợp `-d` (cho phép downgrade nếu cần) đảm bảo 100% tài khoản trong Account Switcher được bảo toàn.
- **Hậu kiểm sau khi cài:**
  1. Kiểm tra lại `versionName=47.0.3` và số lượng split APKs >= 50.
  2. `am force-stop com.ss.android.ugc.trill` và đưa máy về Home (`input keyevent 3`).
  3. Kiểm tra canary 1 máy (M201) chạy thử luồng mở Switcher trước khi rollout diện rộng toàn bộ 78 máy Admin.
