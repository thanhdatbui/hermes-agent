# Invariant: NO INSPECT -> NO BLOCKED (Anti-Premature-Block Discipline)

*Thẩm định & Phê duyệt bởi GPT-5.6-Sol High (04/10/2026 - Score: 92/100)*

## 1. Bệnh Lý Kiến Trúc: Bẫy Bại Liệt L3 BLOCKED Quan Liêu
Trước đây, hệ thống bị biến tướng theo chuỗi tha hóa:
```
Worker chậm/timeout (180s) -> Coordinator thấy tín hiệu đỏ -> Tuyên bố L3 BLOCKED -> Trách nhiệm đùn ra ngoài -> Task chết đứng.
```
Nguyên nhân gốc rễ:
1. **Quyền gọi BLOCKED rẻ hơn quyền giải quyết vấn đề**: Coordinator được thưởng vì "không làm sai", không bị bắt buộc chứng minh đã kiểm tra thực tế.
2. **Đồng nhất sai lầm: "Worker timeout == Task fail"**: Worker timeout chỉ là đứt kết nối mạng giữa Coordinator và Subagent. Rất nhiều trường hợp Worker đã ghi file, bắn API hoặc hoàn tất 90% việc (ví dụ PATCH runtime thành công) nhưng bị kẹt ở bước kiểm thử mạng tiếp theo.
3. **Bẫy "Target bẩn = Auto Block"**: Quy định cũ cấm Coordinator can thiệp khi target repo có file dở dang đã biến thành lá chắn trốn việc hoàn hảo.

---

## 2. Quy Tắc Bất Biến: NO INSPECT -> NO BLOCKED
> **"Worker timeout là một TRIGGER ĐỂ INSPECT, TUYỆT ĐỐI KHÔNG PHẢI BẰNG CHỨNG ĐỂ BLOCK."**

Trước khi Coordinator được phép thốt ra từ `BLOCKED`, bắt buộc phải qua 3 bước:

### Step 0 — Live Inspect O(1)
Coordinator bắt buộc kiểm tra trạng thái hiện trường:
- Process / worker có alive không?
- Service / port có phản hồi không (qua browser/curl/local API)?
- Dependency có thật sự chết không?

### Step 1 — Verify Artifact Trước Khi Kết Luận
Coordinator phải kiểm tra:
- Tệp mục tiêu hoặc database có thay đổi chưa?
- Output/result có đang nằm ở đích không?
- **Nếu Artifact ĐÃ ĐẠT: Nghiệm thu và BÁO DONE NGAY.** Tuyệt đối không giữ trạng thái lỗi chỉ vì worker timeout.

### Step 2 — Chế Tài Phạt Nặng BLOCKED Giả
Nếu Coordinator tuyên bố BLOCKED mà khi inspect lại thấy:
- Artifact đã hoàn tất, HOẶC
- Có thể kiểm chứng / tự fix được trong vòng 5-30s qua công cụ có sẵn
=> **Coi đây là THẤT BẠI NGHIÊM TRỌNG NHẤT của Coordinator (nặng hơn cả task fail bình thường).**

---

## 3. Thang Điều Phối Đóng Vòng Lặp (Close-The-Loop Ladder)
Đổi từ thang đi xuống hố (`L1 -> L2 -> BLOCKED -> DỪNG`) sang thang đóng vòng lặp:

- **L0 (Execute & Transient Retry)**: Worker thi công. Retry tối đa 2 lần nếu lỗi mạng/timeout.
- **L1 (Artifact & Live Inspection - Bắt buộc)**: Khi worker timeout, Coordinator lập tức live inspect O(1). Nếu artifact xong -> DONE. Nếu target dở dang nhưng đúng diff -> verify và DONE. Cấm lấy cớ target bẩn để block.
- **L2 (Coordinator Repair O(1))**: Coordinator trực tiếp vá lỗi vặt (<= 15 dòng, verify < 30s) hoặc hoàn tất nốt bước verify mà worker chưa kịp nộp.
- **L3 (Verified External Blocker)**: CHỈ ĐƯỢC PHÉP khi chứng minh dependency bất khả kháng ngoài tầm kiểm soát (mất điện, cháy máy, đứt mạng internet upstream, thiếu quyền OS).
