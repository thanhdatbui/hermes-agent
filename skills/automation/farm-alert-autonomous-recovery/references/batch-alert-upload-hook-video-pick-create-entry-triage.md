# Batch Alert: UploadHook Video Pick Create Entry Unconfirmed Triage

## 1. Triệu Chứng & Mẫu Cảnh Báo (Symptom & Alert Pattern)
Khi nhận được cảnh báo batch diện rộng trên Farm:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN / KIBE】
• Quy trình / Script: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
• Tỷ lệ thất bại toàn batch: 90% - 100%
❌ Signature: UploadScriptError:UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control
```

## 2. Phân Tích Nguyên Nhân Gốc (Root Cause Analysis)
1. **Liên repo Cross-Hook (Feed Session -> Upload Hook):**
   - Dù tên tiến trình là `Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)`, sau khi hoàn tất phiên lướt feed, script `python_runner/flows/multi_machine_feed_session.py` sẽ tự động gọi `_run_upload_hook()` để dispatch tiến trình upload video (`scripts.tiktok_workflow` trong repo `Tiktok-video`).
   - Lỗi phát sinh từ `UploadHook`, không phải từ logic lướt feed.

2. **Cơ chế Fail-Closed tại State Machine (`Tiktok-video`):**
   - Trong `state_machine.py`, khi vào bước chọn video đăng (`video_pick`), hàm `_find_bounded_create_button()` tìm nút `+` (Create) ở thanh điều hướng đáy.
   - Điều kiện kiểm tra cực kỳ chặt chẽ:
     - `clickable == "true"`
     - `content-desc` hoặc `text` nằm trong whitelist cứng: `["+", "quay", "tạo", "create"]`.
     - Tọa độ tâm `center_x` phải nằm trong khoảng `40% - 60%` chiều ngang màn hình.
     - Tọa độ tâm `center_y` phải `>= 88%` chiều cao màn hình.
   - Khi TikTok cập nhật phiên bản hoặc thay đổi nhãn/layout (hoặc màn hình camera/action sheet che khuất không có nhãn đúng chuẩn), script thử nhánh cứu hộ `_recover_video_pick_create_entry()`.
   - Nếu sau khi recapture màn hình vẫn không tìm thấy nút hợp lệ, script kích hoạt dừng an toàn `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`, đưa máy về `LauncherActivity` (Home screen) để tránh click mù gây sai lệch tài khoản.

## 3. Quy Trình Kiểm Chứng Hiện Trường O(1)
1. **Chạy inspect nhanh máy đại diện:**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
2. **Đối soát 3 chỉ số an toàn:**
   - Focus hiện tại là `LauncherActivity` (Home screen) -> Xác nhận máy đã fail-safe dọn dẹp sạch, không bị treo app.
   - Màn hình `OFF (Sleep/Dozing)` -> Máy không bị sáng màn hình đốt pin/nhiệt độ.
   - Wi-Fi IP và Proxy vẫn kết nối bình thường.
3. **Phân tách lỗi đơn lẻ (P0) đi kèm:**
   - Nếu có máy dính `ACCOUNT_SWITCHER_FAILED: ACCOUNT_MISSING` (như M261): máy này kẹt ở `SplashActivity` hoặc Switcher do thiếu nick, cần chạy reconcile nạp bù nick độc lập với lỗi create control của batch.

## 4. Kỷ Luật Phản Hồi Operator (Bottom-line First)
- **Khẳng định ngay bản chất lỗi:** Lỗi không phải do treo máy hay chết proxy diện rộng, mà do `UploadHook` cuối ca lướt feed không nhận diện được nút tạo video/bottom-centre create control trên giao diện TikTok, dẫn đến cơ chế fail-closed tự động giải phóng app và đưa toàn bộ máy về Home screen.
- **Tách bạch 2 luồng xử lý:**
  - Luồng 1 (74 máy UI control): Cập nhật selector/whitelist nhãn trong `_find_bounded_create_button` và canary test 1 máy.
  - Luồng 2 (Máy thiếu nick P0): Nạp bù tài khoản vào Switcher qua `reconcile_tiktok_accounts.py`.
