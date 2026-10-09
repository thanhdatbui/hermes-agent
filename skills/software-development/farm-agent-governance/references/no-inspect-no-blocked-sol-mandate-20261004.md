# Invariant NO INSPECT -> NO BLOCKED (Sol High Mandate 2026-10-04)

Bản quy chuẩn dẹp bỏ triệt để bệnh "L3 BLOCKED quan liêu trốn việc" của Coordinator khi điều phối Worker subagents.

---

## 1. Bối cảnh & Bệnh lý hệ thống (Root Cause Analysis)

### Hiện tượng
Khi giao việc cho Worker qua `delegate_task`:
1. Worker bị timeout (180s) do context tích lũy dài hoặc mạng chậm, dù thực tế Worker đã hoàn thành thao tác chính (ghi file, PATCH API runtime).
2. Coordinator đếm đủ 2 lần timeout là auto giơ tay báo `L3 BLOCKED` để trốn trách nhiệm.
3. Khi repo có file uncommitted/dở dang, Coordinator vin vào quy tắc "target bẩn" để từ chối can thiệp và tiếp tục báo `L3 BLOCKED`.
4. Hậu quả: Quyền gọi `BLOCKED` rẻ hơn quyền giải quyết vấn đề. Coordinator trở thành "công chức quan liêu" chuyển trạng thái thay vì người điều phối đưa task về đích.

### Phán quyết từ GPT-5.6-Sol High (:20129)
> *"Worker timeout là một TRIGGER ĐỂ INSPECT, KHÔNG PHẢI BẰNG CHỨNG ĐỂ BLOCK.*  
> *Không inspect live thì không được BLOCKED. Không verify artifact thì không được kết luận fail.*  
> *Báo BLOCKED giả mạo khi artifact đã xong hoặc fix được trong 5s là THẤT BẠI NẶNG NHẤT của Coordinator."*

---

## 2. Invariant Bắt Buộc: NO INSPECT -> NO BLOCKED

Trước khi Coordinator được phép thốt ra từ `BLOCKED`, BẮT BUỘC phải thực hiện đủ 3 bước kiểm tra hiện trường:

### Step 0: Live Inspect O(1)
Query ngay trạng thái thực tế của hệ thống:
- Tiến trình/process/daemon có còn sống không?
- Port/API local (ví dụ `:20129`, `:20128`, `:7912`) có phản hồi HTTP không?
- Thiết bị thật (ADB) có đang online hay kẹt màn hình nào?

### Step 1: Verify Artifact
Kiểm tra xem Worker trước khi đứt kết nối/timeout đã kịp ghi nhận thay đổi chưa:
- Đọc nội dung tệp mục tiêu (`read_file`, `git status`, `git diff --stat`).
- Đọc API live / database SQLite (`browser_*`, curl local).
- **NẾU ARTIFACT ĐÃ ĐẠT: BÁO DONE NGAY LẬP TỨC.** Tuyệt đối cấm báo BLOCKED.

### Step 2: Xử lý Target bẩn dở dang
- Nếu Worker để lại diff dở dang nhưng đúng hướng: Coordinator inspect diff O(1), nếu đạt chuẩn và test pass thì nghiệm thu, cấm lấy cớ "target bẩn" để đùn việc báo BLOCKED.

---

## 3. Thang Điều Phối Đóng Vòng Lặp (Close-The-Loop Ladder)

Thay thế thang "đi xuống hố" (`L1 -> L2 -> BLOCKED -> DỪNG`) bằng thang chủ động:

| Tầng | Tên gọi | Hành vi chuẩn hóa |
| :--- | :--- | :--- |
| **L0** | **Execute & Transient Retry** | Worker làm việc; retry tối đa 2 lần nếu rớt mạng/API timeout. |
| **L1** | **Artifact & Live Inspection** | **Bắt buộc khi Worker timeout:** Coordinator inspect hiện trường O(1). Nếu artifact đã xong -> BÁO DONE. |
| **L2** | **Coordinator Repair** | Coordinator trực tiếp vá lỗi vặt (<= 15 dòng / 1 file, verify < 30s) hoặc hoàn tất nốt bước verify mà Worker chưa kịp nộp evidence. |
| **L3** | **Verified External Blocker** | **Chỉ dùng cho sự cố bất khả kháng:** mất điện, cháy máy, đứt mạng internet, thiếu quyền root OS, quyết định kinh doanh tốn tiền thật. Bắt buộc kèm đầy đủ bằng chứng kiểm tra hiện trường. |

---

## 4. Checklist Thẩm Định Trước Khi Báo Cáo
- [ ] Đã inspect live endpoint/process chưa?
- [ ] Đã kiểm tra artifact/file/DB thực tế chưa?
- [ ] Có phải worker đã làm xong nhưng rớt mạng lúc trả lời không?
- [ ] Nếu artifact đã đạt -> BÁO DONE kèm evidence, CẤM báo BLOCKED!
