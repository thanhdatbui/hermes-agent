# Telegram 400 Message Too Long & Line-Aware Auto-Chunking Runbook

## Bối cảnh sự cố (2026-10-10)
Trong phiên chạy sáng, watchdog tổng hợp báo cáo Ca 1 (Row 2). Báo cáo lướt Feed được lưu bình thường, nhưng báo cáo Follow hoàn toàn không xuất hiện trên kênh Telegram `Tiktok Follow` (`-5127276494`), khiến User tưởng ca chạy bị mất hút hoặc bot ngừng hoạt động.

## Root Cause
1. **Telegram API 4096-Character Hard Ceiling**:
   - Khi có nhiều máy bị nhả follow hoặc danh sách proxy bị ngắt cầu dao (Circuit Breakers) dài (22 proxy kèm máy anh em được cứu), nội dung thông báo ghép đầy đủ vượt quá **4.500 – 5.500 ký tự**.
   - Telegram Bot API giới hạn độ dài mỗi tin nhắn là 4.096 ký tự. Lệnh `POST https://api.telegram.org/bot<token>/sendMessage` ném lỗi HTTP 400:
     ```json
     {"ok": false, "error_code": 400, "description": "Bad Request: message is too long"}
     ```
2. **Khối bắt lỗi nuốt ngoại lệ**:
   - Khối `try...except Exception as exc: logger.warning("[WATCHDOG_TELEGRAM_DISPATCH_FAIL] err=%s", exc)` bắt lỗi nhưng không ném ra ngoài và không có cơ chế retry/fallback chia nhỏ tin nhắn, làm mất hoàn toàn tin nhắn gửi tới nhóm.
3. **Lặp dữ liệu Cầu dao IP giữa các cụm**:
   - Đoạn format Cầu dao IP được gắn vào cả 2 khối cluster (Kibe và Admin), làm nội dung bị nhân đôi không cần thiết.

## Giải pháp Chuẩn Hóa (Line-Aware Chunking Pattern)

Mọi watchdog/script gửi tin nhắn tổng hợp dài qua Telegram API BẮT BUỘC áp dụng thuật toán chia nhỏ theo dòng an toàn:

```python
MAX_TELEGRAM_CHUNK_LEN = 3900  # Giữ biên an toàn dưới 4096 ký tự

def send_telegram_chunks(bot_token: str, chat_id: str, full_msg: str, timeout: int = 10):
    if not full_msg:
        return
    
    chunks = []
    if len(full_msg) <= MAX_TELEGRAM_CHUNK_LEN:
        chunks = [full_msg]
    else:
        curr_lines = []
        curr_len = 0
        for line in full_msg.splitlines(keepends=True):
            if curr_len + len(line) > MAX_TELEGRAM_CHUNK_LEN:
                if curr_lines:
                    chunks.append("".join(curr_lines))
                curr_lines = [line]
                curr_len = len(line)
            else:
                curr_lines.append(line)
                curr_len += len(line)
        if curr_lines:
            chunks.append("".join(curr_lines))

    for idx, chunk in enumerate(chunks):
        body = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": chunk
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=body
        )
        urllib.request.urlopen(req, timeout=timeout)
```

## Checklist Phòng Ngừa
1. **Line-aware Split**: Không cắt ngang giữa dòng chữ hoặc bảng markdown làm vỡ cấu trúc hiển thị trên Telegram.
2. **Cluster Isolation**: Các bảng thông số dùng chung toàn farm (như IP Circuit Breaker) chỉ xuất 1 lần tại cụm đại diện (ví dụ Kibe), không in lặp lại ở cụm khác.
3. **Safe Buffer**: Luôn dùng ngưỡng trần 3.900 ký tự thay vì sát 4.096 ký tự để tránh lỗi tính toán chênh lệch encoding UTF-8 / ký tự đặc biệt.
