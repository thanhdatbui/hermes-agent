# Triage Lỗi Header Workbook Ngoặc Đơn & Admin Proxy Loopback (17/10/2026)

## 1. Lỗi Header Workbook `Missing required fields: Folder Video`
- **Triệu chứng**: Khi chạy runner upload (ví dụ `run_canary_m42.py`), runner báo:
  `Đọc workbook lần 1/5 thất bại: Missing required fields: Folder Video`
- **Nguyên nhân cốt lõi**:
  - Workbook `Tik*.xlsx` (Tik1..Tik8) sử dụng tiêu đề cột mở rộng:
    `Folder Video (Render Dich)` và `Video Goc (Nguon Cao)`.
  - Bộ từ điển `CANONICAL_HEADERS` trong `scripts/tiktok_workflow/account_source.py` trước đây chỉ khai báo alias `"folder video", "video folder"`, khiến hàm `canonical_header()` trả về chuỗi rỗng và hàm `validate_row()` từ chối.
- **Giải pháp O(1)**:
  - Bổ sung alias vào `CANONICAL_HEADERS`:
    ```python
    "Folder Video": {
        "folder video", "video folder",
        "folder video (render dich)", "folder video render dich", "sttvideo",
    },
    "video gốc": {
        "video goc", "video source", "source video",
        "video goc (nguon cao)", "video goc nguon cao",
    }
    ```
  - **Lưu ý Windows Line Endings**: Chuẩn hóa file về LF (`fix_crlf_temp.py`) trước khi commit để tránh diff phình toàn file. Commit chuẩn `[L2-surgery]` và đồng bộ file sang host Admin.

## 2. Downloader Admin Chạy Ngầm Nhưng Văng 502 Bad Gateway
- **Triệu chứng**: `tasklist` thấy `download_by_niche.py` vẫn chạy trên Admin nhưng file log `download_admin_p10.log` xuất hiện hàng loạt:
  `ProxyError: ('Unable to connect to proxy', OSError('Tunnel connection failed: 502 Bad Gateway'))`
- **Nguyên nhân cốt lõi**:
  - File cấu hình proxy trên Admin (`proxy_pool_69.txt`) cấu hình domain ngoài: `mirotik1.taadaa.click:10001..10035`.
  - Khi host Admin (`192.168.110.119`) cùng dải LAN gọi vòng ra domain WAN, router MikroTik từ chối loopback proxy.
- **Giải pháp O(1)**:
  - Thay thế toàn bộ `mirotik1.taadaa.click:` bằng IP LAN MikroTik `192.168.110.2:`.
  - **HOT-RELOAD**: Bắt buộc kill tiến trình con `download_by_niche.py` cũ để supervisor (`run_admin_downloader_service.py`) khởi động lại tiến trình mới nạp cấu hình proxy từ disk.
