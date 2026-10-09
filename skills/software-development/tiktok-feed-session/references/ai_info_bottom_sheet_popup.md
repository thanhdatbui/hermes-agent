# Xử lý Popup / Bottom Sheet "Thông tin về AI" (AI Label Modal)

## Hiện tượng & Nguy cơ
- **Màn hình xuất hiện:** Bottom sheet modal xuất hiện khi lướt trúng video được gắn nhãn AI trên TikTok Feed.
- **Dấu hiệu kẹt:** Modal đè lên vùng cuộn màn hình, vô hiệu hoá swipe cử chỉ video. Runner lầm tưởng là màn hình loading/startup bị đơ và kích hoạt swipe recovery rồi fail sau 2 lần thử.

## Nhận diện (Detector Signatures)
- **Tiêu đề:** `"Thông tin về AI"`, `"AI-generated content"`
- **Nội dung:** 
  - `"Bài đăng được nhà sáng tạo gắn nhãn"`
  - `"Nhà sáng tạo đã đánh dấu rằng nội dung này được tạo hoặc chỉnh sửa bằng AI"`
  - `"TikTok chưa xác nhận điều này có chính xác hay không"`
  - `"Tìm hiểu thêm"`
- **Khớp linh hoạt:** Kiểm tra cả chuỗi XML và OCR (case-insensitive) qua `benign_popup_registry.py`.

## Chiến lược đóng (Dismisser Strategy)
1. **Lớp 1 (Nút ✕ góc trên modal):**
   - Tìm ImageView / View có `content-desc` là `"Đóng"`, `"Close"`, `"Quay lại"` hoặc phần tử icon đóng nằm ở góc trên bên phải của modal container (thường $x > 800$, $y < 1200$).
   - Gọi `ctx.tap(cx, cy)` nếu tính được bounds hợp lệ.
2. **Lớp 2 (Tap ngoài modal):**
   - Tap vào vùng tối phía trên modal (ví dụ `(x=540, y=300)`).
3. **Lớp 3 (Phím BACK an toàn):**
   - Gọi `ctx.keyevent(4)` (Android KEYCODE_BACK) để hạ bottom sheet.
   - `time.sleep(1.0)` và xác nhận màn hình đã trở lại feed.

## Vị trí tích hợp trong Codebase
- **Registry:** `python_runner/flows/benign_popup_registry.py` -> Đăng ký `RegistryEntry("tiktok_ai_info_bottom_sheet", 68, _detect_ai_info_bottom_sheet, _dismiss_ai_info_bottom_sheet, True, "manual")`.
- **Flow Helper:** `python_runner/flows/benign_popup.py` -> Cung cấp hàm `detect_ai_info_popup(xml_root)` và `dismiss_ai_info_popup(ctx)`.
- **Cạm bẫy Dataclass `PopupDismissResult`:** Trường `before_attempt: dict[str, Any]` không có default value trong `benign_popup.py`. BẮT BUỘC truyền `before_attempt={"action": "dismiss_ai_info_bottom_sheet"}` khi khởi tạo `PopupDismissResult`, nếu không sẽ ném `TypeError: missing 1 required positional argument`.
- **Focused Unit Test:** Chạy via `python -m unittest tests/test_ai_info_bottom_sheet.py` với workdir `D:/Taadaa/tiktok-luot nuoi acc/python_runner` (tránh lỗi cross-drive ntpath relpath ValueError giữa C: và D: trên Windows).
- **Canary Test Thực Chiến (Máy N):**
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
- **Log định danh:** Ghi nhận `dismiss_tiktok_ai_info_bottom_sheet` trong log.jsonl để phân loại taxonomy `pass/degraded acceptable`.
