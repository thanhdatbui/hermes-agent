# Pitfall & RCA: Kẹt Video Detail Surface Trong Normalize Home (VIDEO_PICK_HOME_NOT_REACHED)

## Hiện tượng & Mã lỗi
- **Mã lỗi:** `[VIDEO_PICK_HOME_NOT_REACHED] Không đạt Home root 'trang chủ' + labelled bottom-centre create control trong budget 60s (taps=0, backs=0)`
- **Các máy bị ảnh hưởng tiêu biểu:** M57, M58, M61, M67 trong các đợt chạy upload sau Profile Grid Scan (`ACCOUNT_READY`).

## Nguyên nhân gốc rễ (Root Cause)
1. **Màn hình thực tế:**
   - Sau khi scan grid video trên profile để kiểm tra baseline video hoặc avatar, TikTok có thể bị mở vào xem video chi tiết fullscreen (video playback của chính nick).
   - UI có: nút Back (`content-desc="Quay lại"`, resource `bsd`), thanh tìm kiếm (`Tìm nội dung liên quan`, resource `oa4`/`tv_search_sug_word`), `345 lượt xem` (`view_entrance_text`), nút `Cài đặt quyền riêng tư` (`t0c`).
   - Màn hình này **không có bottom nav** (không có các tab `home_tab`, `profile_tab`...).
2. **Khuyết tật nhận diện trong `state_machine.py`:**
   - Hàm `_is_video_detail_surface` yêu cầu quá ngặt: bắt buộc phải có `caption_markers = ("thêm vị trí", "add location", "thêm ghi chú")`. Tuy nhiên video cũ hoặc video thông thường của nick không hề có location marker nên điều kiện này fail (`False`).
   - Màn hình lại chứa `resource-id="com.ss.android.ugc.trill:id/long_press_layout"` nên hàm `_is_tiktok_root_surface` nhận diện nhầm đây là Root surface (`True`).
   - Kết quả: Vòng lặp `_normalize_to_home_for_video_pick` không tìm thấy tab Trang chủ để tap, nhưng cũng không dám Back (vì tưởng là root surface). Vòng lặp rơi vào `break` ngay tức khắc sau lần dump đầu tiên (`taps=0, backs=0`) và ném ngoại lệ `VIDEO_PICK_HOME_NOT_REACHED`.

## Giải pháp kỹ thuật chuẩn hóa
1. **Mở rộng nhận diện `_is_video_detail_surface`:**
   - Bổ sung các markers đặc trưng của video thuộc sở hữu của nick:
     - `t0c` hoặc text `"cài đặt quyền riêng tư"` / `"privacy settings"`
     - `view_entrance_text` hoặc text `"lượt xem"` / `"views"`
     - `tv_post_time` (ngày đăng video)
2. **Quy tắc điều hướng trong `_normalize_to_home_for_video_pick`:**
   - Khi phát hiện `_is_video_detail_surface`: Bắt buộc thực hiện 1 nhịp `Back` có giới hạn (`bounded_back`, tối đa 2 lần) để thoát khỏi fullscreen video player về lại Profile root.
   - Khi đã về Profile root (đã xuất hiện bottom nav bar), thực hiện tap semantic vào tab `Trang chủ` (`home_tab` hoặc text `"Trang chủ"`) để chuyển về feed và đạt Home root + nút Create (`+`).
