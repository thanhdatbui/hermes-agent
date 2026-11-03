# Quy Chuẩn Đối Soát Ground Truth Khi Chọn Niche và Tránh Bẫy "Báo Cáo Đối Phó"

## 1. Bối cảnh & Nguyên nhân gốc rễ (Root Cause)
Khi được yêu cầu: *"Tự chọn ngách hot dựa trên dữ liệu cắn đề xuất của farm"*, Coordinator trước đây mắc 3 lỗi nghiêm trọng:
1. **Lười biếng & Làm tắt:** Chỉ đếm số lượng dòng trong Excel `Tik1..Tik5` hoặc nhìn vào kho file `sources.qualified30.json` có sẵn kênh nào thì bốc kênh đó.
2. **Bịa đặt số liệu (Hallucination):** Tự ý phán ngách Ẩm thực là "Top 1 cắn đề xuất", trong khi số liệu kiểm toán toàn farm 1.272 nick đã chứng minh Ẩm thực là "bẫy flop" (tỷ lệ flop 20.3%, chỉ đạt 4.1 tim/clip, video quay chảo nấu không mặt người bị TikTok bóp reach nặng).
3. **Phát ngôn hứa hẹn suông:** Dùng các cụm từ *"em tiếp tục theo dõi..."*, *"để em..."* ở cuối câu mà không gọi tool, dẫn tới việc bị chốt chặn cơ học `conversation_loop.py` chèn cảnh báo `⚠️ [Hệ thống dừng: Bot đã hứa hành động nhưng không kích hoạt tool]`.

## 2. Invariant Đối Soát Niche Bắt Buộc Trước Khi Đổi Nguồn
- **CẤM TUYỆT ĐỐI** tự suy diễn hay chọn Niche theo cảm tính hoặc nhìn vào vài kênh mẫu.
- **BẮT BUỘC** chạy script đối soát toàn diện trên 1.272 tài khoản farm:
  ```bash
  python D:/Taadaa/tools/audit_niches_farm.py
  ```
- **Quy tắc xếp hạng Niche:**
  - 👑 **Top 1 Tương tác & Đề xuất:** `Câu chuyện` (Storytelling / Bài học cuộc sống) — tỷ lệ breakout cao nhất, ít bị flop nhất.
  - 🔥 **Top Hiệu suất / Clip:** `Giao thông` (Camera hành trình) và `Gym / Fitness`.
  - ❌ **Vùng Cấm (Flop Trap):** Tuyệt đối KHÔNG chọn `Ẩm thực quay cận cảnh`, `Yoga`, `Làm đẹp Douyin`, `Mỹ phẩm` cho các kênh đang cứu flop.

## 3. Kỷ Luật Tool-Use & Chống Cảnh Báo Dừng Bot
- Khi thông báo tiến độ cho User, **CẤM dùng các từ hứa hẹn suông** nằm trong danh sách `_action_phrases` (`em sẽ`, `để em`, `tiếp tục theo dõi`, `đang tiến hành`...) nếu không kích hoạt tool trong cùng lượt.
- Báo cáo kết quả phải dựa trên **bằng chứng vật lý đã kiểm chứng**: file trên đĩa D, log tiến trình exit code 0, telemetry `report.json` và ảnh chụp màn hình UI thật.
