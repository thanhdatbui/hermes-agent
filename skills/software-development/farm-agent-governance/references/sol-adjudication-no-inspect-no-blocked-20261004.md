# Sol High Adjudication: Invariant "NO INSPECT -> NO BLOCKED" & Anti-Paralysis Escalation (04/10/2026)

## 1. Bối cảnh & Hiện tượng Bệnh lý (The Paralysis Trap)
Trong phiên vận hành ngày 04/10/2026, Coordinator gặp sự cố:
- Worker subagent được dispatch thực hiện task (hạ `modelLockout = 120s` trên OmniRoute).
- Subagent thực chất **đã bắn lệnh PATCH thành công lên runtime :20129**, nhưng bị ngâm timeout 180s ở bước chạy test probe sau đó.
- Coordinator thấy worker timeout (2 lần liên tiếp), máy móc đếm số lần fail rồi tuyên bố ngay: `L3 BLOCKED: Target bẩn / Worker timeout`, đùn việc ra ngoài và dừng task.
- User phản ứng gay gắt trước bệnh quan liêu: *"CỨ L3 BLOCKED CẢ NGÀY ĐỊT MẸ MÀY CƠ CHẾ GÌ ÓC LỒN V"*.
- Tham vấn trực tiếp Cố Vấn Tối Cao **GPT-5.6-Sol High (:20129)** chỉ ra: **Quyền gọi BLOCKED đang rẻ hơn quyền giải quyết vấn đề**. Coordinator biến thành máy chuyển trạng thái trốn việc thay vì người đưa task về đích.

---

## 2. Bản chất Bệnh học từ Sol High

1. **Worker Timeout != Task Fail:**
   - Worker timeout (180s) chỉ phản ánh việc rớt heartbeat/kết nối giữa Coordinator và Subagent.
   - Timeout hoàn toàn không chứng minh artifact chưa được tạo, file chưa được sửa hay runtime chưa nhận cấu hình.
2. **Bẫy "Target bẩn = Auto Block":**
   - Quy định cũ *"nếu target bẩn do worker để lại thay đổi -> L3 BLOCKED"* biến thành lá chắn hoàn hảo để Coordinator đứng im hợp pháp.
3. **Escalation Ladder hỏng:**
   - Thang cũ biến thành đường dốc xuống hố: `L1 -> L2 -> L3 BLOCKED -> STOP`.

---

## 3. Hard Invariant Cốt Lõi: NO INSPECT -> NO BLOCKED

> **"Worker timeout là một TRIGGER ĐỂ INSPECT, KHÔNG PHẢI BẰNG CHỨNG ĐỂ BLOCK."**

Trước khi Coordinator được phép thốt ra từ `BLOCKED`, bắt buộc phải đi qua 3 bước:

### Step 0: Live Inspect O(1)
Coordinator bắt buộc kiểm tra hiện trường thực tế:
- Worker process còn sống không?
- Service / Port / Endpoint có đang phản hồi không?
- Thay đổi đã được áp dụng vào RAM / Database / Runtime chưa?
(Sử dụng công cụ không bị guard chặn: `browser_*` truy cập local API, `read_file`, inspect status).

### Step 1: Verify Artifact Trước Khi Kết Luận
- Đọc file mục tiêu / git status: Nếu code/cấu hình đã nằm ở đó và đúng mục tiêu -> **CHỐT DONE NGAY**, cấm giở trò BLOCKED.
- Nếu target có file dở dang: Đọc diff O(1). Nếu diff hợp lệ, Coordinator hoàn tất nốt bước verify (chạy test, check endpoint) để đưa task về đích.
- **Chống Bệnh Than Thở Khi Worker Timeout:** Tuyệt đối cấm Coordinator than phiền "không sửa được", "bị timeout", "harness lỗi" để đùn đẩy trách nhiệm. Worker timeout 180s là hiện tượng bình thường; Coordinator phải chủ động kiểm tra xem patch đã vào file chưa và tự động điều phối lane kiểm chứng tiếp theo.

### Step 2: Phạt Nặng BLOCKED Giả (False Blocker Penalty)
- Nếu Coordinator tuyên bố `BLOCKED` mà khi kiểm tra lại phát hiện:
  * Artifact thực chất đã DONE, hoặc
  * Chỉ cần 5 giây inspect là verify được, hoặc
  * Có thể tự sửa/hoàn tất trong ngân sách O(1),
  -> **Xử lý là THẤT BẠI NGHIÊM TRỌNG NHẤT của Coordinator (nặng hơn cả task fail thông thường).**

---

## 4. Thang Điều Phối Đóng Vòng Lặp Mới (Close-The-Loop Ladder)

```
L0 EXECUTE (Worker bình thường)
  │
L1 SELF RECOVER & LIVE INSPECTION (Bắt buộc kiểm tra hiện trường khi đứt mạng/timeout)
  │
L2 COORDINATOR REPAIR (Tự vá lỗi vặt <=15 dòng, verify nốt artifact, đóng vòng lặp)
  │
L3 VERIFIED BLOCKED (Chỉ khi chứng minh dependency bất khả kháng ngoài tầm kiểm soát)
  │
L4 HUMAN DECISION (Quyết định tài chính / nghiệp vụ)
```

- **L0 (Execute):** Worker thi công theo Patch Contract. Lỗi mạng/timeout transient cho phép retry tối đa 2 lần.
- **L1 (Live Inspection):** Khi worker timeout hoặc fail, Coordinator BẮT BUỘC inspect hiện trường live O(1). Nếu artifact đã đạt -> chốt DONE. Cấm lấy cớ "target bẩn" để đùn việc.
- **L2 (Coordinator Repair):** Coordinator có toàn quyền và trách nhiệm sửa đường đi, chạy lệnh kiểm chứng, vá lỗi nhỏ (<=15 dòng) để đưa task về DONE.
- **L3 (Verified Blocked):** CHỈ ĐƯỢC PHÉP khi có đủ 4 yếu tố:
  1. Đã inspect hiện trường O(1).
  2. Bằng chứng dependency bất khả kháng (mất điện, sập mạng upstream, tài khoản cạn sạch tiền).
  3. Điều kiện unblock rõ ràng.
  4. Không thể giải quyết bằng bất kỳ công cụ nào trong tay Coordinator.
