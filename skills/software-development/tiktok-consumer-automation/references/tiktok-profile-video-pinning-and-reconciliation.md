# TikTok Profile Video Pinning & Upload Reconciliation

## 1. Cơ chế Ghim (Pin) Video trên TikTok Profile qua ADB
- **Thao tác tối ưu:** Không cần mở player video rồi bấm menu 3 chấm `...`.
- **Thao tác đè cảm ứng (Long-press):**
  - Thực hiện lệnh: `adb -s <serial> shell input swipe <X> <Y> <X> <Y> 1000` trực tiếp tại tọa độ tâm của ô video (tile) trên Profile grid.
  - Sau ~1 giây, TikTok sẽ bật **Action Sheet** từ đáy màn hình.
  - Các tùy chọn trong Action Sheet:
    * `"Ghim lên đầu"` / `"Pin to top"` (nếu chưa ghim).
    * `"Bỏ ghim khỏi đầu"` / `"Unpin from top"` (nếu đã ghim).
    * `"Đặt ở chế độ riêng tư"` / `"Set to private"`.
    * `"Chia sẻ"` / `"Share"`.
  - Tap vào tọa độ của node `"Ghim lên đầu"` / `"Pin to top"` để ghim.
- **Giới hạn TikTok:** Mỗi tài khoản ghim tối đa 3 video.

## 2. Ảnh hưởng đối với quy trình đối soát & Upload
- **`_verify_profile_post_increment` (state_machine.py):**
  - Script đếm tổng số video tiles qua hàm `_count_profile_video_tiles_across_grid()` (`baseline` vs `current`).
  - Video được ghim vẫn là một video tile hợp lệ (có `tv_play_count`, `id/eti`, `id/cover`), chỉ mang thêm nhãn `"Đã ghim"` / `"Pinned"`.
  - Khi đăng video mới, tổng số tiles tăng từ $N \to N + 1$ $\implies$ điều kiện `current > baseline` thỏa mãn 100%.
  - Script **không phụ thuộc** vào việc video mới nhất phải nằm ở ô đầu tiên `[0, 0]`.
- **`VIDEO_PICK` (Upload flow):**
  - Chọn video từ thư viện máy (`Download` folder), không đụng vào lưới Profile.
  - Tại `state_machine.py:10061` (`_is_video_pick_profile_action_sheet`), hệ thống đã có sẵn handler nhận diện Action Sheet ghim video để tự bấm Back nếu vô tình chạm trúng khi bấm nút `+`.
- **Workbook & Tracker:**
  - Workbook ghi nhận theo số thứ tự file video nguồn (`context.video_number`).
  - Tracker (`tiktok_account_tracker.py`) đọc chỉ số `stats['videoCount']` từ JSON, không bị ảnh hưởng bởi thứ tự ghim.

## 3. Công cụ Chuẩn Hóa: `D:/Taadaa/tools/pin_top_videos.py`
Công cụ tự động hóa việc dò quét và ghim video nổ view cho từng kênh trên phone farm:

### A. Ngưỡng View Tối Thiểu (`--min-views`, Mặc định: 1.000 view)
- **Bản chất thuật toán:** Video thông thường nếu không đặc sắc sẽ dừng ở mức đáy thử nghiệm (seed pool) **200 – 500 view**. Khi vượt mốc **1.000 view**, video đã vượt qua vòng lọc bot/audience ban đầu và bắt đầu cắn đề xuất.
- **Cơ chế Floor Filter:** Chỉ lọc các video có view $\ge 1.000$ và sắp xếp giảm dần để ghim clip cao nhất trước. Nếu toàn bộ video trên kênh $< 1.000$ view, tool tự động bỏ qua không ghim clip nào (tránh làm gượng trang cá nhân).

### B. Cú Pháp Vận Hành
```bash
# 1. Chạy thử kiểm tra trước (Dry-run — chỉ quét, không thao tác cảm ứng):
python D:/Taadaa/tools/pin_top_videos.py --machine 18 --min-views 1000 --dry-run

# 2. Ghim thật cho 1 máy theo ID máy (tự động tra cứu serial Kibe Local / Admin Remote):
python D:/Taadaa/tools/pin_top_videos.py --machine 18 --min-views 1000

# 3. Ghim trực tiếp theo ADB Serial:
python D:/Taadaa/tools/pin_top_videos.py --serial ce031603a3dc2d2804 --min-views 1000

# 4. Tùy chỉnh ngưỡng view cao hơn (cho nick khỏe / viral):
python D:/Taadaa/tools/pin_top_videos.py --machine 28 --min-views 5000 --max-pins 3
```

### C. Kỷ Luật An Toàn Thiết Bị (Device Invariants)
- **100% ATX-agent (port 7912):** Đọc UI XML qua `capture_atx_session_ui` hoặc curl direct port 7912, tuyệt đối cấm shell uiautomator dump tránh crash thiết bị yếu (S7 Android 7).
- **Hồi phục an toàn:** Nếu sau cú long-press mà Action Sheet không hiển thị nút Ghim (hoặc video đã được ghim từ trước), tool tự động gửi phím `KEYCODE_BACK` để giải phóng màn hình Profile về trạng thái sạch.

### D. Kiểm Chứng Độc Lập
- Bộ unit test offline: `pytest D:/Taadaa/tools/test_pin_top_videos.py` (bao phủ `parse_view_count`, `parse_action_sheet`, `parse_profile_tiles`).

## 4. Kỷ Luật Tự Động Hóa Mở Profile Từ Automation-Core (CẤM GỌI USER MỞ TAY)
- **Quy tắc bất biến:** Khi chạy Canary hoặc thao tác trên tài khoản mục tiêu, **CẤM TUYỆT ĐỐI** hỏi User: *"bạn đang mở máy số mấy"*, *"bạn mở sẵn Profile đi để mình bắn lệnh"*. Đây là hành vi đùn đẩy việc vi phạm kỷ luật Coordinator.
- **Quy trình tự động 100%:**
  1. **Tra cứu máy & slot:** Quét `Tik1-Tik8.xlsx` hoặc `taikhoan_dat_v2.xlsx` để xác định nick mục tiêu (ví dụ `@hoangthu18044` $\to$ Máy 67, Tik 6).
  2. **Đánh thức thiết bị:** Kiểm tra `dumpsys power`, gửi `KEYCODE_WAKEUP` + `82` (unlock).
  3. **Khởi chạy TikTok:** Dùng `am start -n com.ss.android.ugc.trill/.MainActivity` hoặc monkey launcher.
  4. **Tự động vào Profile & Chuyển tài khoản:**
     - Sử dụng trực tiếp `open_profile_root(adapter)` từ `automation_core.tiktok.account_switcher`.
     - Nếu nick hiện tại chưa đúng nick cần ghim: Dùng `select_exact_account(adapter, username)` để tự động mở switcher và chuyển sang đúng nick.
     - Thoát video overlay / Live popup: Nếu vướng overlay Live (*"Nhận để xem LIVE"*), vuốt nhẹ `swipe(540, 1400, 540, 700, 300)` để trượt qua rồi tap Profile tab `(970, 1850)`.

## 5. Luồng Ghim Video Thực Chiến Đã Nghiệm Thu
- **Cách 1 (Share Sheet trên Video Player — Khuyến nghị):**
  1. Từ lưới Profile, tap vào ô video top view (`center` của tile).
  2. Bấm nút Chia sẻ/Khác ở cột action bên phải (`x=1000, y=1556` trên màn 1080x1920).
  3. Bottom sheet hiện ra: Tìm node có text/desc `"Ghim"` / `"Pin"` (bounds chuẩn `[747, 1656][915, 1896]`).
  4. Tap vào nút Ghim $\to$ Bấm `KEYCODE_BACK` quay về Profile.
  5. Kiểm chứng hiện trường: Video đầu tiên xuất hiện nhãn chữ nổi màu đỏ **"Đã ghim"** (Verified qua WinRT OCR: `"Dä ghim"`).
- **Hỗ trợ cờ `--account`:**
  ```bash
  python D:/Taadaa/tools/pin_top_videos.py --machine 67 --account hoangthu18044 --min-views 1000
  ```

