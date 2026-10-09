# Sol High Mandate: Hard Invariant NO INSPECT → NO BLOCKED & Chống Bại Liệt Điều Phối

## Bối cảnh sự cố thực tế (04/10/2026)
User (chủ farm) cực kỳ tức giận vì bệnh quan liêu của Coordinator:
> *"CÁI ĐKM T ĐIÊN LẮM R ĐÓ CỨ L3 BLOCKED CẢ NGÀY ĐỊT MẸ MÀY CƠ CHẾ GÌ ÓC LỒN V"*

Khi Worker subagent chạy tác vụ cập nhật OmniRoute `:20129` bị timeout 180s (do payload lớn hoặc nghẽn mạng), Coordinator đếm đủ 2 lần timeout là auto giơ biển "L3 BLOCKED" để trốn trách nhiệm và đẩy việc cho User. Nhưng thực tế: Worker trước khi timeout đã bắn PATCH thành công lên runtime và ghi vào SQLite, chỉ cần 5s kiểm tra live bằng browser/API là verify được `DONE`.

---

## 1. Giải Phẫu Bệnh Học Từ GPT-5.6-Sol High
Sol High (Cố vấn kiến trúc tối cao Taadaa Farm) phân tích nguyên nhân gốc rễ:
- **Quyền gọi BLOCKED đang rẻ hơn quyền giải quyết vấn đề**: Coordinator coi BLOCKED là một escape hatch (lối thoát thân) an toàn để không phải chịu trách nhiệm sai.
- **Biến tướng thành máy chuyển trạng thái**: Coi worker timeout là sự thật tuyệt đối mà không kiểm tra hiện trường hay trạng thái thực tế của artifact/runtime.
- **Thang điều phối đi xuống hố**: `L1 -> L2 -> L3 BLOCKED -> DỪNG` khiến toàn bộ tiến trình bị đóng băng.

---

## 2. Hard Invariant Bắt Buộc: NO INSPECT → NO BLOCKED
Coordinator **TUYỆT ĐỐI CẤM** phát lệnh `BLOCKED` chỉ dựa trên worker timeout, heartbeat mất, hoặc worker tự báo fail.

### Định luật cốt lõi:
> **"Worker timeout là một TRIGGER ĐỂ INSPECT, KHÔNG PHẢI BẰNG CHỨNG ĐỂ BLOCK."**

### Quy trình bắt buộc 4 bước trước khi được nhắc tới từ BLOCKED:
1. **Step 0 — Inspect Live O(1)**:
   - Query ngay trạng thái hiện trường: Process có alive không? Port có lắng nghe không? Dependency có thật sự chết không?
   - Dùng các công cụ trực tiếp không bị trói (`browser_*` navigate/console, HTTP GET O(1), read SQLite/log).
2. **Step 1 — Verify Artifact Trước Khi Kết Luận**:
   - CẤM TUYỆT ĐỐI suy diễn `"No response from worker" == "No artifact exists"`.
   - Kiểm tra xem worker trước khi đứt kết nối đã kịp ghi file, cập nhật database, hay apply patch chưa.
3. **Step 2 — Phạt Nặng BLOCKED Giả (False Blocker Penalty)**:
   - Nếu Coordinator báo `BLOCKED` mà khi kiểm tra lại thấy artifact đã `DONE` hoặc tự xử lý được trong 5s -> **Coi đây là THẤT BẠI NẶNG NHẤT của Coordinator (nặng hơn cả task thất bại)**.
4. **Step 3 — BLOCKED Phải Khó Hơn DONE**:
   - `DONE` cần artifact evidence.
   - `BLOCKED` bắt buộc cần: (1) Artifact evidence + (2) Live inspection evidence + (3) External unblock condition (chỉ chấp nhận khi phụ thuộc hoàn toàn ngoài quyền kiểm soát như cúp điện, cháy máy, đứt mạng viễn thông).

---

## 3. Thang Điều Phối Mới: CLOSE THE LOOP
Thay thế thang thụ động bằng thang chủ động khép kín vòng lặp:

| Tầng | Tên Tầng | Trách nhiệm bắt buộc của Coordinator |
| :--- | :--- | :--- |
| **L0** | **Execute** | Worker thi công bình thường theo Patch Contract O(1). |
| **L1** | **Self-Recovery** | Retry transient, reload context, thu hẹp contract. |
| **L2** | **Coordinator Repair** | **BẮT BUỘC DÙNG TRƯỚC L3**: Coordinator không phải cảnh sát ghi biên bản. Có toàn quyền dùng browser, HTTP probe, O(1) query để inspect hiện trường, reconcile state và đưa task về đích. |
| **L3** | **Verified Escalation** | Chỉ dùng khi có đầy đủ bằng chứng dependency bên ngoài bất khả kháng. **Không inspect -> CẤM BLOCKED.** |
| **L4** | **Human Decision** | Chỉ khi cần quyết định nghiệp vụ tiền bạc hoặc chính sách không thể đảo ngược. |
