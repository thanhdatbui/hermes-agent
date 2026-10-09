# follow module2 degraded pattern — 2026-09-25

## Bối cảnh
Phiên nuôi Ca 1 ngày 2026-09-25: 5 máy (M9, M29, M38, M39, M48) follow tự nhiên thành công (2-4 lượt/máy trong Feed), nhưng follow chéo chỉ được đúng 1 lượt/máy (nick Anchor). Root cause: module 2 abort toàn phiên khi không mở được tab "Đã follow" của Anchor.

## Chuỗi lỗi (module 2 gốc trước khi fix)
1. Script follow Anchor → ghi nhận 1 lượt follow (Anchor).
2. Bấm vào tab "Đã follow" trên trang cá nhân Anchor → màn hình relation render nhưng tab chưa `selected=true` trong UiAutomator dump (animation lag, hoặc TikTok mở ở tab khác).
3. Sau 2 lần thử (ladder): đặt `res.status = "MANUAL_REVIEW"` + `break`.
4. `follow_engine.py` dòng 833: `if mode in ("1", "both") and res.status == STATE_OK:` → Module 1 bị **khóa hoàn toàn** vì status không còn là OK.
5. Cả 27 máy đều dừng sau 1-5 phút, không chạy được lượt follow bù nào.

## Fix đã áp dụng (2026-09-25)
### mode2_follow_followers.py
**Anchor 1 — tap tab chủ động:**
Thêm vào poll loop trong `_open_following_tab`: nếu tab chưa selected, tìm node `android:id/text1` chứa "đã follow/following" và `tap_center` ngay, không đợi timeout.

**Anchor 2 — safe-skip thay vì abort:**
Thay `res.status = "MANUAL_REVIEW" + break` bằng:
- Log warning rõ anchor và lần thử.
- Ghi `res.details["mode2_degraded"] = True` + `res.details["mode2_degraded_reasons"].append(reason)`.
- `_back_to_feed(engine)` hoặc `recover_ui` để trở về Feed.
- `continue` sang anchor tiếp theo; **KHÔNG đặt failed, KHÔNG break**.

### multi_machine_feed_session.py (follow hook parser)
- Sau `result.update(terminal_payload)`: đọc `details.mode2_degraded` từ FOLLOW_RESULT payload, gán `result["mode2_degraded"] = True`.
- `_write_follow_result result_log`: nếu `mode2_degraded`, ghi `"script_error"` (không phải `"ok"`).
- Alert predicate: `elif (returncode != 0 or failed or status != "OK" or contract_error or mode2_degraded)`.
- `error_reason`: ưu tiên hiển thị `"mode2_degraded: <reasons>"` khi có cờ.

## Phân tích follow chéo vs follow tự nhiên (pitfall đối soát)
Follow tự nhiên (Feed): click nút `+` trực tiếp trên video đang phát → cực đơn giản, không chuyển màn hình.
Follow chéo (Module 2): cần mở profile Anchor → mở tab Đã follow → duyệt danh sách nội bộ. Hai population khác nhau; follow tự nhiên thành công không đồng nghĩa module 2 hoạt động.

**Khi user hỏi "tại sao follow chéo ít dù nick đó follow tự nhiên được":**
→ Không giải thích bằng nhóm máy ineligible/skipped (dưỡng sinh, thiếu video...).
→ Phải đọc `follow_result.json` của chính các máy đó và trace qua code path module 2.

## Quy tắc Farm Alert khi module 2 degraded nhưng module 1 thành công
- `status=OK, failed=0` KHÔNG miễn trừ Farm Alert nếu `mode2_degraded=True`.
- Alert phải nêu: nick (@username), machine (MN), anchor lỗi, reason, và kết quả fallback module 1.
- Watchdog cron đọc `script_error/degraded` trong log để đối soát; không dựa vào `result_log=ok`.
