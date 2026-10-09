# Quy trình Điều tra & Phục hồi Alert Transient Network Marker

Khi nhận Farm Alert với signature:
`detector-miss:network/error/retry marker detected` (thuộc phân loại `TAXONOMY_DETECTOR` hoặc `manual-needed:network` do `classifier.py` gán khi thấy text "Thử lại", "Không có kết nối Internet", v.v.):

## 1. Trích xuất Hiện trường & Canary O(1)
- Lệnh inspect: `python D:/Taadaa/tools/inspect_machine.py <N>`
- Kiểm tra focus: nếu focus đã về `LauncherActivity` hoặc màn hình Sleep/Dozing -> session nuôi feed đã kết thúc vòng đời an toàn và nhả lock.
- Nghiệm thu visual bằng chứng: chụp screencap màn hình kiểm tra (đáp ứng Gate 6 Visual Evidence).

## 2. Rà soát Upstream Proxy vs Forwarding Port
1. Lấy thông tin proxy gán thiết bị từ `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (cột Proxy upstream) và `settings get global http_proxy` (`192.168.110.2:200xx`).
2. Probe kết nối upstream bằng Python urllib/requests:
   - Thử GET tới endpoint kiểm tra IP/health (`http://httpbin.org/ip`) qua proxy.
   - Đo độ trễ (latency): nếu độ trễ <= 3.0s và IP trả về hợp lệ -> đường truyền proxy hiện tại LIVE bình thường.
3. Nguyên nhân gây alert: Khi đồng loạt 80-160 máy cùng chạy feed lúc bắt đầu ca, có thể xảy ra hiện tượng **transient network spike** (nghẽn mạng nhất thời 1-2 phút) khiến TikTok hiển thị màn hình retry.

## 3. Kỷ luật Quyết định (Code Surgery vs Non-Code Blocker)
- **TUYỆT ĐỐI KHÔNG** vội vàng sửa code monolith (`feed_swipe_smoke.py`) khi upstream proxy bị nghẽn mạng cục bộ hoặc chập chờn nhất thời.
- Nếu cả cụm proxy đã hồi phục 100%, thiết bị đã về Home sạch sẽ, không kẹt lock -> Kết luận transient network spike, báo cáo toàn farm và mở lại fleet an toàn.
