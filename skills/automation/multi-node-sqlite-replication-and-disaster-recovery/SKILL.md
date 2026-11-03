---
name: multi-node-sqlite-replication-and-disaster-recovery
description: Kiến trúc đồng bộ SQLite farm_master.db giữa 2 cụm máy Kibe và Admin, nguyên tắc Zero-Overlap, và quy trình Disaster Recovery khi node hỏng.
---
# Multi-Node SQLite Replication & Disaster Recovery (Kibe <-> Admin)

## 1. Trọng Tâm & Bối Cảnh
- **Môi trường:** 2 máy Controller (Kibe `192.168.110.118` và Admin `192.168.110.119`) cùng chung subnet LAN.
- **Dải máy quản lý (Zero Overlap):**
  - Kibe quản lý máy 1 - 80 (640 nick TikTok).
  - Admin quản lý máy 201 - 280 (630 nick TikTok).
- **Mục tiêu kép:**
  1. **Vận hành độc lập hàng ngày:** Không nghẽn lock, không bị rớt mạng làm treo runner, tốc độ local $O(1) \approx 0.005$s.
  2. **Phục hồi thảm họa (Disaster Recovery - DR):** Nếu máy Kibe bị hỏng phần cứng/cháy ổ cứng, toàn bộ 80 máy S7 của Kibe mang sang cắm vào máy Admin vẫn có 100% dữ liệu để tiếp tục vận hành ngay lập tức.

## 2. 3 Nguyên Tắc Cốt Tử (Đồng Thuận Hội Đồng Cố Vấn Sol, Claude CLI, Gemini)
1. **Full-Farm Replica tại mỗi Node:**
   - Cả Kibe và Admin BẮT BUỘC đều phải sở hữu 1 bản SQLite `D:/Taadaa/data/farm_master.db` chứa đầy đủ 100% tài khoản toàn farm (1.270 nick).
   - Khi Kibe chết, Admin đã có sẵn 640 nick của Kibe để nhận diện thiết bị ngay khi cắm dàn S7 sang.
2. **Phân Quyền Ghi Độc Quyền (Single-Writer Partitioning):**
   - Kibe chỉ được phép ghi vào dải máy 1 - 80.
   - Admin chỉ được phép ghi vào dải máy 201 - 280.
   - Triệt tiêu 100% xung đột ghi (Write Contention) và không bao giờ bị Split-Brain.
3. **CẤM Chép Đè File Nhị Phân (.db) Qua Mạng LAN:**
   - Tuyệt đối KHÔNG dùng robocopy/scp đè toàn bộ file `farm_master.db`, vì dễ gây Data Wipe (file cũ đè file mới).
   - Chỉ đồng bộ theo dòng (Row-Level Upsert) hoặc trích xuất JSON/Text đối soát.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
