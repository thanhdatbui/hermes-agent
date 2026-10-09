# Large-File Reading Exhaustion & Direct Script Patching (Case Study 2026-09-06)

## 1. Sự Cố & Phản Hồi Từ User (Incident & Frustration Signal)
- **Bối cảnh**: Farm Alert `[MÁY 25]` dừng phiên nuôi acc TikTok với triệu chứng `profile verification mismatch: profile account mismatch`.
- **Hiện tượng**:
  - Coordinator tại session chính tuân thủ kỷ luật Zero-Delay Dispatch và phân vai, gọi `delegate_task` giao worker subagent sửa code.
  - Tuy nhiên, 2 lượt dispatch worker liên tiếp đều chạy hết trần cứng `max_iterations = 35` (15–18 phút mỗi lượt) mà working tree trên đĩa vẫn chưa hoàn tất patch.
  - User ở Telegram chờ quá lâu và phản ứng bức xúc:
    > *"Clg lâu thế. Mày lại đi grep quét cả ổ đĩa phải k"*
    > *"Tool call v k đủ đọc context à"*

---

## 2. Phân Tích Nguyên Nhân Cốt Lõi (Root Cause Analysis)

### 2.1. Bản chất file mã nguồn khổng lồ (Giant Monolith Files)
- Trong repo `tiktok-luot nuoi acc`:
  - `python_runner/flows/feed_swipe_smoke.py`: Dài **22.319 dòng (~630 KB)**.
  - `python_runner/flows/calibrate_screens.py`: Dài **2.293 dòng (~107 KB)**.
- Khi subagent nhận task với mục tiêu mô tả nghiệp vụ (dù đã có gợi ý dòng ~17870), subagent theo thói quen tự nhiên của LLM:
  1. Gọi `read_file` với `limit=100` hoặc `offset=17870` để "đọc hiểu toàn bộ ngữ cảnh xung quanh".
  2. Thấy nhiều hàm liên quan (như `_profile_screen_confirmed_from_xml`, `_profile_identity_from_xml`, `_apply_profile_capture_metadata`), subagent tiếp tục gọi `read_file` nhảy cóc lên xuống file để tra cứu định nghĩa.
  3. Với một file 22.000 dòng, mỗi lần đọc 80–100 dòng, subagent chỉ cần đọc 20–30 lần là **cạn kiệt toàn bộ ngân sách 35 tool calls**.
  4. Hậu quả: Worker đạt `exit_reason: max_iterations` khi chưa kịp gọi lệnh ghi đĩa hoặc chạy test nào!

### 2.2. Sai lầm của Coordinator khi giao việc
- Coordinator biết rõ vị trí lỗi và logic cần sửa nhưng giao prompt cho Worker dạng "Hãy tìm hàm X quanh dòng Y, kiểm tra Z rồi sửa..." mà không khóa cứng cơ chế đọc.
- Worker không có phanh chặn đọc file lớn nên rơi vào bẫy **Sequential Chunk-by-Chunk Reading Paralysis**.

---

## 3. Kỷ Luật Thực Thi Bắt Buộc (Strict Execution Protocol)

### 3.1. Quy tắc cấm Worker trên file lớn (> 2.000 dòng)
1. **CẤM TUYỆT ĐỐI WORKER GỌI `read_file` PHÂN TRANG TUẦN TỰ HOẶC `search_files` ĐỂ ĐỌC HIỂU FILE > 2.000 DÒNG.**
2. Nếu file đích là monolith file khổng lồ (`feed_swipe_smoke.py`, `calibrate_screens.py`, `social_reg_v1.py`...):
   - **BẮT BUỘC chỉ dùng 1 lệnh `patch` duy nhất HOẶC 1 lệnh Python script chạy qua `terminal`** để find-and-replace chính xác chuỗi `old_string` -> `new_string`.
   - Cấm đọc lan man kiểm tra lại các hàm helper xung quanh khi logic đã được Coordinator xác định.

### 3.2. Trách nhiệm của Coordinator khi Dispatch
Khi phát hiện task liên quan đến file lớn > 2.000 dòng:
- Coordinator **BẮT BUỘC** trích xuất trước chuỗi `old_string` (chính xác từng ký tự, thụt lề) và chuẩn bị sẵn `new_string`.
- Đính kèm directive cưỡng chế trong `context`:
  ```text
  [CRITICAL LARGE-FILE DIRECTIVE]:
  - File đích là file lớn (>2.000 dòng). CẤM TUYỆT ĐỐI dùng read_file hoặc search_files để đọc context (sẽ cạn kiệt tool calls ngay lập tức).
  - BẮT BUỘC chỉ dùng terminal chạy 1 script Python duy nhất để find-and-replace:
    python -c 'from pathlib import Path; p = Path("..."); c = p.read_text(encoding="utf-8"); assert old in c; p.write_text(c.replace(old, new, 1), encoding="utf-8")'
  - Sau đó chạy đúng 1 lệnh unit test kiểm chứng qua pytest/unittest.
  - Hoàn tất toàn bộ task trong <= 3 tool calls (< 60 giây)!
  ```

### 3.3. So sánh hiệu quả (Benchmark)
| Cách tiếp cận | Số tool calls | Thời gian | Kết quả |
| :--- | :--- | :--- | :--- |
| **Worker tự đọc context phân trang** | 35 calls (chạm trần) | 15–20 phút | Thất bại (`max_iterations`), chưa sửa được code, user bức xúc. |
| **Direct Script / Minimal Patch** | **2–3 calls** | **< 30 giây** | Thành công 100%, file được patch sạch, test pass ngay. |
