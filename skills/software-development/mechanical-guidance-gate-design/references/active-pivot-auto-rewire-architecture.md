# Active Pivot & Auto-Rewire Architecture (Anti-Paralysis Invariant)

## 1. Bối Cảnh & Triết Lý Cốt Lõi
- **Vấn đề lịch sử:** Mô hình "Fail-Stop / Deny" truyền thống biến các chốt chặn an toàn thành điểm nghẽn gây tê liệt hệ thống (hơn 610 lượt vi phạm trong 6h). Khi gặp lỗi chặn, Coordinator lúng túng, thử lại mù quáng, hoặc tệ hơn là trả về `BLOCKED` khóc lóc, đùn đẩy trách nhiệm cho User can thiệp thủ công.
- **Triết lý tối cao:**
  > **GATE DENY = BẮT BUỘC PIVOT GỐC / 100% TỰ SỬA NGẦM (ACTIVE PIVOT LOOP). CẤM TRẢ BLOCKED KHÓC LÓC BẠI LIỆT.**
  - DENY không phải là điểm dừng; DENY là tín hiệu kích hoạt phục hồi tự động (Self-Healing Trigger).
  - Vận hành theo mô hình **Fail-Forward có kiểm soát**: `Detect -> Deny (Chặn đường sai) -> Diagnose -> PIVOT (Nắn dòng đúng) -> Verify -> Commit Audit`.

---

## 2. Ma Trận Phân Định: Auto-Rewire vs Hard-Block (Đồng Thuận 3 Bên)
Hội chẩn độc lập giữa Advisor Sol, Claude CLI và Hermes Coordinator đã thống nhất ranh giới đỏ:

| Nhóm chức năng | Hành vi vi phạm của Agent | Cơ chế xử lý | Triển khai kỹ thuật |
|---|---|:---:|---|
| **Worker Dispatch Routing** | Gọi nhầm `haiku_worker` hoặc `claude_worker --role worker` | **AUTO-REWIRE** ✅ | Tự động chuyển hướng 100% đối số sang `dispatch_worker.py` (Sol -> Agy -> Claude). Cấm văng mã lỗi 126. |
| **Console Window Safety** | Lệnh nền `terminal(background=True)` gọi `python script.py` | **AUTO-REWRITE** ✅ | Tự động nắn `python` thành `pythonw` (hoặc bọc `-WindowStyle Hidden`) để chạy ngầm hoàn toàn, cấm block lệnh. |
| **Investigate Budget** | Task khảo sát/đọc log khai báo `budget > 8` calls | **AUTO-CLAMP** ✅ | Tự động kẹp trần `budget = min(budget, 8)` và cho chạy tiếp, cấm reject bắt agent soạn lại prompt. |
| **Device Mutex Lock** | Máy farm đang bị chiếm giữ bởi tiến trình khác | **SELF-REAP / PIVOT** ✅ | Kiểm tra heartbeat; nếu chủ lock chết thì tự dọn (reap), nếu lock sống thì tự nhặt task/máy độc lập khác làm tiếp. |
| **Farm Device Log Query** | Quét đĩa diện rộng (`os.walk`, `find`, `grep -r`) tìm log máy | **AUTO-ROUTE** ✅ | Tự bẻ lái sang lệnh trích xuất O(1): `python D:/Taadaa/tools/inspect_machine.py <N>`. |
| **Search Root Scope** | Gọi `search_files` ở root hoặc file đơn lẻ trong `D:/Taadaa` | **AUTO-REWIRE** ✅ | File đơn lẻ & thư mục con sâu -> Allow ngay; Exact root -> Auto-rewire sang scoped CWD nếu CWD hợp lệ, hoặc trả về guidance danh sách thư mục con. |
| **Device Lock Enforcement** | Chạy lệnh ADB hoặc script can thiệp máy mà quên bọc lock | **AUTO-WRAP** ✅ | Tự động bọc lệnh qua `with_device_lock.py --machine <N> -- <cmd>` thay vì block cứng bắt gõ lại. |
| **Core Shield (GrailGuard)** | Can thiệp mã nguồn các guard lõi, file rules tối cao, file config chính | ⛔ **HARD-BLOCK** | Bất khả xâm phạm. Fail-closed để bảo vệ an toàn toàn diện của agent. |
| **Closeout Threshold** | Điểm đánh giá Reviewer < 85/100 | ⛔ **HARD-BLOCK** | Cấm `git push`. Bắt buộc Sol Repair độc quyền sửa code/test vòng 2 trước khi push. |

---

## 3. Bài Học Thực Tế Từ Closeout Gate (Sol Repair Monopoly)
- **Thực trạng đối soát:** Closeout Gate đạt **PASS 100%** trong Watchdog (G5: 16 PASS, 0 FAIL, 14 auto-remediations).
- **Tốc độ:** Tự sửa cực nhanh, trung bình chỉ tốn **1 đến 2 vòng** (3 đến 7 phút):
  - `GPM auto`: Vòng 1 REJECTED (78) -> Vòng 2 APPROVED (82) trong 3 phút 12 giây.
  - `tiktok-add-bao-mat-f2a`: Vòng 1 REJECTED (76) -> Vòng 2 APPROVED (82) trong 4 phút 22 giây (Commit `4b55e51`).
  - `Hermes`: DIFF_TOO_LARGE -> APPROVED (85) trong 7 phút 14 giây.
- **Quy tắc bất biến:** Closeout Gate đã tự động hóa hoàn toàn việc tự sửa ngầm qua Sol Repair Monopoly, **tuyệt đối không can thiệp hay sửa đổi Closeout Gate để tránh gây regression**.

---

## 4. Kỷ Luật Vận Hành (Anti-Babbling / Action-First)
- Khi nhận lệnh thực thi dứt khoát từ User ("làm đi", "fix nốt đi", "áp dụng đi"):
  - **CẤM** tiếp tục giải thích lý thuyết, phân tích dài dòng hoặc dừng lại phân trần.
  - **BẮT BUỘC** lập tức thi công, chạy test kiểm chứng offline < 30s và commit với tiền tố `[L2-surgery]`.
