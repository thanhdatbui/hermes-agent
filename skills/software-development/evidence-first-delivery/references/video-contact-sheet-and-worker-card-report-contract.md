# Video Contact Sheet O(1) & Worker Card Report Contract

Đúc kết từ bài học kiến trúc AnDanceOS (Trương Thành An) và chuẩn hóa vào hệ thống Taadaa Phone Farm (18/10/2026).

## 1. Video Contact Sheet O(1) cho Render Video TikTok

### Bản chất & Vấn đề giải quyết
- Khi batch render video TikTok (Tik1/Tik2/Tik3), video dài 60–90 giây thường nặng hàng chục MB.
- Nếu gửi file `.mp4`, User hoặc Coordinator phải tải về và tua xem từ đầu đến cuối rất mất thời gian.
- Nếu không kiểm tra hoặc chỉ kiểm tra exit code của FFmpeg thì dễ lọt các lỗi: phụ đề nhảy cỡ chữ, text bị che bởi các nút tương tác TikTok (Like/Share/Comment), khung hình đen (black frames), hoặc lệch khung dọc 9:16.

### Giải pháp kỹ thuật: Contact Sheet 3x3
- Sử dụng công cụ `D:/Taadaa/tools/video_contact_sheet.py`:
  1. Dùng `ffprobe` bóc tách thời lượng `duration` và độ phân giải thực tế.
  2. Tính toán $N = 9$ khung hình cách đều: `step = duration / (N + 1)`, lấy các mốc `step * 1, step * 2, ..., step * 9` để né hoàn toàn khung đen lúc mở đầu (fade-in 0s) và kết thúc (EOF).
  3. Dùng `ffmpeg -ss` fast-seek trích xuất từng khung hình, chuẩn hóa tỷ lệ 9:16 (360x640 per tile).
  4. Gắn badge mốc thời gian (`MM:SS`) ở góc trên mỗi ô.
  5. Dùng Pillow ghép thành 1 ảnh lưới JPEG duy nhất ($1080 \times 1920$).
- Gửi qua `MEDIA:<path_to_contact_sheet.jpg>`: User và Bot chỉ cần liếc mắt 1 giây là thẩm định trọn vẹn toàn bộ clip 60s.

### Cạm bẫy chí tử: CẤM áp dụng Contact Sheet cho UI Farm
- **BẪY GHÉP MÀN HÌNH UI (UI Screen-Stitching Trap):** Tuyệt đối CẤM ghép các màn hình thao tác Android (Feed, Switcher, Profile, Sửa hồ sơ) thành 1 ảnh lưới gửi 1 lần.
- **Lý do vi phạm:**
  1. Vi phạm nghiêm ngặt `GATE 6: MAX BLIND STEPS = 1` (Mọi thao tác thay đổi giao diện bắt buộc phải chụp và gửi ảnh ngay lập tức).
  2. Thu nhỏ ảnh màn hình làm vỡ nét chữ, khiến `WinRT OCR` đọc sai và làm hỏng so khớp thuật toán `pHash diff > 15`.

---

## 2. Thẻ Nghiệm Thu Công Việc Chuẩn Hóa (Worker Card Report)

### Vấn đề giải quyết
- Chống thói quen báo cáo văn vở, chat tự do thiếu cấu trúc của LLM ("Em làm xong rồi anh nhé...").
- Chống tình trạng báo cáo hoàn thành ảo khi chưa có artifact hoặc chưa kiểm định.
- Minh bạch ranh giới an toàn (Boundaries): Làm rõ việc gì đã làm và việc gì CHƯA ĐƯỢC PHÉP LÀM (Fail-Closed).

### Cấu trúc Thẻ Bắt Buộc (Card Schema)
Công cụ chuẩn: `D:/Taadaa/tools/worker_card_report.py` (hoặc module `WorkerCard`).

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 THẺ NGHIỆM THU CÔNG VIỆC — ✅ [HOÀN THÀNH / READY]
👷 Người làm: <Worker CLI / Script Runner>
🎯 Nhiệm vụ : <Tên task / Module>
⏱ Thời gian: <Thời lượng thực thi>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 SẢN PHẨM BÀN GIAO (ARTIFACTS):
  • File chính: D:/Taadaa/...
  • Log thực thi: D:/Taadaa/...
  📷 Bằng chứng thị giác: MEDIA:D:/Taadaa/.../contact_sheet.jpg

🔍 KIỂM ĐỊNH CHẤT LƯỢNG (VERIFICATION):
  • Focused Test: PASSED (X tests in Y.Zs)
  • Lint / Metrics: 0 errors

🛡️ RANH GIỚI AN TOÀN (BOUNDARIES - FAIL-CLOSED):
  [ĐÃ LÀM]:
    - Đã sửa logic hàm X
    - Đã chạy focused test offline
  [CHƯA LÀM]:
    - CHƯA commit git
    - CHƯA nạp lên thiết bị farm thật
    - CHƯA upload lên TikTok
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Quy tắc Thẩm định Fail-Closed của Card:
1. `worker`, `task`, `artifacts`, `verification`, `done_actions`, `not_done_boundaries` bắt buộc không được rỗng.
2. Trạng thái `SUCCESS` mà thiếu `artifacts` hoặc thiếu `verification` -> BỊ TỪ CHỐI (Validation Error).
3. Thiếu mục `[CHƯA LÀM]` -> BỊ TỪ CHỐI vì vi phạm nguyên tắc an toàn Fail-Closed.
