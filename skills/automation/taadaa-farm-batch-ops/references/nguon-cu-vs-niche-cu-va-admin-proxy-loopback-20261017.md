# Nguồn Cũ vs Niche Cũ & Bẫy Proxy Loopback LAN Admin (Session 2026-10-17)

## 1. Phân Biệt Sắc Bén: "Nguồn Cũ" vs "Niche Cũ" (User Correction)
- **Lời chỉnh đốn của User**: *"T hỏi nguồn cũ chứ k phải niche cũ"*.
- **Bài học cốt lõi**:
  - Khi User hỏi về **"nguồn cũ"**, User đang hỏi về **CHÍNH XÁC KÊNH / CREATOR GỐC** (1 folder = 1 kênh / 1 nhân vật duy nhất).
  - CẤM TUYỆT ĐỐI nhầm lẫn sang giải thích về "niche cũ / niche mới" hay thuật toán phân loại ngách.
  - **Bất biến 1 Folder = 1 Creator**: Mọi thao tác tải bù, render bù BẮT BUỘC phải lấy từ đúng kho video gốc của kênh đó (`D:\video goc\<src_id>`). Tuyệt đối không cào nhồi video của nhân vật/kênh khác vào folder cũ làm lẫn lộn khuôn mặt và avatar của nick.

## 2. Bẫy Header Workbook Ngoặc Đơn: `Folder Video (Render Dich)`
- **Hiện tượng**: Runner upload văng lỗi:
  `Missing required fields: Folder Video`
- **Nguyên nhân**: File `Tik*.xlsx` (Tik1..Tik8) sử dụng tiêu đề chi tiết: `Folder Video (Render Dich)` và `Video Goc (Nguon Cao)`.
- **Khắc phục chuẩn hóa**:
  - `CANONICAL_HEADERS` trong `scripts/tiktok_workflow/account_source.py` bắt buộc bổ sung alias:
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
  - **Kỷ luật Line Endings CRLF trên Windows**: Khi sửa `account_source.py`, luôn chạy script chuẩn hóa byte `\r\n` -> `\n` để đưa `git diff --numstat` về phạm vi O(1) (< 20 dòng), tránh bẫy phình diff làm hỏng Closeout Gate.
  - Đồng bộ `account_source.py` đã vá sang cả máy Admin (`admin-farm`).

## 3. Bẫy Proxy Loopback LAN Trên Máy Admin (502 Bad Gateway)
- **Hiện tượng**: Tiến trình cào `download_by_niche.py` trên Admin vẫn chạy nhưng log liên tục văng:
  `ProxyError: ('Unable to connect to proxy', OSError('Tunnel connection failed: 502 Bad Gateway'))`
- **Nguyên nhân gốc rễ**:
  - File `proxy_pool_69.txt` trên Admin chứa domain ngoài `mirotik1.taadaa.click:10001..10035`.
  - Host Admin (`192.168.110.119`) nằm trong mạng LAN khi kết nối loopback ra ngoài qua domain WAN thì bị router MikroTik từ chối/báo 502.
  - Trong khi đó, kết nối trực tiếp vào IP LAN `192.168.110.2:10001..10035` hoàn toàn thông suốt (`TcpTestSucceeded : True`).
- **Bẫy Cache Proxy Trong Bộ Nhớ RAM (Hot-Reload Invariant)**:
  - Chỉ sửa file `proxy_pool_69.txt` trên đĩa là CHƯA ĐỦ! Tiến trình con `download_by_niche.py` đang chạy vẫn giữ danh sách proxy cũ trong RAM.
  - BẮT BUỘC phải kill các tiến trình Python downloader cũ (`download_by_niche.py`), để supervisor service (`run_admin_downloader_service.py`) tự động respawn tiến trình mới đọc danh sách proxy đã chuẩn hóa sang IP LAN.
