# Inbound Vision Hard-Gate & Game Idle Auto-Close Architecture

## 1. Bối Cảnh & Sự Cố
Trong phiên làm việc chuẩn hóa kênh `@vyvy14190`, hệ thống gặp hai sự cố nghiêm trọng:
1. **Agent bị mù ảnh đầu vào nhưng vẫn chém gió**: User gửi ảnh chụp màn hình bắt bẻ lỗi crop avatar (ô 2 và ô 3 chỉ là mảng lông nâu đỏ mờ căm, không có mặt mũi). Thay vì mở ảnh ra xem thật, Agent sinh text trả lời tự nhận và tự bịa lời giải thích. Nguyên nhân là do hệ thống chỉ có Outbound Gate kiểm tra `MEDIA:` ở đầu ra, hoàn toàn không có Inbound Gate ở đầu vào để chặn Agent mở mồm khi chưa mở mắt.
2. **Kẹt lịch reboot định kỳ 11:20 do game treo idle**: Script `farm_preflight_daily_reset.py` kiểm tra thấy tiến trình `war3.exe` (PID 24252) trên Admin PC nên cơ chế chống AFK đã chủ động hủy reboot. Tuy nhiên tiến trình này đã idle chuột/phím hơn 8.8 giờ mà không ai chơi.

---

## 2. Giải Pháp Sửa Tầng Cơ Học

### A. Inbound Vision Hard-Gate tại `gateway/run.py` (dòng 11830)
- **Vị trí**: Nằm tại `gateway/run.py` ngay trước khi response được deliver ra Telegram/chat.
- **Nguyên lý kiểm soát**:
  1. Phát hiện tin nhắn có ảnh (`event.media_urls` hoặc các marker `[Image attached at:` / `[Replied-to image`).
  2. Bắt buộc transcript turn hiện tại phải có tool call vision (`browser_vision`, `vision_analyze`, `ag_cli_vision`) thành công.
  3. **Strict Turn Isolation**: Chỉ quét messages sau `history_offset` (`_turn_msgs = _curr_messages[_hist_len:] if len(_curr_messages) > _hist_len else []`). Tuyệt đối không fallback về toàn bộ transcript cũ để chống bypass bằng tool call của turn trước.
  4. **Tool Success Verification**: Kiểm tra tool result (role='tool') bắt buộc content > 10 ký tự và không dính `error`, `failed`, `traceback`.
  5. **Fail-Closed 100%**: Nếu vi phạm hoặc có exception, Gateway tự động ghi đè câu trả lời thành:
     `⛔ [GATEWAY BLOCKED - INBOUND VISION GATE]: Tin nhắn có ảnh đính kèm nhưng Agent chưa thực sự gọi tool Vision mở mắt đọc ảnh trong lượt này! Yêu cầu Agent phải gọi tool kiểm tra ảnh trước khi trả lời!`

### B. Game Idle Auto-Close Watchdog (`C:\Taadaa_Service\game_idle_auto_close_watchdog.py`)
- **Mục đích**: Tự động đóng game Warcraft 3 hoặc TFT/League khi người dùng không thao tác chuột/phím > 1 giờ (3600s), giải phóng tài nguyên và tránh chặn lịch reboot định kỳ 05:20, 11:20, 17:20.
- **Cơ chế**:
  - Dùng `ctypes.windll.user32.GetLastInputInfo` đo thời gian không đụng chuột/phím trên Windows.
  - Quét các process: `war3.exe`, `w3l.exe`, `warcraft iii.exe`, `frozen throne.exe`, `league of legends.exe`, `tftclient-win64-shipping.exe`.
  - Nếu `idle_seconds >= 3600`: Tự động gửi `terminate()` hoặc `taskkill /F /PID` đóng game an toàn.
  - Nếu `idle_seconds < 3600`: Im lặng thoát (exit 0) để người dùng tiếp tục chơi.
