# Avatar Upload Failure Signatures and Recovery (Taadaa Farm)

Tài liệu hướng dẫn nhận diện, phân loại và xử lý nhanh O(1) các cụm lỗi thường gặp trong quá trình upload avatar tài khoản TikTok hàng loạt sau ca tối (`post_evening_avatar_watchdog`).

---

## 1. [AVATAR_EDIT_OPEN_FAILED / right_pencil_button False Positive]

### Hiện tượng
Khi chạy upload avatar ca tối (`run_tiktok_upload_avatar.ps1` hoặc `post_evening_avatar_watchdog.py`), nhiều máy báo lỗi:
```text
[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở
```
Tiến trình kẹt khoảng 240s qua nhiều nhánh thử (thử click bút chì, vuốt header, tap avatar circle, fallback deep-link) rồi thất bại.

### Căn nguyên gốc rễ
Trong `tiktok_workflow/state_machine.py`, hàm `_find_profile_edit_button()` sử dụng detector heuristic:
```python
right_pencil_button = (
    750 <= left <= 950
    and 450 <= top <= 650
    and 80 <= right - left <= 220
    and 60 <= bottom - top <= 160
)
```
1. **False Positive trên Layout mới hoặc khi Profile bị Scrolled**:
   - Khi trang Profile bị cuộn xuống phần grid video, hoặc trên layout TikTok có nút phụ ở góc phải (nút "Chia sẻ hồ sơ", liên kết Instagram, hoặc thumbnail video ở hàng đầu tiên), widget ImageView này có tọa độ `[931..1080, 463..636]` thỏa mãn điều kiện `right_pencil_button`.
2. **Lỗi Short-circuit trong vòng lặp**:
   - Trong vòng lặp `for node in root.iter("node")`, detector kiểm tra bounds heuristic ngay lập tức cho từng node không có text. Do đó nó bắt nhầm widget ImageView góc phải trước khi duyệt đến các node có text ngữ nghĩa ("Sửa hồ sơ", "Chỉnh sửa", "+ Thêm tiểu sử") nằm ở phần sau của cây XML.
3. **Hệ quả**:
   - Khi tap nhầm vào widget góc phải (Share sheet hoặc Video), app không chuyển sang màn "Sửa hồ sơ". Các bước kiểm tra sau đó (`_wait_for_avatar_edit_screen`) timeout 60s cho mỗi lần thử và kết luận `AVATAR_EDIT_OPEN_FAILED`.

### Triage O(1) & Khắc phục
1. **Kiểm tra hiện trường bằng mắt**:
   - Mở ảnh `profile-grid-account_ready-*.png`.
   - Chạy OCR (`winrt_ocr.py`) kiểm tra xem màn hình có đang hiển thị video thumbnail hoặc nút "Chia sẻ" hay không.
2. **Kỷ luật sửa code**:
   - Tách làm 2 pass duyệt XML độc lập:
     - **Pass 1 (Semantic First)**: Duyệt toàn bộ XML tìm kiếm theo semantic text (`text` hoặc `content-desc` khớp `"Sửa hồ sơ"`, `"Chỉnh sửa"`, `"+ Thêm tiểu sử"`, `"Edit profile"`) và resource ID đã biết.
     - **Pass 2 (Layout Heuristic Fallback)**: Chỉ kích hoạt khi Pass 1 hoàn toàn không tìm thấy bất kỳ candidate nào.
   - Thêm bước vuốt đưa header về đỉnh (`swipe 540 500 540 1500`) trước khi tìm nút sửa hồ sơ.

---

## 2. [AVATAR_SOURCE_MISSING / Missing avatar.jpg in Video Folder]

### Hiện tượng
Script upload avatar dừng khẩn cấp và ném lỗi:
```text
[AVATAR_SOURCE_MISSING] ENSURE_AVATAR: Avatar file not found in folder: D:\video goc\<folder_id>
```

### Căn nguyên
Folder video gốc (ví dụ: `D:\video goc\415`) đã được tải về và render video, nhưng bước tạo file avatar đại diện (`avatar.jpg`) bị gián đoạn, bỏ sót, hoặc chưa được copy ra thư mục gốc của folder.

### Triage & Cấp cứu O(1)
1. **Kiểm tra frame đại diện có sẵn**:
   - Kiểm tra thư mục con `D:\video goc\<folder_id>\.avatar_work\representative_frames\`.
   - Nếu đã có file `v00_001.jpg`, thực hiện copy ngay lập tức:
     ```python
     shutil.copy(r"D:\video goc\<folder_id>\.avatar_work\representative_frames\v00_001.jpg", r"D:\video goc\<folder_id>\avatar.jpg")
     ```
   - Thao tác tốn O(1) (< 1 giây), lập tức unblock máy cho lượt upload tiếp theo mà không cần chạy lại pipeline render nặng nề.
2. **Nếu chưa có frame đại diện**:
   - Chạy script tạo avatar chuẩn của repo:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/_make_avatar.py <folder_id>
     ```

---

## 3. [Bulk Device Disconnect / USB Hub Outage trên Admin Remote]

### Hiện tượng
Báo cáo batch alert ghi nhận hàng loạt máy liên tục (ví dụ: dải 20 máy `M261..M280`) đồng loạt dính `[PREFLIGHT_VPN_BLOCKED]` hoặc `device not found`.

### Triage O(1)
1. **Không mò mẫm code từng máy**:
   - Kiểm tra file `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` để tra cứu dải máy.
   - Chạy lệnh kiểm tra socket ADB Admin:
     ```bash
     adb -H 192.168.110.119 -P 5037 devices
     ```
2. **Quy luật Hub 20 cổng**:
   - Nếu toàn bộ 20 máy trong 1 dải (như M261..M280) cùng vắng mặt (0/20 online), đây là **sự cố phần cứng vật lý của Hub USB 20 cổng** trên rack Admin (sập nguồn adapter hoặc lỏng cáp uplink USB vào máy chủ Admin).
   - Đánh dấu ngay **L3 BLOCKED** kèm bằng chứng đối soát, báo chủ farm kiểm tra rack vật lý, tuyệt đối không chạy vòng lặp retry hay can thiệp code.
