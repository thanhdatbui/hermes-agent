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

### D. Bẫy Ngưỡng Sáng Thumbnail Camera Upload (`non_dark_r` vs Nút Hiệu Ứng Bên Trái) & Bẫy Khóa Cứng Tọa Độ (Regression Hazard)
- **Bố cục giao diện Camera TikTok:**
  - **Bên TRÁI nút quay (Shutter):** Là nút **"Hiệu ứng"** (Effects). Icon này luôn có màu sắc rực rỡ (`non_dark_l >= 0.20`).
  - **Bên PHẢI nút quay:** Mới chính là nút **"Tải lên"** (Upload / Gallery).
- **Cái bẫy thuật toán trong `state_machine.py`:**
  - Code kiểm tra độ sáng vùng bên phải `non_dark_r`. Khi clip vừa render hoặc đẩy vào máy có thumbnail/frame đầu tối, `non_dark_r` tụt xuống 0.0000.
  - Khi `non_dark_r < 0.20`, code cũ **loại bỏ hoàn toàn ứng viên bên Phải** (`right_targets = []`).
  - Danh sách chỉ còn duy nhất ứng viên bên Trái (`left_targets`), khiến script tap 4 lần liên tiếp vào nút "Hiệu ứng" (`x≈156, y≈1574`), không thể bung Gallery picker.
- **Bẫy Khóa Cứng Tọa Độ Một Bên (Anti-Pattern / Regression Trap):**
  - CẤM TUYỆT ĐỐI khóa cứng ép tap bên Phải hoặc đảo mù quáng `ordered_candidates = right_targets + left_targets`. Nếu `right_targets` rỗng thì đảo thứ tự vô tác dụng; còn nếu ép cứng bên Phải sẽ gây **Regression** trên các build Samsung S7 (như M38, M27) vốn có nút thumbnail nằm bên Trái (`BL` tại `118, 1824`) hoặc rơi vào bẫy card CapCut khi mở nhầm tab Tạo.
- **Giải Pháp Chuẩn Kiến Trúc (Preserve Dark Right Candidate & Alternating Retry):**
  - Không bao giờ loại bỏ ứng viên bên Phải khi thumbnail tối; gán `score = 0.0` để giữ lại trong `ordered_candidates`:
    ```python
    right_targets = []
    if non_dark_r >= 0.20:
        right_targets.append(("R", (int(width * 0.875), int(height * 0.83)), non_dark_r))
    else:
        right_targets.append(("R", (int(width * 0.875), int(height * 0.83)), 0.0))
    ```
  - Khi danh sách luôn có đủ cả 2 phía, cơ chế luân phiên `target_idx = taps_done % len(valid_targets)` sẽ tự động:
    * Lần 1: Tap bên Trái (nếu điểm sáng cao hơn).
    * Lần 2 (khi UI vẫn là Camera): **BẮT BUỘC luân phiên sang bên Phải** (`945, 1593`), mở thành công Gallery ngay cả khi thumbnail tối đen!
    * Bảo toàn 100% khả năng tương thích cho cả máy có nút bên Trái lẫn máy có nút bên Phải, Zero Regression.
