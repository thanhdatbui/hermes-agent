# Admin Local APK Upgrade, OneDrive Hydration & Camera Thumbnail Visual Triage

## 1. Triệu Chứng & Sự Cố Thực Tế (26/10/2026)
- **Cảnh báo lan rộng toàn batch:** 74/78 máy Admin (M201–M280) báo lỗi:
  `UploadHook: [MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`
- **Nghi vấn ban đầu:** Nghi ngờ do app TikTok chưa lên v47.0.3 như cụm Kibe.
- **Thực tế kiểm chứng:**
  - 65/74 máy Admin **thực tế đã ở sẵn TikTok v47.0.3** (59–60 split APKs) từ trước.
  - Lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` vẫn tái diễn 100% không phải do thiếu APK, mà do **lệch tọa độ tap nút Tải lên (Upload) trong Camera Mode**.

---

## 2. Các Bẫy Vận Hành & Hạ Tầng Cần Tránh

### A. Bẫy Đẩy APK Qua Mạng LAN Socket Thay Vì Tận Dụng Local OneDrive Trên Admin PC
- **Anti-Pattern:** Dùng lệnh `adb -H 192.168.110.119 -P 5037 install-multiple` từ máy Kibe để stream 55 file split APK (280MB/máy × 78 máy = ~22GB dữ liệu) qua mạng LAN.
- **Hậu quả:** Gây nghẽn socket ADB, rớt kết nối USB, timeout 300s và fail hơn 50 máy liên tục.
- **Quy tắc bất biến:**
  - Trên host Admin (`192.168.110.119`) đã có sẵn thư mục đồng bộ OneDrive cục bộ: `D:\OneDrive\apk-bank\com_ss_android_ugc_trill`.
  - BẮT BUỘC thực thi script cài đặt **trực tiếp trên máy Admin** qua `admin_ssh.py`, sử dụng ADB cục bộ `C:\Program Files (x86)\xiaowei\tools\adb.exe` và kho APK tại ổ D cục bộ.
  - Dữ liệu đi thẳng qua bus USB nội bộ của host Admin tới điện thoại, **hoàn toàn 0 byte tải mạng LAN**.

### B. Bẫy OneDrive Files On-Demand (Cloud-only) & `[Errno 22] Invalid argument`
- **Hiện tượng:** Script Python mới tạo trên OneDrive của Kibe khi vừa đồng bộ sang Admin, chạy qua SSH báo lỗi:
  `can't open file 'D:\OneDrive\...\script.py': [Errno 22] Invalid argument`
- **Nguyên nhân:** Windows OneDrive bật chế độ "Files On-Demand". File mới tạo hiển thị kích thước trong ngoặc đơn (ví dụ `(6,192)` bytes) ở trạng thái Cloud-only (chưa tải nội dung về đĩa). Hàm `open()` của Python trên Windows không thể mở trực tiếp file chưa hydrate.
- **Giải pháp:**
  - Hoặc cưỡng chế hydrate file qua PowerShell trước khi chạy:
    ```powershell
    Get-Content D:\OneDrive\...\script.py -Raw | Set-Content D:\Taadaa\tools\script.py
    ```
  - Hoặc lưu các script thực thi trực tiếp vào thư mục đĩa cục bộ không thuộc OneDrive: `D:\Taadaa\tools\`.

### C. Bẫy `UnicodeEncodeError: 'charmap'` Trên Windows OpenSSH Console
- **Hiện tượng:** Script chạy nâng cấp hoàn thành 100% các máy, nhưng dòng cuối in tổng kết bằng tiếng Việt (`print("KẾT QUẢ: ...")`) khiến Python crash với `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ebe'`.
- **Nguyên nhân:** Phiên console SSH trên Windows mặc định dùng codepage `cp1252` thay vì UTF-8.
- **Giải pháp:**
  - Luôn truyền cờ `-X utf8` hoặc `-u` khi gọi Python qua SSH: `python -X utf8 script.py`.
  - Phần text in ra console summary ở script công cụ nền nên dùng tiếng Anh / ASCII không dấu (`RESULT: OK=...`).

### D. Bẫy Ngưỡng Sáng Thumbnail Camera Upload (`non_dark_r` vs Nút Hiệu Ứng Bên Trái)
- **Bố cục giao diện Camera TikTok:**
  - **Bên TRÁI nút quay (Shutter):** Là nút **"Hiệu ứng"** (Effects). Icon này luôn có màu sắc rực rỡ (`non_dark_l >= 0.20`).
  - **Bên PHẢI nút quay:** Mới chính là nút **"Tải lên"** (Upload / Gallery).
- **Cái bẫy thuật toán trong `state_machine.py`:**
  - Code kiểm tra độ sáng vùng bên phải `non_dark_r`. Khi clip vừa render hoặc đẩy vào máy có thumbnail/frame đầu tối, `non_dark_r` tụt xuống 0.0000.
  - Thuật toán `ordered_candidates = left_targets + right_targets` thấy bên trái có điểm sáng (`non_dark_l >= 0.20`) liền ưu tiên cụm bên trái, dẫn tới việc **tap 4 lần liên tiếp vào nút "Hiệu ứng"** (`x≈156, y≈1574`).
  - Gallery không mở ra được, script lùi lại tìm nút `+` đáy thất bại và kích hoạt fail-closed `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.
- **Giải pháp:**
  - Đảo thứ tự ưu tiên nút bấm: `ordered_candidates = right_targets + left_targets`.
  - Luôn ưu tiên tap vào nút "Tải lên" bên phải (`R` tại tọa độ `x≈945, y≈1593` trên màn 1080×1920) làm mục tiêu chính khi ở Camera surface, bất kể video thumbnail sáng hay tối.
