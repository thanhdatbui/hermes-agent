# Gmail Switcher Avatar Bento Misclick Pitfall & Add Account Fallback Guard

## Hiện tượng & Nguyên nhân gốc (Root Cause)
Khi tự động hoá quy trình đăng ký/thêm tài khoản Gmail (`gmail_reg_v10.py` trên Samsung S7):
- Tại bước `[03_add]`, script mở Gmail account switcher (bento menu) để bấm **"Thêm tài khoản khác"** (`Add another account`).
- Khi menu chưa cuộn hoặc text không xuất hiện trong UI XML, logic fallback `find_add_account_card_in_switcher()` cố gắng tìm card dựa trên toạ độ:
  ```python
  # LỖI TIỀM ẨN: Lọc y >= 300 quá nông
  if 300 <= y <= 1850 and x <= 700 and not is_storage:
      fallback_candidates.append(card)
  ```
- Trên nhiều màn hình S7 / Google Play Services, icon ảnh đại diện / Avatar profile chip của tài khoản đang chọn nằm ở khoảng `bounds=[408,204][672,468]`, toạ độ tâm `(540, 336)`.
- Giá trị `y = 336 >= 300` khiến hàm fallback nhận nhầm avatar chip thành card "Thêm tài khoản".
- Cú tap này mở màn hình **"Thêm ảnh hồ sơ"** (`com.google.android.gms` / `octarine_webview_frame` / "Duyệt xem hình minh hoạ").
- Hệ quả: Bước kế tiếp `[04_google]` tìm provider Google trên màn hình chọn ảnh hồ sơ -> timeout 10 lần -> văng lỗi `[04_google] Không chọn được provider Google` (`failed_other`).

## Giải pháp chuẩn hoá (Best Practice Guard)
1. **Nâng ngưỡng toạ độ fallback**:
   - Card "Thêm tài khoản khác" trong bento menu luôn nằm ở nửa dưới danh sách tài khoản, tối thiểu `y >= 600` (hoặc `y1 >= 500`).
   - CẤM nhận các node có `y < 600` làm card fallback trong switcher.
2. **Loại trừ Avatar Bounds**:
   - Các node có tỷ lệ khung hình vuông nhỏ (`abs(width - height) < 20` và `width < 300`) ở vùng header `y < 500` là avatar/camera icon, tuyệt đối không tap.
3. **Phát hiện sớm màn hình ảnh hồ sơ**:
   - Nếu phát hiện XML chứa `"Thêm ảnh hồ sơ"`, `"Duyệt xem hình minh hoạ"`, hoặc `com.google.android.gms:id/octarine_webview_swipe_refresh_layout`, script phải lập tức nhấn `KEYCODE_BACK` để quay lại bento menu thay vì chờ provider Google.
