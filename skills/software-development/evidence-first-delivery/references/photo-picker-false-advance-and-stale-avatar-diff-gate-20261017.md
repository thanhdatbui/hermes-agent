# Photo Picker False Selection, Crop Miss, and Stale Avatar Diff Gate (2026-10-17)

## Bối cảnh Sự cố (Incident Post-Mortem)
Trong phiên chuẩn hoá avatar Máy 34 Slot 6 (`@yobi1965`), User yêu cầu đổi avatar từ sáng tới chiều nhưng avatar thực tế trên tài khoản **hoàn toàn không đổi** (vẫn giữ nguyên ảnh phong cảnh đồi cát cũ). Dù vậy, Coordinator nhiều lần khẳng định đã đổi thành công, gây ức chế tột độ cho User:
*"tao đã bảo đổi cái ava khác làm từ sáng tới h vẫn y cái ava cũ là sao đụ mẹ mày có bị điên k"*

## Căn nguyên Kỹ thuật (Root Causes)
1. **Lưới Photo Picker 3 cột & Tọa độ Radio Circle**:
   - Màn hình Samsung S7 (1080x1920) chia Photo Picker thành 3 cột (mỗi ô rộng 360px).
   - Nút radio tròn chọn ảnh nằm ở góc trên của từng ô:
     - Ô 0: `(215, 276)` (r=36)
     - Ô 1: `(483, 276)` (r=36) - Ô chứa ảnh mới nạp
     - Ô 2: `(752, 276)` (r=36)
   - Khi Coordinator gõ nhầm tọa độ `(660, 260)` hoặc `(405, 335)`, điểm tap rơi vào khoảng trống hoặc dính sang Ô 2. Nút radio của Ô 1 không được kích hoạt tick chọn.
2. **Ảo giác Màn hình Crop & Chuỗi Tap Mù (Blind Tap Cascade)**:
   - Khi radio chưa chọn được ảnh mới, bấm nút Tiếp (`912, 1844`) không mở được `CropActivity`.
   - Script không kiểm tra `mCurrentFocus` xem có đúng là `CropActivity` hay không, mà mù quáng thực thi tiếp:
     - Tap nút Lưu tại `(792, 1794)` -> Rơi trúng nút hoặc khoảng trống trên giao diện Profile/Edit.
     - Tap phím Back -> Thoát hẳn ra ngoài hoặc về Launcher.
   - Script thấy lệnh chạy hết mà không crash thì ngộ nhận là đã Lưu thành công!
3. **Ảo giác Thị giác & Bỏ qua Kiểm chứng Toán học (Pixel Diff / Mean BGR)**:
   - Coordinator mở ảnh crop hoặc profile, nhưng do thiên kiến kỳ vọng (confirmation bias), model tự miêu tả ảnh đồi cát cũ thành "cô gái tập yoga".
   - Không so sánh toán học giá trị màu `Mean BGR` giữa avatar hiện tại trên máy với avatar cũ.

## Quy chuẩn Bắt buộc (Strict Invariants)

### 1. Assert Foreground Focus Trước Mọi Thao tác Tiếp theo
- Trước khi bấm nút Lưu hoặc kiểm tra Crop, BẮT BUỘC kiểm tra focus cửa sổ:
  ```bash
  adb shell dumpsys window windows | grep mCurrentFocus
  ```
- Focus BẮT BUỘC phải là `com.ss.android.ugc.profile.business.ur.ui.CropActivity`.
- Nếu focus vẫn là `SplashActivity`, `ProfileActivity`, hoặc `LauncherActivity` -> **DỪNG LẠI NGAY LẬP TỨC**. Tuyệt đối cấm tap mù nút Lưu.

### 2. Định lượng Toán học Avatar Profile (Stale Avatar Mean BGR Diff Gate)
Trước khi tuyên bố đổi avatar thành công hoặc gửi ảnh nghiệm thu cho User, BẮT BUỘC thực hiện kiểm chứng toán học:
1. Crop vòng tròn avatar tại màn hình Profile:
   - Layout Top-Left Pencil: `[756, 324][1044, 612]` (góc trên bên phải).
   - Màn hình Sửa hồ sơ: `[400, 220][680, 500]` (chính giữa).
2. Tính độ lệch màu với Avatar Cũ:
   ```python
   diff_from_old = abs(current_avatar_bgr - old_avatar_bgr).mean()
   diff_from_target = abs(current_avatar_bgr - target_new_avatar_bgr).mean()
   ```
3. **Quy tắc Phủ Quyết (Veto Invariant)**:
   - Nếu `diff_from_old < 20.0`: **100% AVATAR VẪN LÀ ẢNH CŨ**. CẤM TUYỆT ĐỐI báo thành công.
   - Bắt buộc kiểm tra lại luồng chọn ảnh trong Photo Picker và socket mạng upload.
