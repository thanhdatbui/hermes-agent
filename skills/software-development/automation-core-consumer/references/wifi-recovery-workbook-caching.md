# Stage 2 Wi-Fi Recovery & Workbook Lookup Caching Pattern

## Bối cảnh & Tiêu chuẩn Closeout Gate
Khi triển khai logic Stage 2 Wi-Fi recovery (ví dụ: fallback dùng `com.steinwurf.adbjoinwifi`) trong consumer preflight (`vpn_preflight.py`), cần tra cứu số máy và thông tin Wi-Fi (SSID, Password) từ mapping workbook (`PROXYgandienthoai.xlsx`).

## Pitfalls & Nguyên nhân rớt Closeout Gate
1. **Đọc trực tiếp openpyxl mỗi lần gọi**: Khiến preflight bị chậm nghiêm trọng do đọc/parse file Excel lặp đi lặp lại trên từng vòng lặp retry hoặc từng device thread.
2. **Nuốt toàn bộ ngoại lệ bằng `pass`**: Che giấu lỗi I/O, lỗi schema hoặc lỗi corrupted file, gây khó khăn cho việc giám sát hạ tầng farm.
3. **Thiếu telemetry logging**: Hệ thống telemetry (`_VPN_TIMEOUT_LOGGER`) không nhận được sự kiện khi:
   - Tra cứu thất bại (serial không tồn tại hoặc workbook rỗng/lỗi).
   - Tra cứu thành công (kèm SSID resolve được).
   - Cache hit / miss.

## Mô hình chuẩn (Thread-Safe In-Memory Cache)
- Dùng `threading.Lock()` bảo vệ cache dictionary `_WIFI_CREDENTIALS_CACHE: dict[str, tuple[str, str] | None]`.
- Lưu `_WIFI_WORKBOOK_CACHE_KEY` dựa trên file path và `st_mtime` để tự động invalidation khi workbook được cập nhật.
- Đảm bảo hàm reset cache (như `reset_proxy_mapping_cache()`) xoá sạch cache để các unit tests chạy độc lập.
- Ghi log telemetry rõ ràng qua logger chuyên dụng (`_VPN_TIMEOUT_LOGGER.info` / `warning` / `error`).
