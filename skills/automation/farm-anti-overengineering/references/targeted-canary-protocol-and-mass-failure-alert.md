# Targeted Canary Architecture & Anti-Unbounded Session Protocol

Đúc kết từ sự cố ngày 14/09/2026: Agent chạy full-session khi canary gây timeout 360s, chụp ảnh non lúc máy ở màn hình tìm kiếm, và thiết kế 4 tầng bảo vệ được thẩm định bởi Claude Code CLI (Opus Architecture Review).

---

## 1. Bản chất sự cố & Bài học xương máu (Root Cause)

| Hiện tượng | Sai lầm của Agent | Hậu quả |
|---|---|---|
| Sửa bug selector mở tab Following trong Mode 2 | Gọi lệnh full session: `run_follow --machine 10 --account-row-index 2 --mode 2` | Chạy toàn bộ chu trình nuôi acc (budget 18 follows, xem video 10-15 phút) |
| Timeout tool 360s | Không có trần budget/thời gian riêng cho canary | Worker bị ngắt giữa chừng khi máy mới mở trang Search |
| Báo cáo sai sự thật | Chụp screencap vội khi hết budget calls | Ảnh nghiệm thu là màn hình tìm kiếm ban đầu, chưa vào màn hình đích |

---

## 2. Thiết kế 4 tầng bảo vệ tuân thủ (Defense-in-Depth)

Theo thẩm định từ Senior Architect Claude Code:

### Lớp 1: Hard Guard CLI (Chặn đứng vật lý tại cửa ngõ)
Không tin vào "trí nhớ" của Agent. Khi lệnh gọi chứa cờ canary, CLI bắt buộc phải có đủ **bộ tam giác**:
`--canary-hook <hook_name>` + `--canary-target <UID>` + `--canary-screencap <path>`
Nếu thiếu bất kỳ cờ nào hoặc cố tình gọi full session nuôi acc trong bối cảnh test:
-> CLI lập tức `sys.exit("[HARD GUARD] Missing required canary flags")` trước khi thực thi logic nghiệp vụ.

### Lớp 2: Bounded Budget Ceiling (Trần ngân sách kỹ thuật bất khả xâm phạm)
Canary mode có trần cố định bằng code, **CẤM KẾ THỪA** config của session nuôi thông thường:
- `budget_follows`: **Cố định = 1** (Cấm truyền 15–18).
- `timeout_sec`: **Cố định <= 55s** (Tự ngắt fail-fast trước 60s).
- Bỏ qua mọi chu kỳ delay người dùng (delay 15-30s xem video).

### Lớp 3: Semantic Screen Assertion (Nghiệm thu ảnh chụp đúng màn hình đích)
- Chụp ảnh screencap chỉ được lưu nếu thiết bị đã được chứng minh đứng ở **đúng màn hình đích**.
- Kiểm tra fingerprint UI XML (ví dụ: RecyclerView `uzs` hoặc header text `"Đang follow"`) trước khi gọi `screencap()`.
- Nếu chưa vào đúng màn hình đích: ném `[SCREEN ASSERT FAIL]`, **CẤM LƯU ẢNH CHỤP**. Điều này triệt tiêu hoàn toàn lỗi chụp ảnh non / false-positive.

### Lớp 4: Quy chuẩn thao tác Coordinator (Checklist & Lệnh chuẩn)
Lệnh mẫu chuẩn hóa bắt buộc:
```bash
python -m follow_runner.run_follow \
  --machine <N> \
  --canary-hook <tên_hàm_vừa_sửa> \
  --canary-target <1_UID_duy_nhất> \
  --canary-screencap <đường_dẫn_ảnh>
```

---

## 3. Quy tắc Farm Alert Gate: Lỗi diện rộng >10 máy
- Watchdog phiên (`feed_session_watchdog.py`) phải theo dõi cả 3 khâu: Lướt Feed, Follow Hook, Upload Hook.
- Nếu **bất kỳ khâu nào có > 10 máy lỗi** (ví dụ: 13 máy lỗi UI mở tab Follow do TikTok đổi layout):
  -> **BẮT BUỘC** hú còi báo động đỏ `[FARM ALERT]` trực tiếp về Telegram chat ID `-5373649734`.
  -> Không được để tỷ lệ thành công tổng thể (như Feed 84%) che khuất lỗi mass failure 100% của Follow hook.
