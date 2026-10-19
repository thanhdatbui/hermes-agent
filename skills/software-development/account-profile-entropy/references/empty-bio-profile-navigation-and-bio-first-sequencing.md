# Empty-Bio Layout Sequencing & Profile Edit Activation Invariant

## 1. Bối Cảnh Hiện Trường Thực Tế (Sự Cố Máy 76 - 19/10/2026)
Trên TikTok v47 chạy trên Samsung S7 (1080x1920), đối với các tài khoản chưa từng cài Bio (bio trống):
- TikTok ẩn hoàn toàn nút văn bản "Sửa hồ sơ" và "Chia sẻ hồ sơ" bên dưới các chỉ số follow.
- Dưới các chỉ số follow chỉ xuất hiện 2 chip ngang hàng:
  * Chip 1: `+ Thêm tiểu sử` (`[75, 667][381, 705]`, tâm `(228, 686)`).
  * Chip 2: `@ Tài khoản của tôi nói về...` (`[431, 671][990, 709]`).
- Tọa độ `(870, 558)` (vốn là bút chì trên một số layout khác) nằm trúng vào vùng avatar/bong bóng trạng thái bên phải, mở ra popup **"Thêm vào Nhật ký"** (`state=UNKNOWN`: *Thêm vào Nhật ký / Ảnh / Video*). Nếu script cố bấm `(870, 558)` sẽ kẹt vòng lặp mở popup -> Back -> mở popup dẫn đến `ABORT: vuot qua 35 buoc`.

---

## 2. Quy Chuẩn Thứ Tự Thực Thi Bắt Buộc (Bio-First Sequencing)

Khi thực hiện đổi tên và nạp bio trên tài khoản chưa có Bio:
1. **Kiểm tra sự tồn tại của nút "Sửa hồ sơ"**:
   ```python
   btn = find_box(boxes, r"(sua|chinh sua|edit)\s*(h[o0]|profile)")
   ```
2. **Nếu CÓ `btn`**: Tap `center(btn)` để vào thẳng `EDIT_PROFILE`.
3. **Nếu KHÔNG CÓ `btn` (Profile trống Bio)**:
   - **BƯỚC 1: Nạp Bio trước qua chip `+ Thêm tiểu sử`**:
     ```python
     elif TARGET_BIO and not bio_saved:
         tieu_su = find_box(boxes, r"tieu su|them tieu su|\+ them")
         if tieu_su:
             xy = center(tieu_su) # Tọa độ thực tế ~(228, 686)
             print(f"Chưa có 'Sửa hồ sơ', tap '+ Thêm tiểu sử' tại {xy} để mở Bio")
             tap(xy, 4)
             continue
     ```
   - Chip `+ Thêm tiểu sử` mở trực tiếp màn hình `BIO_EDIT` (nhận diện qua `0/160` hoặc `tiểu sử` không có `follower/thích`).
   - Nhập Bio tiếng Việt có dấu qua Base64 UTF-8 broadcast của AdbKeyboard (`ADB_KEYBOARD_INPUT_TEXT`), tap "Lưu" `(980, 140)`.
   - Đánh dấu `bio_saved = True` và quay về màn hình Hồ sơ (`PROFILE`).
4. **BƯỚC 2: Đổi Tên sau khi nút "Sửa hồ sơ" đã lộ diện**:
   - Khi đã có Bio, TikTok tự động tái cấu trúc giao diện Profile: dòng Bio mới xuất hiện, đồng thời nút bấm văn bản **"Sửa hồ sơ"** chính thức lộ diện tại `y ≈ 865` (hoặc `y ≈ 985`).
   - Lúc này `find_box(boxes, r"(sua|chinh sua|edit)\s*(h[o0]|profile)")` sẽ bắt trúng nút `Sửa hồ sơ`, mở màn hình `EDIT_PROFILE`.
   - Trong `EDIT_PROFILE`, chạm dòng "Tên", xóa tên cũ, gõ tên mới, xác nhận dialog 7 ngày và hoàn tất.

---

## 3. Heuristic Phân Biệt Tọa Độ Trên Samsung S7 v47

| Thành phần UI | Bounding Box thực tế | Tọa độ tâm chuẩn | Lưu ý |
| :--- | :--- | :--- | :--- |
| **Dòng Tên hiển thị (Cleora)** | `[38, 295][254, 348]` | `(146, 320)` | CẤM tap vì là header mở Account Switcher |
| **Username (@cleorbgtwyr)** | `[38, 378][295, 413]` | `(166, 395)` | Dòng định danh |
| **Stats Follow/Like** | `[37, 544][540, 573]` | `(288, 558)` | Hàng chỉ số |
| **Chip `+ Thêm tiểu sử`** | `[75, 667][381, 705]` | `(228, 686)` | **Dùng để vào `BIO_EDIT` khi chưa có bio** |
| **Nút "Sửa hồ sơ" (khi có bio)** | `[36, 825][520, 909]` | `(278, 867)` | Hiện ra sau khi đã lưu Bio |
| **Vùng Avatar (bên phải)** | `[780, 260][1020, 500]` | `(900, 380)` | CẤM tap vì mở popup "Thêm vào Nhật ký" |
