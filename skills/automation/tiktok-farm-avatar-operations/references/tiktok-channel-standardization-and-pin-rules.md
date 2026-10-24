# Quy Chuẩn Chuẩn Hoá Kênh TikTok Farm & Quy Tắc Ghim Bài (Pin Top)

Quy trình chuẩn hoá kênh TikTok toàn diện (Profile Standardization 5-in-1: Tên, Bio, Avatar, Hashtag/Niche, Ghim bài) áp dụng trên dàn máy Phone Farm.

---

## 1. Năm Hạng Mục Chuẩn Hoá Kênh (5-in-1 Checklist)

| STT | Hạng mục | Quy chuẩn thực thi | Cơ chế khóa & Bảo vệ |
| :--- | :--- | :--- | :--- |
| **1** | **Tên hiển thị (Nickname)** | 100% tiếng Việt có dấu, họ tên người thật tự nhiên (VD: `Đặng Nhật Huy`, `Thanh Khoa`). CẤM hậu tố rác (`Heo`, `Sữa`, `Cún`, số ngẫu nhiên). | Khóa tay sau khi đổi, cấm script đổi tên tự động can thiệp. |
| **2** | **Tiểu sử (Bio)** | 100% tiếng Việt có dấu, đúng định vị ngách (Niche), văn phong tự nhiên. CẤM link rác, ký tự lạ. Gõ bắt buộc qua **AdbKeyboard Base64 UTF-8** (cấm `adb input text` thô). | Pre-submit check: kiểm tra độ dài > 0 ký tự trước khi bấm Lưu (`980, 150`). |
| **3** | **Avatar (Ảnh đại diện)** | Trích xuất khuôn mặt/nhân vật từ video gốc, crop vuông $512 \times 512$, WinRT OCR kiểm tra `lines == 0` (sạch chữ rác/watermark). | Cắm marker `.manual_avatar_locked` tại cả 2 kho $F_{src}$ & $F_{vid}$, đăng ký vào `manual_avatar_protected_folders.json`, set `Avatar = OK`. |
| **4** | **Hashtag & Niche** | Xác định đúng chủ đề video thực tế (VD: Lập trình, Âm nhạc, Nhảy, Nấu ăn), cập nhật bộ Hashtag Pool chuẩn 10 tag. | Cắm marker `.manual_hashtag_locked` tại $F_{src}$ & $F_{vid}$, đăng ký vào `manual_hashtag_protected_folders.json`, cập nhật `TaiKhoan` & `Hashtag theo Folder`. |
| **5** | **Ghim bài (Pin Top)** | Đưa video top view cao nhất lên vị trí danh dự tạo uy tín cho kênh. | Áp dụng ngưỡng view trần $\ge 1.000$ views và cơ chế LIFO. |

---

## 2. Quy Tắc Ghim Bài (Pin Top Video) & Điều Kiện Ngưỡng

### A. Ngưỡng View Kích Hoạt (Threshold Gate):
* **CHỈ GHIM KHI VIDEO ĐẠT TRẦN $\ge 1.000$ VIEWS (1K+):**
  - Mục đích ghim bài là tạo **mỏ neo uy tín và độ trust (social proof)** khi người xem bấm vào Profile.
  - **CẤM TUYỆT ĐỐI GHIM BÀI VIEW LẸT ĐẸT:** Nếu kênh chỉ có các video vài chục đến vài trăm view (hoặc 0 view), **BẮT BUỘC KHÔNG GHIM**, giữ nguyên hiển thị theo timeline tự nhiên. Ghim video view thấp sẽ phản tác dụng, làm lộ rõ tài khoản farm/kênh yếu và giảm tỷ lệ bấm Follow.

### B. Cơ Chế LIFO & Quy Tắc Xếp Ô (Ô 1 Luôn Là Top View Cao Nhất):
* **Cơ chế TikTok LIFO (Last In, First Out):**
  - Mỗi khi bấm **Ghim** một video mới, TikTok sẽ tự động **nhét video mới đó vào Ô số 1 (trên cùng bên trái)** và **đẩy các video đã ghim trước đó lùi sang phải**.
* **Quy tắc xếp hàng chuẩn:**
  - **Video có view cao nhất BẮT BUỘC phải nằm ở Ô số 1 ngoài cùng bên trái.**
  - Nếu ghim nhiều video (tối đa 3 clip): Ghim theo **thứ tự view tăng dần** (video view thấp hơn ghim trước, video view cao nhất ghim sau cùng) để video cao nhất chốt ở Ô số 1.
  - **Đổi video ghim (Swap):** Nếu clip view cao nhất bị đẩy sang ô 2 hoặc 3, phải **Bỏ ghim (Unpin)** clip đó rồi **Ghim lại ngay** để đưa nó trở lại Ô số 1.

---

## 3. Thao Tác UI Trên Màn Hình Samsung S7 (1080x1920)

* **Tọa độ tâm nút "Sửa hồ sơ":** `(315, 865)`.
  - **CẤM TAP `(540, 865)`:** Tọa độ $x=540$ là khe giữa 2 nút `[Sửa hồ sơ]` và `[Chia sẻ hồ sơ]`, tap vào đây sẽ rơi vào khoảng trống và kẹt 5 lần ở màn hình Profile (`ABORT: ket o trang thai PROFILE 5 lan lien tiep`).
* **Bơm chữ tiếng Việt có dấu:**
  ```bash
  # 1. Chuyển sang AdbKeyboard
  adb -s <serial> shell ime set com.github.uiautomator/.AdbKeyboard
  # 2. Bơm text base64 UTF-8
  adb -s <serial> shell am broadcast -a ADB_INPUT_B64 --es msg <base64_string>
  ```
* **Nút Lưu (Save):** Tọa độ góc trên bên phải `(980, 150)`.

---

## 4. Nghiệm Thu Thực Tế (Visual Proof & OCR Invariant)

* Trước khi kết thúc chuẩn hoá hoặc báo cáo User:
  1. Chụp ảnh màn hình Profile thiết bị thật (`MEDIA:<path>`).
  2. Dùng `browser_vision` hoặc `run_winrt_ocr.py` soi mắt kiểm tra tận mắt:
     - Đúng username (`@handle`).
     - Tên hiển thị tiếng Việt có dấu đúng chuẩn.
     - Bio hiển thị đầy đủ dấu tiếng Việt, không lỗi font hay ký tự lạ.
     - Nếu có ghim bài: Xác nhận có nhãn chữ đỏ **"Đã ghim"** ở góc trên bên trái thumbnail ô số 1 kèm số view $\ge 1.000$ views.
