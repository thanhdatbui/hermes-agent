# TikTok Public Tracking, SlardarWAF Bypass & 67-Proxy Pool

## 1. Bối cảnh & Hiện tượng (Session 2026-09-17)
Khi theo dõi chỉ số tài khoản TikTok (Follower, Like, Video, UID, SecUID, trạng thái Live/Die) tự động từ danh sách farm (`taikhoan_run_safe.xlsx` ~592 accounts):
- TikTok cho phép đọc public profile thông qua HTML nhúng hydration JSON `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` khi dùng User-Agent mobile (Safari iPhone).
- **Bẫy Rate-Limit & False Positive DIE (568 nick báo nhầm DIE)**:
  - Khi gửi dồn dập hàng trăm request từ 1 IP máy tính duy nhất trong thời gian ngắn, TikTok kích hoạt Slardar WAF.
  - Phản hồi trả về trang HTML ~1400 bytes chứa `slardarClient: SlardarWAF` và **hoàn toàn không có thẻ script hydration JSON**.
  - **Sai lầm tai hại**: Nếu parser chỉ kiểm tra "không thấy hydration JSON -> kết luận NOT_FOUND / DIE", toàn bộ dàn nick sống sẽ bị gán nhầm là nick DIE!
  - **Quy tắc phân biệt**:
    + Nick DIE / BANNED thật: TikTok trả về JSON hợp lệ với `statusCode == 10221` hoặc `userInfo == None`.
    + Nick bị Rate-limit / Chặn WAF: HTML chứa `SlardarWAF` / `slardar` -> Gán trạng thái `RATE_LIMITED` và bắt buộc retry qua proxy khác trong pool.

## 2. Kho 67 Proxy của Farm Taadaa
Farm sở hữu dải 67 proxy 4G xoay vòng, lưu tại các nguồn chuẩn:
1. `D:/Taadaa/Tiktok-video/proxy_pool_67.txt` (57 proxy chính)
2. `D:/Taadaa/Tiktok-video/proxy_pool_67_direct.txt`
3. `D:/OneDrive/TaadaaData/proxy_combined_pool.txt` (66 proxy, gồm các dải MikroTik 10008..10012)
4. `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx` (bảng gán proxy theo máy)

### Quy tắc URL-Encode Proxy:
- Mật khẩu proxy thường chứa ký tự đặc biệt `#` và `!` (ví dụ: `TaadaaMobi#2026!`).
- Bắt buộc dùng `urllib.parse.quote(..., safe="")` để chuyển thành `TaadaaMobi%232026%21`.
- Chuỗi proxy HTTP chuẩn: `http://{user_enc}:{pwd_enc}@{host}:{port}` (ví dụ: `http://mobi2:TaadaaMobi%232026%21@test.taadaa.click:5102`).

## 3. Kỷ luật Sol Planner trước khi Dispatch
- Khi user yêu cầu lập kế hoạch can thiệp, xây tool, hoặc sửa luồng, Coordinator **BẮT BUỘC** gọi Sol Brain (:20129) qua `D:/Taadaa/tools/sol_planner.py` để sinh Plan Tầng A trước khi dispatch worker:
  `python D:/Taadaa/tools/sol_planner.py --goal "<Mục tiêu>" --file "<File đích>"`
- Tuyệt đối CẤM Coordinator tự ý dispatch worker khi chưa qua Sol Planner.
