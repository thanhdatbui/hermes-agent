# Phân Tích Sự Cố Tách Nhóm Proxy `tb.taadaa.click` vs `test.taadaa.click` & Kỷ Luật Dò Lỗi Batch Tận Gốc (31/10/2026)

## 1. Triệu Chứng & Cạm Bẫy Chẩn Đoán "Cho Có Lệ" (Anti-Superficial Triage)
- **Cảnh báo:** Farm Alert báo batch chạy 79 máy trên cụm Admin (M201–M280) thất bại 34 máy (43%), chia làm 2 chữ ký:
  * 9 máy: `global proxy egress IP verification failed: ... proxyconnect tcp: dial tcp 192.168.110.2:202xx: connect: network is unreachable`.
  * 25 máy: `dumpsys connectivity: Wi-Fi not connected`.
- **Cạm bẫy đối phó / lười suy nghĩ của Coordinator:**
  * Chỉ inspect 1–2 máy canary đại diện (M203, M208) lúc batch đã kết thúc, thấy máy đang ở Home launcher, Wi-Fi đã tự re-join, pin tốt -> vội vàng kết luận "nghẽn mạng tạm thời / race condition".
  * Chạy `mobiproxy_auto_healer.py` thấy báo 32/32 ports HEALTHY -> vội kết luận cụm proxy 4G bình thường, khuyên mở lại toàn bộ fleet mà không đi sâu vào log thật.
  * Hậu quả: Bị User bắt bài vì lảm nhảm, trốn tránh việc tìm nguyên nhân thực sự.

## 2. Bản Chất Lỗi Gốc Rễ Từ Dữ Liệu Thật (Exact Root Cause)
- **Đối soát danh sách máy lỗi với `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`:**
  * Toàn bộ 80 máy Admin được chia làm 2 cụm proxy upstream:
    1. 48 máy trỏ cổng proxy nội bộ `192.168.110.2:10008..10035` (chạy qua Sing-box).
    2. 32 máy trỏ ra domain ngoại **`tb.taadaa.click:5141..5158`** (Tailscale IP: `100.115.94.49`).
  * **Trùng khớp 100%:** Toàn bộ 31 máy bị fail trong file chạy `taikhoan_run_safe.xlsx` đều thuộc chính xác danh sách 32 máy trỏ về `tb.taadaa.click`. 48 máy chạy qua `192.168.110.2` đều đạt kết quả 100% SUCCESS.
  * Node Tailscale / thiết bị chủ `tb.taadaa.click` (`100.115.94.49`) bị rớt kết nối hoặc sập dịch vụ (các cổng 5141..5158 đều timeout).

## 3. Vì Sao Sinh Ra 2 Chữ Ký Lỗi Khác Nhau?
- **Nhóm 1 (`egress IP verification failed`):** Các máy đang lưu cài đặt proxy nội bộ cũ `192.168.110.2:202xx`. Khi preflight chạy, Wi-Fi nội bộ thông suốt nhưng port nội bộ không forward được ra ngoài -> lỗi dial TCP `network is unreachable`.
- **Nhóm 2 (`dumpsys connectivity: Wi-Fi not connected`):** Các máy đã nhận proxy `tb.taadaa.click`. Do proxy sập hoàn toàn, cơ chế kiểm tra Captive Portal (Generate 204) của Android bị chặn -> Android đánh dấu Wi-Fi "Không có Internet" hoặc tự ngắt kết nối wlan0 -> dumpsys không còn cờ `CONNECTED`.

## 4. Điểm Mù Của Tool Giám Sát `mobiproxy_auto_healer.py`
- `mobiproxy_auto_healer.py` đang hardcode kiểm tra host `test.taadaa.click` (các cổng 5101..5138 phục vụ cụm Kibe M1–M80).
- Cụm máy Admin dùng `tb.taadaa.click` (cổng 5141..5158) hoàn toàn nằm ngoài tầm quét của auto-healer, dẫn đến tình trạng healer báo 32/32 xanh nhưng thực chất 32 máy Admin đang chết đứng.

## 5. Kỷ Luật Vận Hành Khi Nhận Batch Alert
1. **Đối soát tập hợp máy (Set Intersection Check):**
   * Lấy danh sách máy lỗi trong `log.jsonl` hoặc alert, đối chiếu ngay với cột Proxy trong `PROXYgandienthoai.xlsx`.
   * Nếu 100% máy lỗi cùng chia sẻ 1 upstream domain/subnet/port range -> đó là lỗi hạ tầng phân vùng, CẤM đổ lỗi cho thiết bị hay transient rớt mạng.
2. **Kiểm tra log chi tiết từng máy:**
   * Đọc trực tiếp `D:/Taadaa/runtime/<cluster>/live/<date>/.../log.jsonl` để xem error message đầy đủ kèm URL/IP đang kết nối.
3. **CẤM báo cáo qua loa:**
   * Báo cáo sự cố BẮT BUỘC chỉ rõ: (a) Tên miền/IP bị chết, (b) Các máy bị ảnh hưởng, (c) Bằng chứng đối soát, (d) Hành động khắc phục hạ tầng cụ thể.
