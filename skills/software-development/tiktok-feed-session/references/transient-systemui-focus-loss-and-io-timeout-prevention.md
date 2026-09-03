# Transient SystemUI Focus Loss & I/O Scan Hang Prevention

## 1. Transient Focus Loss False-Positive (Case FEED-FOCUS-01)
### Hiện tượng
Khi chạy `multi-machine-feed-session` hoặc `feed_swipe_smoke.py`, máy bất ngờ bị dừng phiên với lý do `TikTok focus lost`, mặc dù ảnh chụp màn hình và XML tại hiện trường chứng minh 100% màn hình vẫn đang ở TikTok Feed (`Đề xuất` / `Đã follow`), video đang phát bình thường.

### Nguyên nhân gốc
1. `dumpsys window` trên Android trả về `focused_package` tạm thời là `com.android.systemui` hoặc `com.sec.android.inputmethod` do thông báo ngầm từ VPN/ViChanger, toast notification hoặc bàn phím chớp ngầm.
2. Hàm `safety_check_attempt` trong `safety.py` đã chuẩn hóa `focus_pkg = expected` khi XML chứng minh màn hình là `for-you`/`following`/`friends`/`profile`.
3. Tuy nhiên, logic kiểm tra bước tiếp theo trong `feed_swipe_smoke.py` lại so sánh trực tiếp biến thô `focused_package != expected_package` (bỏ qua `safety.focus_package` đã được chuẩn hóa), dẫn đến việc đánh rớt bước kiểm tra an toàn và báo lỗi `TikTok focus lost`.

### Quy tắc xử lý & Phòng tránh
- Luôn sử dụng `safety.focus_package` hoặc `effective_focus_package` sau khi đã qua bộ lọc xác thực XML/màn hình.
- Tuyệt đối không đánh giá mất focus chỉ dựa vào package thô từ `dumpsys` khi XML đã xác nhận rõ ràng là Feed hợp lệ.

---

## 2. Phòng tránh treo lệnh do quét I/O đệ quy sâu (Anti-Pattern: Deep Recursive Walks)
### Hiện tượng
Agent chạy các lệnh `os.walk('D:/Taadaa')`, `find /d/Taadaa`, hoặc `glob('**')` dẫn đến việc quét qua hàng trăm nghìn file artifacts/logs cũ trong `D:/Taadaa/runtime`, khiến terminal bị block 900s và phiên kéo dài hơn 100 phút không thể phản hồi người dùng.

### Quy tắc bất biến
1. **CẤM quét đệ quy toàn bộ thư mục cha `D:/Taadaa`:** Chỉ định rõ ràng thư mục cấp 1 hoặc đường dẫn file cụ thể cần đọc.
2. **Luôn đặt timeout ngắn cho các lệnh thăm dò (max 10-15s):** Không để lệnh chạy ngâm chờ 900s.
3. **Ưu tiên bằng chứng của Turn hiện tại:** Khi user gửi ảnh/alert trong tin nhắn mới, xử lý ngay đúng máy/alert trong tin nhắn đó, không tự động đào bới toàn bộ session cũ làm lạc hướng điều tra.
