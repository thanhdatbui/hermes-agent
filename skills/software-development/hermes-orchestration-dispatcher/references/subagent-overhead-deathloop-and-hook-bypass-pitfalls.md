# Subagent Overhead Death Loop & Pre-Tool Hook Bypass Pitfalls (2026-09-25)

## 1. Tử huyệt "Subagent Overhead Death Loop" trên Monolith (> 1.500 dòng)

### Bản chất sự cố:
Khi Coordinator nhận yêu cầu thêm nhiều tính năng hoặc sửa code trên file monolith (như `tiktok_dashboard.py` ~1.876 dòng):
- **Sai lầm:** Gộp 2 tính năng lớn (Modal Overview Chart + Machine Fleet Heatmap) vào 1 prompt dispatch `delegate_task` cho worker.
- **Hậu quả:** Worker subagent (omni-worker) phải đọc lại toàn bộ monolith (~25k-90k token context), tự mò mẫm các đoạn template HTML/CSS/JS nhúng trong Python, lặp vô hạn ở bước escape `{}`/`\`, dẫn đến **TIMEOUT 600s (10 phút)**, `0 files modified`, đốt sạch thời gian và quota của user mà không sinh ra bất kỳ artifact nào.
- Ngay cả khi thu hẹp scope về Pass 1, worker vẫn tiếp tục timeout 600s nếu không được phân rã thành các đơn vị sửa đổi tất định.

---

## 2. Phân loại 3 Lớp Công Việc (Claude Opus Approved 2026-09-25)

| Lớp | Điều kiện xác định | Thực thi chuẩn |
| :--- | :--- | :--- |
| **D: Deterministic Patch** | • Đã biết chính xác file và anchor duy nhất (`grep -o ... \| wc -l == 1`).<br>• Diff $\le$ 80 dòng mỗi patch.<br>• Có lệnh verify tất định (`pytest`, `py_compile`, `node --check`).<br>• Không can thiệp ADB hay thiết bị thật. | **Coordinator tự apply và verify ngay (15–30s). CẤM dispatch worker subagent gây lãng phí.** |
| **S: Scoped Build** | • Biết file, cần viết logic mới > 80 dòng.<br>• Đã có acceptance test rõ ràng. | **Worker subagent**, bắt buộc cấp sẵn Worker Brief (Anchor Map + Acceptance command), budget cứng $\le$ 240s (cấm để 600s). |
| **E: Exploratory** | • Khám phá thiết bị thật (ADB, UI app, OCR, trace máy farm).<br>• Debug sự cố chưa rõ nguyên nhân gốc rễ. | **Bắt buộc Worker subagent** độc lập trong context riêng. |

---

## 3. Phân biệt Rạch ròi: "Anchor Map" vs "Phân Rã Việc"

- **Anchor Map (Bản đồ Điểm Neo Vật Lý):**
  * Là toạ độ chính xác tuyệt đối trong mã nguồn (`wc -l == 1`).
  * Ví dụ: `<button class="btn-filter" id="btn-bxh-heart">` xuất hiện duy nhất 1 lần, `<div class="chart-wrapper">` xuất hiện duy nhất 1 lần.
  * Giúp người sửa code chèn trúng đích 100%, không bị chèn nhầm vị trí tương tự.
- **Phân Rã Việc (Decomposition):**
  * Là chia nhỏ bài toán theo **ngữ nghĩa và vòng đời**: tách riêng API endpoint $\rightarrow$ HTML structure $\rightarrow$ CSS styling $\rightarrow$ JS interactions.
  * Mỗi unit tương ứng 1 patch độc lập, verify độc lập, fail thì rollback ngay mà không ảnh hưởng unit khác.

---

## 4. Hai Lỗ Hổng Khiến Pre-Tool Hook `guard_dispatch_contract.py` Bị Vô Hiệu Hóa

Qua đối soát thực tế tại sao Hook ép gọi Sol Planner không chạy từ 21/09 đến 25/09:

1. **Bẫy Regex Language Mismatch:**
   * Hook chỉ kiểm tra từ khóa tiếng Việt: `r'\b(?:patch|sửa code|chỉnh sửa|cập nhật code|refactor|fix code)\b'` và `FILE: <path>`.
   * Khi Coordinator dispatch bằng tiếng Anh (`"Implement Modal Overview tab..."`, `"Target files: 1. D:/Taadaa/tools/tiktok_dashboard.py"`), Hook ngộ nhận đây là task **INVESTIGATE (khảo sát)**.
   * Thấy prompt có chữ `"Budget: <= 10 tool calls"`, Hook cho phép `sys.exit(0)` (ALLOW) chạy thẳng, bỏ qua hoàn toàn bước gọi Sol Planner.
   * **Khắc phục:** Mở rộng regex nhận diện cả tiếng Anh (`implement`, `add`, `feature`, `update`, `target files`, `files:`, v.v.).

2. **Lệch Timeout Vật Lý Trong `config.yaml`:**
   * Trong `config.yaml`: hook `guard_dispatch_contract.py` cấu hình `timeout: 5` (5 giây).
   * Trong khi đó `sol_planner.py` gọi sang OmniRoute `:20129` để suy luận Sol High cần **15 – 25 giây** (`timeout=25`).
   * **Hậu quả:** Hermes Agent kill tiến trình hook sau 5s, và mặc định bỏ qua lỗi timeout để thả cho tool call chạy ra ngoài mà không chặn lại.
   * **Khắc phục:** Cấu hình timeout của hook `guard_dispatch_contract` trong `config.yaml` tối thiểu **30 giây**.
