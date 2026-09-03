# Checklive Runner Failure Isolation Pattern (2026-08-28)

## Bối cảnh
Khi chạy cron checklive kho hàng buổi sáng (`daily_manual_stock_checklive.py`), tiến trình duyệt qua nhiều sản phẩm:
- SP 40 (TikTok): Gọi cookie qua Camoufox + proxy kết nối tới khommo247 API.
- SP 57 (Instagram): Gọi Playwright/CDP kết nối tới clonefbig.com.
- Các SP up tay khác (SP 38, 39, 60, 61...): Đọc số lượng tồn kho và die từ VPS MySQL database.

## Vấn đề
Nếu một bên thứ ba (như khommo247) gặp lỗi mạng (`NS_ERROR_NET_TIMEOUT`, 502, hoặc hết hạn cookie) mà vòng lặp `for sid in SP_MAP` không bọc `try/except` độc lập, ngoại lệ sẽ làm crash script `daily_manual_stock_checklive.py` ngay ở SP 40.
Hậu quả:
1. SP 57 (IG) không được check live dù clonefbig và CDP browser vẫn hoạt động bình thường.
2. Số lượng tồn kho và biến động bán hàng của toàn bộ sản phẩm khác không được tổng hợp.
3. Không gửi được báo cáo trạng thái qua Telegram bot.

## Giải pháp chuẩn hóa
Bọc `try/except Exception` độc lập trong từng vòng lặp SP:
```python
for sid, (name, ctype) in SP_MAP.items():
    if sid not in all_stock:
        continue
    info = all_stock[sid]
    res = {"live": [], "die": [], "fail": [], "deleted": 0}
    try:
        if ctype == "tiktok" and info["items"]:
            res = check_tiktok(info["items"])
        elif ctype == "ig" and info["items"]:
            res = check_ig(info["items"])
    except Exception as e:
        log(f"❌ LỖI checklive SP {sid} ({name}): {e}")
        res = {"live": [], "die": [], "fail": info.get("items", []), "deleted": 0}
    
    # Tiếp tục tính delta, cập nhật state và tạo dòng báo cáo cho SP này
```
Đảm bảo khi 1 nguồn lỗi, kết quả các nguồn khác vẫn ghi nhận và tin nhắn tổng kết kho vẫn gửi về bot đầy đủ.
