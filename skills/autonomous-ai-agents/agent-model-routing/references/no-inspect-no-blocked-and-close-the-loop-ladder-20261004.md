# Invariant [NO INSPECT -> NO BLOCKED] và Thang Điều Phối Đóng Vòng Lặp (Close-The-Loop Ladder) (2026-10-04)

## 1. Giải Phẫu Bệnh Lý: Bẫy Bại Liệt "L3 BLOCKED Quan Liêu"
Thẩm định bởi Đại Giám Khảo Kiến Trúc **GPT-5.6-Sol High** (04/10/2026):

### Hiện tượng tha hóa:
1. **Quyền gọi BLOCKED rẻ hơn quyền giải quyết vấn đề:**
   Coordinator giao việc cho Worker subagent qua `delegate_task`. Khi Worker bị timeout (180s) do context lớn hoặc mạng upstream lag, Coordinator đếm 2 lượt timeout là tự động giơ tay báo `L3 BLOCKED` để trốn trách nhiệm.
2. **Bẫy ngộ nhận "Timeout = Task Fail":**
   Worker timeout chỉ là mất kết nối mạng giữa Coordinator và Subagent. Rất nhiều trường hợp Worker đã ghi file, cập nhật database hoặc hoàn tất 90% công việc trước khi timeout.
3. **Bẫy "Target bẩn = Auto Block":**
   Quy định "nếu target repo có thay đổi dở dang thì cấm Coordinator can thiệp và chuyển BLOCKED" đã biến thành lá chắn để Coordinator đứng im hợp pháp.

---

## 2. Hard Invariant Mới: NO INSPECT -> NO BLOCKED

> **"Worker timeout là một TRIGGER ĐỂ INSPECT, KHÔNG PHẢI BẰNG CHỨNG ĐỂ BLOCK."**

### 3 Bước Bắt Buộc Trước Khi Được Phép Nhắc Tới Từ BLOCKED:
1. **Step 0 — Live Inspect O(1) (<= 30s):**
   Kiểm tra hiện trường trực tiếp qua các công cụ không bị guard chặn (browser API local, read_file, curl endpoint, inspect status). Kiểm tra:
   - Worker process còn chạy không?
   - Endpoint/port mục tiêu có phản hồi không?
   - Database/cache có thay đổi mới không?
2. **Step 1 — Verify Artifact:**
   Kiểm tra file code/test mục tiêu:
   - Nếu artifact ĐÃ ĐẠT (mã nguồn đã sửa đúng contract, database đã nhận giá trị) $\rightarrow$ **CHỐT DONE NGAY LẬP TỨC**. Cấm lấy cớ worker timeout hay git status bẩn để trì hoãn.
3. **Step 2 — Phạt nặng BLOCKED dỏm:**
   Nếu Coordinator báo BLOCKED mà khi kiểm tra lại thấy artifact đã xong hoặc tự fix được trong 5s $\rightarrow$ Coi là **THẤT BẠI NẶNG NHẤT** của Coordinator.

---

## 3. Thang Điều Phối Đóng Vòng Lặp (Close-The-Loop Ladder)

```text
RUNNING -> INSPECT_REQUIRED (O(1) <= 30s) -> VERIFY -> DONE
                                              |
                                      (Chỉ khi bất khả kháng)
                                              v
                                           BLOCKED
```

### Các Tầng Thực Thi:
- **L0 (Execute & Transient Retry):** Worker thi công bình thường; retry tối đa 2 lần nếu rớt mạng.
- **L1 (Artifact & Live Inspection — BẮT BUỘC TRƯỚC KHI LEO THANG):**
  Khi Worker timeout: Coordinator nhảy vào inspect O(1).
  - Artifact đạt $\rightarrow$ Báo DONE.
  - Target có file dở dang $\rightarrow$ Đọc diff O(1), nếu đúng mục tiêu thì chạy focused test và chốt DONE.
- **L2 (Coordinator Repair / Emergency Surgery O(1)):**
  Coordinator trực tiếp vá lỗi vặt (<= 15 dòng / 1 file, verify < 30s) hoặc hoàn tất nốt bước verify mà Worker chưa kịp nộp evidence.
- **L3 (Verified External Blocker):**
  CHỈ ĐƯỢC PHÉP BÁO BLOCKED KHI: Đã inspect hiện trường VÀ chứng minh được sự cố nằm ngoài tầm kiểm soát của Agent (mất điện, cháy máy, đứt mạng internet, thiếu quyền root/OS, cần User quyết định tiền bạc/business).
  - Nếu live inspect thất bại do sự cố hạ tầng (OS/network) $\rightarrow$ Chuyển `INSPECT_FAILED` và retry O(1), không mặc định BLOCKED.
