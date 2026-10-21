# Triage Hiện Tượng Watchdog Báo Lượt Follow > 0 Nhưng "Thành Công 0 Máy"

## 1. Bản Chất Hiện Tượng

Trong báo cáo Telegram của `feed_session_watchdog.py`:
```text
• Follow chéo (4 lượt follow) [Module 2 (Anchor): 4 | Module 1 (Bù): 0]:
+ Thành công (0 máy | 0.0%): Không có
+ Đối soát TikTok Web (+3 Following thật | Lệch -1 so với script báo 4):
  - M59 (@thutuan4916) : script 3 lượt - web 3 lượt - khớp
  - M63 (@nhumai1595) : script 1 lượt - web 0 lượt - lệch (-1)
+ Nhả follow (14 máy | 100.0%):
  - Nhả liền (0 lượt | 85.7%): (M5, M11, M12, M16, M17, M44, M45, M51, M56, M58, M62, M67)
  - Nhả ở Hồi phục 1 (1 - 4 lượt | 14.3%): (M59: 3 lượt, M63: 1 lượt)
```

Người vận hành thắc mắc: *"Ủa sao có máy follow được mà lại báo không máy follow được ở đầu report?"*

### Nguyên nhân kỹ thuật trong code:
1. **`total_followed_count` (Dòng tiêu đề):**
   - Tính bằng tổng số phần tử `len(fd.get("followed", []))` của mọi máy có chạy follow.
   - Máy M59 follow được 3 nick, M63 follow được 1 nick $\rightarrow$ Tổng là 4 lượt.
2. **`fl_success` ("Thành công N máy"):**
   - Chỉ tính máy có `status in {"OK", "SUCCESS", "COMPLETED"}` VÀ `follow_failed is not True`.
   - Nghĩa là máy phải hoàn thành trọn vẹn phiên follow mà **không gặp bất kỳ lần nhả nào**.
3. **`fl_released` ("Nhả follow N máy"):**
   - Máy nào có `status == "FOLLOW_FAILED"` hoặc `follow_failed is True` lập tức bị xếp vào `fl_released`.
   - Khi runner thực hiện follow (Path B verify trên Profile), nếu TikTok không nhận nút follow (`FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`), runner kích hoạt fail-closed dừng session ngay để tránh cháy nick.
   - Khi đó, dù trước đó máy đã follow thành công 1, 2 hay 3 nick, toàn bộ máy vẫn bị watchdog đưa vào nhóm `fl_released` (Nhả follow).
4. **Phân nhóm trong `fl_released`:**
   - **Nhả liền (0 lượt):** Bấm phát đầu tiên bị nhả ngay (`cnt == 0`).
   - **Nhả ở Hồi phục 1 (1 - 4 lượt):** Đã follow được 1 - 4 nick rồi mới bị nhả (`1 <= cnt <= 4`). Đây chính là vị trí của M59 và M63.
   - **Nhả ở Hồi phục 2 (5 - 9 lượt)** & **Nhả ở Cấp Khỏe (10+ lượt)**.

## 2. Kỷ Luật Trả Lời & Đối Soát Khi Người Vận Hành Chất Vấn

1. **Khẳng định ngay sự thật:** Máy **thực tế có follow thành công** (chỉ rõ nick nào, mấy lượt, đối soát web có khớp không).
2. **Chỉ rõ vị trí của máy trong báo cáo:** Hướng dẫn người dùng nhìn xuống mục `+ Nhả follow` $\rightarrow$ `Nhả ở Hồi phục 1 (1 - 4 lượt)` để thấy máy của mình (M59: 3 lượt, M63: 1 lượt).
3. **Giải thích ngắn gọn quy tắc watchdog:** Mục "Thành công" trên đầu chỉ vinh danh máy chạy sạch 100% không dính nhả; máy bị nhả ở cuối phiên sẽ được chuyển xuống nhóm Nhả follow để theo dõi cooldown/streak.
4. **CẤM TUYỆT ĐỐI viện dẫn lỗi hạ tầng nội bộ của AI:**
   - CẤM nói "Do lỗi HTTP 503", "Do vision API quá tải", "Do endpoint không phản hồi".
   - Người vận hành không quan tâm và rất khó chịu với lỗi nội bộ của tool ("Lỗi 503 là cái gì").
   - Nếu tool vision/ảnh gặp sự cố, âm thầm dùng WinRT OCR hoặc đọc trực tiếp artifact `log.jsonl` / `follow_result.json` trên ổ đĩa để trả lời có căn cứ.
