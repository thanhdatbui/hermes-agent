# Worker timeout và đối soát workbook farm — bài học 2026-09-25

## 1. Không nhầm mục tiêu khi user đổi lệnh
Khi user nói “fix”, xác định object cần fix trong câu mới nhất. Nếu user vừa yêu cầu sửa timeout của worker/subagent thì không tiếp tục sửa workbook farm; dừng worker cũ nếu có thể và đổi contract sang timeout/runtime.

## 2. Timeout lồng nhau phải được tính trước
Log mẫu:
```text
[OmniRouteClient] Attempt 1/3 failed: ... Read timed out. (read timeout=300)
[Command timed out after 600s]
Subagent 0 timed out after 600.1s
```
Nếu `max_retries=3`, `timeout=300s`, tổng chờ lý thuyết đã vượt ngân sách 600s (chưa kể retry delay). Worker sẽ bị executor kill trước khi trả lỗi có cấu trúc. Khi chạm lỗi này:
- định vị class/client bằng literal log (`OmniRouteClient`, `Attempt {attempt}/{max_retries}`, `read timeout`), không quét toàn ổ;
- giữ nguyên semantics khác, giảm per-attempt timeout và retry budget để tổng < 600s;
- ví dụ an toàn cho công cụ closeout: `timeout=60s`, `max_retries=2`, tổng khoảng 122s;
- backup file trước patch, rồi chạy syntax/import focused và probe local ngắn hạn nếu an toàn;
- nếu target không nằm trong root được phép, báo blocker/path thật, không đoán sửa API retry chung.

## 3. Claude CLI không thay thế coordinator verification
Dùng `claude -p` cho điều tra/sửa khi user yêu cầu, nhưng phải giới hạn path, `--allowedTools`, `--max-turns`, và yêu cầu exact files + old/new values + verification. Sau khi Claude kết thúc, coordinator phải tự đọc lại target và chạy focused verification; không báo thành công chỉ dựa vào summary.

## 4. Workbook mapping: phân biệt evidence mạnh và mapping suy đoán
Khi ID trống trong Tik workbook:
- đối chiếu `farm_account_info`, master workbook và các workbook Tik hiện hành;
- kiểm tra duplicate ID chéo toàn bộ Tik1..Tik8 trước khi ghi;
- nếu account hiện nằm ở slot khác hoặc chỉ xuất hiện trong backup lịch sử, gắn `BLOCKED`, không gán lại theo phỏng đoán;
- giữ nguyên machine/device/folder/video-count/keyword/hashtag trừ khi source-of-truth chứng minh cần đổi;
- ghi atomic qua `.tmp` rồi replace, reopen `data_only=True`, kiểm tra lại row và duplicate.

## 5. Phục hồi OneDrive overwrite
Nếu một mapping vừa sửa bị quay lại `MISSING_ID`, coi đây là overwrite/concurrent-sync issue, không phải patch thất bại. Trước khi sửa lại cần kiểm tra process/lock và mtime; sau đó atomic replace + readback. Không báo “đã fix” nếu readback hiện hành chưa đúng.
