# TikTok Search Results Stuck Recovery (Máy 74 & Phone Farm)

## 1. Hiện tượng & Triệu chứng
- **Log Runner:** `unknown TikTok state; swipe recovery (2 swipes) still stuck` hoặc `manual-needed:popup` / `unknown`.
- **Hiện trường thực tế:** Màn hình TikTok đang hiển thị trang **Kết quả tìm kiếm (Search Results)**:
  - Có thanh tìm kiếm `search_edit_text` hoặc query text ở đầu màn hình.
  - Có nút Back arrow (←) ở góc trên bên trái (`bounds[0] <= 200, bounds[1] <= 300`, text `←`, `quay lại`, `back` hoặc id `btn_back`/`iv_back`).
  - Có các tab điều hướng kết quả: `Top` (hoặc `Hỏi`, `Top`, `Người dùng`, `Video`, `Âm thanh`, `LIVE`, `Địa điểm`...).
  - Phần thân màn hình là danh sách/grid video hoặc tài khoản liên quan đến từ khóa tìm kiếm.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Phân loại màn hình bị hổng:**
   - Hàm `detect_search_landing_page` trong `core/benign_popup.py` và `_detect_search_landing` trong `flows/benign_popup_registry.py` chỉ bắt các từ khóa của trang **Gợi ý / Khám phá** (`bạn có thể thích`, `tìm kiếm gần đây`, `nội dung tìm kiếm thịnh hành`, `suggested searches`...).
   - Khi đã nhập từ khóa và bấm tìm kiếm, màn hình chuyển sang **Trang Kết Quả Tìm Kiếm (Search Results)**. Tại đây không còn các từ khóa landing gợi ý, khiến `find_matching_handler` không tìm thấy handler phù hợp.
2. **Cơ chế recovery vuốt feed phản tác dụng:**
   - Trong `_swipe_recovery_on_stuck` (`feed_swipe_smoke.py`), khi gặp màn hình `unknown`, hàm cố gắng thực hiện 2 lần vuốt dọc `input swipe 540 1400 540 400 300`.
   - Tại trang Search Results, lệnh vuốt dọc chỉ cuộn trang kết quả tìm kiếm xuống dưới mà không bao giờ đưa ứng dụng trở lại màn hình Home Feed (`for-you`, `following`, `friends`).
   - Do đó, cả 2 lần vuốt đều thất bại và kết thúc phiên với lỗi `swipe recovery (2 swipes) still stuck`.

## 3. Quy chuẩn khắc phục (Best Practice & Fix Pattern)
1. **Mở rộng nhận diện Search Results & Cạm bẫy Negative Exclusion:**
   - Bổ sung kiểm tra màn hình Search Results trong `core/benign_popup.py` (`detect_search_results_page` hoặc gộp vào `detect_search_landing_page`):
     - Có ô nhập / hiển thị search: class chứa `EditText` hoặc id chứa `search_input`, `et_search`, `search_edit_text`, `tv_search_input`.
     - Cụm tab phân loại kết quả: `Top`, `Người dùng` / `Users`, `Video` / `Videos`, `Âm thanh` / `Sounds`, `LIVE`, `Địa điểm` / `Places`.
     - Điều kiện Search Results: `is_search_results = has_search_input and has_search_tabs`.
   - **Cạm bẫy False Positive Profile Exclusion:** Trang Search Results thường chứa thẻ profile user với text "follower", "following", "đã follow". Nếu áp dụng danh sách loại trừ profile chung (`negative_markers`), hàm sẽ bị `return None` oan uổng. **BẮT BUỘC:** Chỉ áp dụng các marker `("đã follow", "following", "follower", "followers")` khi `not is_search_results`.
2. **Xử lý dismiss 2 lớp trong `_swipe_recovery_on_stuck` (`feed_swipe_smoke.py`):**
   - Tại Section 1B của `_swipe_recovery_on_stuck`, trước khi vuốt feed:
     - Kiểm tra nếu màn hình có nút Back góc trên bên trái (`bounds[0] <= 180, bounds[2] <= 250, bounds[1] <= 320, bounds[3] <= 350` hoặc text/desc `←`, `quay lại`, `back`, `trở lại`) kết hợp ô search hoặc search tabs.
     - Thực hiện bấm nút Back hoặc gửi `keyevent 4` (BACK).
     - **Fallback nút Home feed:** Nếu Back bị kẹt ở lịch sử tìm kiếm, kiểm tra và tap trực tiếp vào tab Trang chủ (`:id/home` hoặc text/desc "trang chủ", "home") ở thanh điều hướng đáy để ép TikTok quay lại Feed chính tức thì.
     - Chờ 0.8s - 1.0s và recapture UI trước khi tiếp tục vuốt.
3. **Cạm bẫy vẽ Banner đỏ kiểm chứng (Canary Screenshot Stamping):**
   - Môi trường host Hermes có `PYTHONPATH` chứa package PIL bị lỗi binary C extension (`ImportError: cannot import name '_imaging' from 'PIL'`).
   - Khi chạy script Python vẽ banner đỏ `[MAY N] CANARY PASS`, **BẮT BUỘC xóa biến môi trường PYTHONPATH** khi gọi venv automation:
     `PYTHONPATH="" "D:/Taadaa/python-envs/automation/Scripts/python.exe" -c "..."`
   - Đảm bảo script dùng đúng thư viện PIL native của venv automation mà không bị venv host đè hỏng.
