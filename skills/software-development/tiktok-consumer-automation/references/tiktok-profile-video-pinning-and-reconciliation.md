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
