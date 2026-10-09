# Telegram Gateway Media Download Resiliency & Retry Architecture

## 1. Triệu chứng & Bối cảnh Sự Cố
- **Hiện tượng**: User gửi ảnh chụp màn hình hoặc file ảnh qua Telegram, bot phản hồi:
  `⚠️ Couldn't download your photo (NetworkError). Please try sending it again.`
  hoặc trong session prompt xuất hiện ghi chú:
  `[The user attempted to send a photo but it could not be downloaded (NetworkError); they have been asked to retry.]`
- **Ảnh hưởng phụ nghiêm trọng**: Người dùng thấy bot bị "treo" 5–10 phút không phản hồi. Thực tế, khi kết nối tới CDN của Telegram (`api.telegram.org/file/bot<token>/...`) bị nghẽn mạng ngầm, hàm download bị treo socket cho tới khi timeout tầng dưới văng ra, làm block event loop xử lý tin nhắn của Telegram Adapter.

## 2. Nguyên nhân Gốc Rễ
1. **Thiếu Retry & Timeout ở Tầng Tải Media**:
   Mã nguồn gốc của Telegram Adapter (`adapter.py`) trong các nhánh `msg.photo` và `msg.document`:
   ```python
   file_obj = await photo.get_file()
   image_bytes = await file_obj.download_as_bytearray()
   ```
   Hoàn toàn không có giới hạn `timeout` tường minh và không có cơ chế `retry`.
2. **Micro-Jitter trên Đường Truyền WARP SOCKS5**:
   Khi Telegram Gateway định tuyến qua Cloudflare WARP (`socks5://127.0.0.1:40000`), proxy thỉnh thoảng gặp micro-jitter:
   `httpx.ProxyError: Proxy Server could not connect: Host unreachable` (khoảng 1 trong 5–10 request bị chập chờn trong 1–2 giây).
   Nếu không có retry, một lần sụt mạng tức thời này sẽ làm sập hoàn toàn luồng tải ảnh của user.
3. **Biến Unbound & Null Reference Sau Vòng Lặp**:
   Nếu vòng lặp retry kết thúc thất bại hoặc ném exception, các biến phụ thuộc như `file_obj.file_path` có thể gây lỗi `UnboundLocalError` hoặc `AttributeError` nếu không được khởi tạo `None` và kiểm tra an toàn bằng `getattr(file_obj, "file_path", None)`.

---

## 3. Kiến Trúc Khắc Phục Chuẩn Hóa

### A. Tách Helper Tải File Chuyên Dụng (`_download_telegram_file_with_retry`)
Không nhúng trực tiếp vòng lặp `for attempt in range(3)` vào từng nhánh xử lý photo hay document. Tách thành method độc lập trên `TelegramAdapter`:
```python
async def _download_telegram_file_with_retry(
    self,
    media_item: Any,
    kind: str,
    timeout: float = 30.0,
) -> tuple[bytearray, Any]:
    """Download file from Telegram CDN with 3-attempt retry loop for network resiliency."""
    for attempt in range(3):
        try:
            file_obj = await asyncio.wait_for(media_item.get_file(), timeout=20.0)
            image_bytes = await asyncio.wait_for(file_obj.download_as_bytearray(), timeout=timeout)
            return image_bytes, file_obj
        except Exception as dl_err:
            if attempt < 2:
                logger.info("[%s] Retrying %s download (attempt %d/3): %s", self.name, kind, attempt + 1, dl_err)
                await asyncio.sleep(1.0)
                continue
            logger.warning("[%s] %s download failed after 3 attempts: %s", self.name, kind, dl_err)
            raise dl_err
    raise RuntimeError(f"Failed to download {kind} after 3 attempts")
```

### B. Sử Dụng An Toàn Tại Điểm Tiếp Nhận Media
Trong `_handle_media_message`:
```python
if msg.photo:
    try:
        photo = msg.photo[-1]
        image_bytes, file_obj = await self._download_telegram_file_with_retry(photo, "photo")
        ext = ".jpg"
        if file_obj and getattr(file_obj, "file_path", None):
            for candidate in [".png", ".webp", ".gif", ".jpeg", ".jpg"]:
                if file_obj.file_path.lower().endswith(candidate):
                    ext = candidate
                    break
        cached_path = cache_image_from_bytes(bytes(image_bytes), ext=ext)
        event.media_urls = [cached_path]
        ...
```
Áp dụng tương tự cho `msg.document` (ảnh gửi dưới dạng uncompressed document).

### C. Chuẩn Hóa Telemetry Audit Trung Tâm (`_record_telegram_audit_event`)
Tất cả các sự kiện vận hành quan trọng (degraded polling, recovery scheduled, media cache failure) đều phải được ghi có cấu trúc qua một helper chung:
```python
def _record_telegram_audit_event(self, event_type: str, data: dict) -> None:
    """Record structured gateway telemetry audit event to JSONL file."""
    try:
        audit_dir = Path(os.environ.get("TELEGRAM_AUDIT_LOG_DIR", "D:/Taadaa/runtime/audit_logs"))
        audit_dir.mkdir(parents=True, exist_ok=True)
        log_payload = {
            "event": event_type,
            **data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(audit_dir / "telegram_gateway_audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("[%s] Failed to record telegram audit event %s: %s", self.name, event_type, exc)
```
- Khi media download thất bại cả 3 lần: ghi event `MEDIA_CACHE_FAILURE` với đầy đủ `kind`, `error`, `error_type`, `display_name`.
- `TELEGRAM_AUDIT_LOG_DIR` cho phép test suite cô lập thư mục log qua `tmp_path` mà không làm ô nhiễm production logs.

---

## 4. Kỷ Luật Thẩm Định Độc Lập (Sol Auditor Gate)
Khi can thiệp vào tầng media và networking của Telegram Adapter:
1. **Kiểm thử Direct Method Execution**: Bắt buộc viết test gọi trực tiếp method production `_download_telegram_file_with_retry` trên adapter instance giả lập (mock `photo.get_file()` ném lỗi transient lần 1 rồi thành công lần 2) để chứng minh recovery thực sự.
2. **Kiểm thử Exhaustion Path**: Test trường hợp thất bại cả 3 lần phải ném đúng ngoại lệ, gọi `_surface_media_cache_failure` và ghi nhận event `MEDIA_CACHE_FAILURE` vào JSONL.
3. **Bảo tồn Clean Working Tree**: Trước khi chạy `closeout_gate.py`, biên dịch cú pháp bằng `py_compile`, chạy unit test tập trung, và đồng bộ code giữa repo source (`D:/Taadaa/Hermes/...`) và runtime package (`AppData/Local/hermes/...`).
