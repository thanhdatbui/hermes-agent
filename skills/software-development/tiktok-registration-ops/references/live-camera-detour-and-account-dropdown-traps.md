# Xử Lý Bẫy Màn Hình Phát LIVE / Camera Khi Mở Account Dropdown (24/09/2026)

## 1. Hiện Tượng (Case Study Máy 69)
- **Triệu chứng:** Runner đăng ký TikTok `social_reg_v1.py` thất bại tại bước `[03_dropdown] Khong mo duoc account dropdown`.
- **Hiện trường XML & Log (`fail_03_account_dropdown_014945.xml`):**
  - Khi cố gắng mở tab Hồ sơ hoặc dismiss các popup xuất hiện sau khi mở app, app TikTok bị chuyển hướng hoặc bật sang màn hình **Phát LIVE / Camera** (`ttlive_preview_surfaceview`).
  - Trong UI XML xuất hiện:
    * `com.ss.android.ugc.trill:id/eaw` (Button "Quay lại màn hình trước" tại bounds `[18,72][150,204]`).
    * Màn hình có RecyclerView các chế độ: "Máy ảnh thiết bị", "Trò chơi di động" (`com.ss.android.ugc.trill:id/z2q`).
- **Defect Trong Dismiss Logic:**
  - Script nhận diện nhầm chuỗi `'Trò chơi di động'` hoặc button text là mục tiêu cần bấm dismiss, dẫn đến vòng lặp bấm liên tục vào `(567, 1666)` (hoặc `(971, 1666)`).
  - Vì mỗi lần bấm vào tab "Trò chơi di động" thì màn hình LIVE vẫn giữ nguyên, script rơi vào vòng lặp vô tận cho đến khi timeout và văng exception `[03_dropdown] Khong mo duoc account dropdown`.

## 2. Quy Tắc Thoát Bẫy Chuẩn Xác (Live Exit Invariant)
1. **Phát hiện màn hình LIVE:**
   - Kiểm tra sự tồn tại của `ttlive_preview_surfaceview`, `id/ttlive_text`, hoặc button quay lại `id/eaw` với desc "Quay lại màn hình trước".
2. **Hành động dứt điểm:**
   - **Tuyệt đối CẤM** tap vào các node text tab/chế độ như `'Trò chơi di động'`, `'Máy ảnh thiết bị'`, `'Phát LIVE'` trong khối dismiss popup.
   - BẮT BUỘC tap vào button quay lại `id/eaw` tại `(84, 138)` (hoặc bounds `[18,72][150,204]`).
   - Nếu sau 1 lần tap `id/eaw` mà màn hình LIVE vẫn chưa đóng, phát lệnh `keyevent 4` (KEYCODE_BACK) để thoát dứt điểm về trang chủ/profile.
