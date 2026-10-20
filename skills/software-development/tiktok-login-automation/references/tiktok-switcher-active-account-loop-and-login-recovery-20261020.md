# TikTok Account Switcher Active Account Loop Trap & Missing Recovery

## 1. Cơ Chế Missing Account Auto-Recovery Trong Runner Đổi Tên
- Khi runner đổi tên (`do_rename_canonical_runner.py`) mở khay Switcher cuộn hết trang mà không thấy username đích (`@{TARGET_USER}`):
  * **CẤM:** Dừng lại báo lỗi văng hoặc crash im lặng.
  * **BẮT BUỘC:** Kích hoạt ngay canonical login runner:
    ```bash
    python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <TARGET_USER> --ss --allow-parent-lock
    ```
  * Sau khi login thành công (exit code 0), chờ 5s nạp phiên rồi tiếp tục flow đổi tên.

## 2. Bẫy Kẹt Vòng Lặp Switcher Khi Acc Đã Active (Active Account Switcher Loop Trap)
- **Hiện tượng:** Máy đã đang active đúng nick `@TARGET_USER` trên Profile (hoặc vừa được switch thành công). Nhưng runner vẫn mở Switcher để kiểm tra, thấy nick đích nằm ở dòng 1 và bấm vào dòng đó. Vì nick đã active, TikTok không đổi gì và giữ nguyên bottom sheet Switcher. Runner lại thấy dòng đó và bấm tiếp, dẫn đến kẹt 5 lần ở trạng thái `SWITCHER` và văng `exit_2` (`Abort: ket o trang thai SWITCHER 5 lan lien tiep`).
- **Khắc phục:**
  * Lưu vết `last_seen_user` khi ở màn hình `PROFILE`.
  * Trong trạng thái `SWITCHER`: Nếu hit tìm thấy chính là nick đang active trên Profile (`seen_profile and is_target_user(last_seen_user)`):
    -> **Bấm Back (`keyevent 4`)** để đóng Switcher ngay lập tức và tiếp tục kiểm tra Profile, không bấm vào dòng nick đang active.

## 3. Nhận Diện Nút Sửa Hồ Sơ / Icon Cây Bút Chì Trên Mọi Giao Diện TikTok
- TikTok có 2 layout Profile chính:
  1. **Giao diện cũ (canh trái):** Có nút text *"Sửa hồ sơ"* rõ ràng, hoặc icon cây bút chì ở góc phải dòng tên `(870, 558)`.
  2. **Giao diện mới (canh giữa):** Avatar ở giữa, tên ở giữa, không có nút text *"Sửa hồ sơ"*, mà chỉ có **icon cây bút chì nhỏ nằm ngay bên phải hộp text của tên**.
- **Cách tap tin cậy:**
  * Nếu OCR thấy nút text `(sua|chinh sua|edit) (ho so|profile)`: Tap tâm nút đó.
  * Nếu không thấy nút text: Tìm bounding box của text Tên `name_hit = (t, b)` -> Tọa độ tap chuẩn là `(min(b[2] + 50, 1000), center(b)[1])` (nằm cách mép phải của text tên 50px).
  * Fallback: Tap tọa độ bút chì cố định `(870, 558)`.

## 4. Chuẩn Hóa Bộ Lọc Tên Rác (Chống Đổi Nhầm Tên Hợp Lệ)
- Không ép đổi những tên người tiếng Việt hợp lệ:
  * Tên có dấu tiếng Việt không chứa số (ví dụ: `Đặng Thu Hà`, `Nguyễn Văn An`).
  * Tên 1 từ chữ cái thuần túy không chứa số (ví dụ: `Phong`, `Lan`, `Hà`, `An`, `Trang`, `Đạt`).
  * Tên không dấu nhiều từ gồm các từ chữ cái thuần túy (`Nguyen Van An`).
- **Chỉ coi là RÁC (`is_stereotyped == True`) khi:**
  1. Tên rỗng hoặc None.
  2. Tên trùng 100% username (không phân biệt hoa thường).
  3. Tên dính đuôi số $\ge 2$ chữ số (`re.search(r"\d{2,}$", d)`).
  4. Tên là chuỗi username rác không dấu dính số (`^[a-z0-9_.]+\d+$`).
