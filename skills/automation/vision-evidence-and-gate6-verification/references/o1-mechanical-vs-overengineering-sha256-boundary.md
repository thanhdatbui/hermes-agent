# Phân Biệt Giữa Cơ Chế Kiểm Tra Cơ Học O(1) và Bệnh Over-Engineering

## 1. Bối Cảnh Sự Cố & Câu Hỏi Thực Tế Từ User
Trong phiên ngày 27/10/2026, sau khi sửa xong lỗi `INVALID_MEDIA_FILE (tampered: sha-256 differs)` do stale receipt cũ, User đặt câu hỏi:
*"Là sao vẫn dùng sha 256 gì à mày ns cái đó gây over engineer mà. Tóm lại hook chuẩn chưa. Đảm bảo bắt agent soi ảnh nhưng k đc over engineer?"*

Đây là câu hỏi phân định ranh giới cốt lõi trong tư duy kiến trúc: Khi nào một cơ chế tính toán (như hash SHA-256) là công cụ cơ học chuẩn $O(1)$, và khi nào nó biến tướng thành **Over-Engineering / Bureaucratic Theater** gây hại?

---

## 2. Ranh Giới Giữa "Cơ Học Chuẩn O(1)" và "Bệnh Over-Engineering"

| Tiêu Chí | Cơ Chế Cơ Học Chuẩn $O(1)$ | Biến Tướng Over-Engineering (Bureaucratic Theater) |
|---|---|---|
| **Mục đích** | Xác nhận đúng sự kiện vật lý thật: "File trên đĩa hiện tại có đúng là file vừa được mắt đọc hay không?" | Xây dựng ảo tưởng bảo mật bằng thủ tục: Cố chống tấn công giả mạo (tampering) trên chính máy local của chính mình. |
| **Chi phí tính toán** | $O(1)$ — Băm 1 file ảnh mất ~0.001s, đối chiếu trực tiếp trong RAM. | Đắp thêm bảng ký HMAC, dynamic nonce, token subtraction, sidecar file `.prov.json`, multi-party consensus. |
| **Phạm vi thời gian (Scope)** | Cực ngắn (TTL = 300s): Chỉ kiểm tra vé của lượt đọc vừa diễn ra ngay trong phiên hiện tại. | Không giới hạn thời gian: Quét ngược log lôi receipt cũ từ 2-3 ngày trước ra so hash với file chụp mới hôm nay. |
| **Hành vi khi có file mới** | Chụp mới đè lên tên file cũ $\rightarrow$ Coi là ảnh mới chưa soi mắt (`NO_RECEIPT`), ép gọi tool soi mắt. | Chụp mới đè lên tên file cũ $\rightarrow$ Báo lỗi *"ảnh bị can thiệp/tampered"*, quăng exception và leak prompt lỗi ra Telegram. |
| **Trải nghiệm Agent / User** | Rõ ràng, không bao giờ nghẽn: Soi mắt rồi $\rightarrow$ PASS. Chưa soi mắt $\rightarrow$ BLOCKED kèm đúng 1 lệnh soi mắt. | Rối rắm, false-positive tràn lan, ép Agent vào vòng lặp xin lỗi/phân trần hoặc nhè prompt kỹ thuật ra chat. |

---

## 3. Bản Chất Lỗi Sáng Nay Không Phải Do Thuật Toán SHA-256
- **Thuật toán SHA-256 không có lỗi:** Bản thân việc tính `sha256(file)` là thao tác cơ học cực nhẹ ($O(1)$), không gây tải hệ thống.
- **Lỗi nằm ở logic nghiệp vụ Over-Engineering:**
  1. Hàm `_latest_signed_receipt` quét ngược log tìm receipt của file `admin_screen.png`.
  2. Nó nhặt được 1 receipt từ ngày 25/10 (2 ngày trước).
  3. Hàm `_media_file_verdict` đem SHA-256 của file chụp sáng 27/10 so sánh với SHA-256 của file ngày 25/10 **mà không hề kiểm tra thời hạn (TTL)**!
  4. Hai hash khác nhau là điều hiển nhiên (vì ảnh chụp màn hình hôm nay khác 2 ngày trước), nhưng Gate lại kết luận phi lý: *"File ảnh đã bị can thiệp trái phép (tampered)"*.

---

## 4. Quy Chuẩn Triệt Tiêu Over-Engineering Cho Gate Thị Giác
Để đảm bảo Gate vừa tuyệt đối ép Agent đọc ảnh, vừa không bị vướng bẫy Over-Engineering:

1. **Giới Hạn Khung Giờ Vé (Strict TTL Binding):**
   Mọi phép kiểm tra tính toàn vẹn giữa File và Receipt BẮT BUỘC phải nằm trong khung thời gian ngắn (`age <= 300s`). Quá 300s, receipt xem như vô hiệu, không bao giờ được dùng để so khớp tamper.
2. **Loại Bỏ So Khớp Vi Mô Hệ Thống Tệp (Drop Microsecond mtime):**
   Không so sánh mtime ở mức microsecond `1e-6s` trên Windows NTFS. Chỉ cần SHA-256 và tồn tại file hợp lệ là đủ.
3. **Cơ Chế Auto-Receipt Khi Native Vision Được Gọi:**
   Khi Agent chủ động gọi `browser_navigate("file:///...")` và `browser_vision`, tầng hook tự động gán vé hợp lệ cho file đó. Không bắt Agent phải chạy thêm script ngoài lề chỉ để sinh chữ ký số.
4. **Tuyệt Đối Cấm Leak Prompt Cưỡng Chế Ra Chat:**
   Các chuỗi format kỹ thuật `[CONTRADICTION_GATE_TRIGGERED]` hay `REQUIRED_NEXT_ACTION` chỉ được xuất hiện trong agent loop nội bộ, cấm xuất bản ra giao diện Telegram của người dùng.
