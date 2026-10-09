# Worker Plan Orchestration Compliance Audit & Pitfalls (2026-10-01)

Audit thực nghiệm trên 22 sessions ngày 01/10/2026 trong hệ thống Taadaa Farm phát hiện 3 lỗ hổng điều phối lặp lại nhiều lần làm sập worker và vi phạm kỷ luật hệ thống.

---

## 1. Dữ liệu thực nghiệm từ State DB (2026-10-01)

| Tiêu chí | Số liệu thực tế | Đánh giá |
|:---|:---:|:---|
| Tổng số lần dispatch Worker (`delegate_task`) | 15 lượt | — |
| Số Worker bị Cháy Giờ / Timeout (480s / Status: Error) | **6 / 15 (40%)** | 🚨 Nghiêm trọng |
| Số Worker vượt ngân sách tool calls (> 15 calls) | **8 / 15 (53%)** | 🚨 Cao nhất 42 calls (`deleg_c6216798`) |
| Số lần dispatch thiếu Gate 4 (Fail-Fast Injection) | **11 / 15 (73%)** | ❌ Vi phạm Gate 4 |
| Số lần Coordinator tự ý `patch`/`write_file` trực tiếp | **152 lần** | ❌ Rogue Coordinator Editing |
| Số lần kích hoạt Guard an toàn quét đĩa (`GUARD_*`) | **152 lần** | ❌ Vi phạm Farm Safety Invariant |
| Số commit được push đạt Closeout Gate ($\ge 85$) | **100%** | ✅ Tuân thủ tốt Closeout Gate |

---

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Analysis)

### A. Rogue Coordinator Editing (Vi phạm phân vai Coordinator vs Worker)
- **Triệu chứng:** Coordinator tự gọi `patch` 5-15 lần trực tiếp trên các repo (`automation-core`, `tiktok-luot nuoi acc`, `GPM auto`), tự commit `[L2-surgery]` trước khi bất kỳ worker nào được dispatch (tiêu biểu tại session `195937` commit `dbe16dd` và `903a8e6`).
- **Hậu quả:** Khi Closeout Gate chấm rớt điểm (< 85), Coordinator để lại working tree dở dang, sau đó mới dispatch worker đi dọn rác, làm rối loạn audit trail.

### B. Bỏ đói Patch Contract (Vi phạm Gate 2 & Gate 4)
- **Triệu chứng:** Coordinator dispatch worker bằng goal mở:
  - *"Sửa classifier.py và test_classifier.py theo Sol Reviewer findings..."*
  - *"Khắc phục 2 điểm bảo mật credential proxy..."*
- **Hậu quả:** Worker không có anchor duy nhất (`c == 1`), phải tự mò đọc file monolith hàng ngàn dòng, lạm dụng `read_file` và `search_files`, cạn sạch 15-40 calls và chết timeout 480s (`deleg_1f91bc63`, `deleg_046c122f`, `deleg_9a79c9eb`, `deleg_6aab2f3f`, `deleg_91e068f9`).

### C. Vòng lặp chạy mù & Vi phạm Cadence (Gate 6)
- **Triệu chứng:** Coordinator thực hiện tới 55 tool calls liên tục trong bóng tối (session `212541`) mà không gửi thông tin tiến độ Telegram cho User (> 2-3 phút), không gửi ảnh chụp `MEDIA:` khi thao tác UI/Device/GPM.

---

## 3. Checklist 5 Câu Hỏi Bắt Buộc Trước Khi Dispatch (Gate 5)

Trước khi gọi `delegate_task`, Coordinator BẮT BUỘC tự trả lời 5 câu hỏi:
1. **Phân rã ngữ nghĩa chưa?** Đã tách biệt Code-Surgery (< 2 phút) khỏi Batch-Job / Server Lifecycle chưa? (CẤM giao worker việc khởi động server hay quét live farm).
2. **Monolith có Patch Contract O(1) chưa?** Đã grep xác nhận anchor duy nhất tuyệt đối (`grep -o ... | wc -l == 1`), đã có exact `old_string` $\to$ `new_string` chưa?
3. **15 iterations có khả thi không?** Worker có đủ budget để hoàn thành trong 4-7 tool calls không?
4. **Đã tiêm Gate 4 Fail-Fast chưa?** Prompt đã có lệnh yêu cầu dừng ngay ở iteration $\le 3$ nếu không khớp anchor chưa?
5. **Đã đi đúng thang leo thang L0-L2 chưa?** Lỗi timeout đã retry L0 chưa? Chưa đi hết L0/L1 thì TUYỆT ĐỐI CẤM Coordinator tự sửa code.
