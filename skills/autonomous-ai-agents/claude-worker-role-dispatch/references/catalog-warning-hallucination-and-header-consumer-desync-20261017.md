# Incident Analysis: Catalog Warning Hallucination & Header Consumer Desync (17/10/2026)

## 1. Sự Cố 1: Lỗi "Đổi Header Excel Nhưng Không Rà Soát Consumer Code"

### Bối cảnh
Ở session trước, để phân định rõ ràng giữa video render và video gốc, các header file Excel được đổi tên:
- `Tik1..Tik8.xlsx`: `Folder Video` -> `Folder Video (Render Dich)`
- `taikhoan_dat_v2_updated .xlsx`: `Folder Video` -> `Folder Video (Slot 1-640)`

### Lỗi phát sinh
Các script Python đọc các file này kiểm tra cứng tuple header:
- `upload_preflight.py`: chỉ match `("folder video", "video folder", "tik")` -> Bị skip toàn bộ ca đăng video do không nhận ra `Folder Video (Render Dich)`.
- `sync-safe-workbook.py`: chỉ match `("folder video", "folder", "thu muc")` -> `folder_col = None`.
Khi mất cột folder, script không thể tính được công thức toán `(Folder - 1) % 8 + 1` để phân slot, dẫn đến fallback bốc tuần tự các dòng từ trên xuống dưới. Các máy có dòng bị xáo trộn vị trí trong Master DAT (như M76-M79) bị đảo lộn toàn bộ 8 slot giữa các file Tik, gây văng lỗi `profile username still mismatched after switch` hàng loạt.

### Giải pháp chuẩn hóa
1. **Mở rộng tuple alias nhận diện header**: Mọi consumer script đọc header bắt buộc dùng alias regex bao quát:
   `("folder video slot 1 640", "folder video", "folder", "thu muc", "render dich")`
2. **Khóa bằng regression test**: Bắt buộc thêm test case assert trực tiếp các header mới trong `test_upload_preflight_headers.py` và `test_hermes_taikhoan_sync_cron.py`.

---

## 2. Sự Cố 2: Bẫy Warning Model Catalog & Đổi Bậy Role Worker

### Bối cảnh
Khi chạy Claude Code CLI (v2.1.281) với `--model claude-haiku-5-5`, CLI in ra cảnh báo:
`"claude-haiku-5-5" isn't described by this version's model catalog; update Claude Code...`

### Phản ứng sai lầm của Coordinator
- Coordinator ngộ nhận cảnh báo này là CLI không hỗ trợ Haiku và cho rằng Haiku bị lỗi.
- Tự tiện đề xuất đổi role `worker` trong `claude_worker.py` từ `claude-haiku-5-5` sang `claude-sonnet-5-5`, vi phạm nghiêm trọng chỉ đạo của Operator (Haiku làm thợ gõ code O(1) tiết kiệm quota, Sonnet chỉ dùng cho Planner/Reviewer).
- Đồng thời hallucination nhắc đến "Claude 3.5 Sonnet", trong khi Operator dùng độc quyền thế hệ 5.5.

### Bản chất kỹ thuật
- Warning `[claude-code:unrecognized_model]` chỉ là advisory của Node.js CLI khi model id chưa nằm trong hardcoded catalog cục bộ, request vẫn gửi về Anthropic API và Haiku VẪN CHẠY BÌNH THƯỜNG.
- Lý do worker bị `Reached max turns (15)` không phải do model, mà do Coordinator:
  1. Truyền prompt dạng multiline trần hoặc prompt mở ("xem file remediate_prompt.txt") qua Windows subprocess khiến CLI bị truncate hoặc đi đọc file lan man.
  2. Bỏ qua cổng điều phối chuẩn `dispatch_worker.py` (nơi đã có sẵn logic sanitize 1 dòng và retry O(1)).
