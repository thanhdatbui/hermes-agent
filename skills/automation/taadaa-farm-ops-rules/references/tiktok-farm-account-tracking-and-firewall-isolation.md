# TikTok Farm Account Tracking, WAF Bypass, and Service Isolation Rules (2026-09-17)

## 1. CẤM CHÈN ROUTE VÀO PRODUCTION WEB SERVICE ĐANG HOẠT ĐỘNG (MikroTik Web Port 2310)
- **Sự cố thực tế**: Khi user yêu cầu đưa TikTok Dashboard lên web xem qua điện thoại, Coordinator đã cho worker chèn route `/tiktok` trực tiếp vào `D:/Taadaa/AI-Tools/tools/mikrotik_web/server.py` và restart process. Hậu quả làm treo và mất kết nối toàn bộ hệ thống quản lý MikroTik đang dùng hàng ngày trên điện thoại của user (`kibe:2310`), gây gián đoạn nghiêm trọng.
- **Quy tắc bất biến**:
  1. TUYỆT ĐỐI CẤM can thiệp, vá code hoặc restart các web server production đang chạy (như MikroTik Web Manager `server.py` port 2310).
  2. Mọi web tool, dashboard phụ trợ BẮT BUỘC chạy độc lập trên process và port riêng biệt (ví dụ port `1905`, `20130`), cấu hình bind `0.0.0.0`.
  3. Khi gặp sự cố kết nối, lập tức revert file `.bak` sạch và restart đúng runtime gốc.

## 2. BẪY WINDOWS FIREWALL PER-PYTHON-BINARY INBOUND RULES
- **Hiện tượng**: Web server lắng nghe trên `0.0.0.0:1905` hoặc `2310`, curl local pass 200, nhưng điện thoại kết nối qua LAN (`192.168.110.x`) hoặc Tailscale (`100.88.x.x`) bị timeout / "Máy chủ ngừng phản hồi".
- **Nguyên nhân cốt lõi**: Windows Defender Firewall quản lý Inbound Rules theo từng đường dẫn binary cụ thể:
  - `C:\Users\Kibe\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe` (Python 3.11 mặc định hệ thống): ĐÃ ĐƯỢC Allow Inbound.
  - `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe` (Python 3.12 mới): Tự động bị Windows tạo rule **Block Inbound TCP/UDP**.
- **Quy tắc chuẩn hóa**: Các web dashboard nội bộ phục vụ xem qua mạng LAN/Tailscale BẮT BUỘC khởi chạy bằng môi trường Python 3.11 (`cmd.exe /c "python D:\Taadaa\tools\..."`), CẤM chạy qua venv Python 3.12 chưa mở firewall.

## 3. CƠ CHẾ PUBLIC SCRAPING TIKTOK & PHÂN BIỆT SLARDARWAF VS DIE/NOT_FOUND
- **Kỹ thuật vượt WAF không cần login/cookie**:
  - Desktop User-Agent bị máy chủ TikTok chặn bởi `SlardarWAF` (HTML ~1400 bytes, trả về HTTP 200 nhưng không có dữ liệu tài khoản).
  - Mobile Safari User-Agent (`Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 ...`) được TikTok trả về HTML hoàn chỉnh (>230KB) chứa khối JSON ẩn:
    `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">`
- **Bẫy kết luận ảo 568 nick DIE**:
  - Khi quét 600 nick dồn dập từ 1 IP, TikTok kích hoạt rate-limit và trả về trang `SlardarWAF`. Nếu code coi "không thấy JSON" là nick DIE $\rightarrow$ báo sai 99% farm die.
  - **Quy tắc phân loại**:
    + Nếu có `__UNIVERSAL_DATA_FOR_REHYDRATION__` và `statusCode == 10221`: Nick THẬT SỰ DIE / NOT_FOUND.
    + Nếu HTML chứa `SlardarWAF` hoặc `slardar`: BẮT BUỘC đánh dấu `RATE_LIMITED` và kích hoạt xoay vòng proxy retry, TUYỆT ĐỐI CẤM gán nhầm thành `NOT_FOUND`.

## 4. QUY TẮC KHO 67 PROXY CANONICAL CỦA FARM
- **Hiện tượng**: Script tự động quét đĩa gom tất cả các file chứa chữ "proxy", cộng dồn cả file direct, file combined admin và dải port forward nội bộ 20001..20032 thành con số 157 proxy ảo.
- **Quy tắc chuẩn**:
  - Dải proxy 4G chuẩn của Farm Kibe gồm đúng **67 proxy**, lưu tại:
    `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (định dạng `host:port:user:pass`).
  - Khi parse vào `urllib.request` / `requests`: BẮT BUỘC dùng `urllib.parse.quote(safe="")` encode user và pass vì chứa ký tự `#` và `!` (`TaadaaMobi%232026%21`).
  - Không nạp chéo với file proxy admin hay duplicate URL direct IP.

## 5. TIÊU CHUẨN ĐÁNH GIÁ "CẮN ĐỀ XUẤT" (VIRAL TRENDING CRITERIA)
- Với dàn Farm ~600 nick nuôi quét snapshot 1 ngày 1 lần (07:00 sáng):
  - **Viral Spike (Bùng nổ like)**: $\Delta$ Like $\ge 500$ tim trong 24h $\rightarrow$ Chỉ số chuẩn xác nhất của video cắn view FYP.
  - **Trending Follower**: $\Delta$ Follower $\ge 50$ follow trong 24h.
  - **Quy tắc Baseline**: Sau các đợt scan lỗi/WAF (bản ghi rác 0 follower), BẮT BUỘC dọn sạch DB snapshots lỗi trước khi tính delta, tránh việc lấy số thật trừ 0 làm toàn bộ farm bị gắn cờ cắn đề xuất ảo.
