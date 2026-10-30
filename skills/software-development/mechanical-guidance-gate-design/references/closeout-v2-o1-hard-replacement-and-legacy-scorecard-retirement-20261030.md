# Closeout Gate v2 O(1) Replacement & Legacy 3000-Line Scorecard Retirement (2026-10-30)

## 1. Bối cảnh & Nguyên Nhân Sự Cố
Trong phiên làm việc 2026-10-30, sau khi hoàn tất sửa lỗi feed và đăng ký Invariant Rule, Coordinator khi nhận lệnh `Done` từ User đã theo quán tính gọi script cũ `closeout_gate.py` với cờ `--json-output` và chờ đợi OmniRoute AI Reviewer chấm điểm 91/100 kèm bảng scorecard hình thức (bureaucratic theater).
User đã phản ánh ngay lập tức: *"Là sao. Closeout gate sửa bỏ luôn vụ chấm điểm r. Sao mày lại đòi chấm điểm nữa. Bữa session kia thống nhất dùng closeout mới r xoá cái cũ r mà?"*

## 2. Bản Chất Triệt Tiêu "Diễn Tuồng Quan Liêu"
Session trước (@session:default/20261026_171659_e2cabbf5) đã thống nhất giữa 3 bên (Claude, Sol, Coordinator):
- **Khai tử triệt để:** Không gọi AI Reviewer chấm điểm cảm tính 81 vs 87 điểm.
- **Không vòng vo:** Không sinh bảng scorecard dài dòng khi chốt phiên.
- **Tiêu chuẩn O(1) duy nhất (`closeout_v2.py`):**
  1. **Phiên Vận Hành (Operational):** Không có code delta -> PASS ngay trong < 0.05s (`python D:/Taadaa/tools/closeout_v2.py --operational --json-output`).
  2. **Phiên Code (Code Verified):** Chỉ chạy `py_compile` cú pháp + `pytest` focused thật sự. Test PASS -> cấp `APPROVED` ngay lập tức.

## 3. Kiến Trúc Khóa Cứng Tầng Cơ Học (Mechanical Lock-in)
Để ngăn chặn hoàn toàn việc các agent hoặc prompt cũ gọi nhầm vào script chấm điểm 3.000 dòng:
1. **Di dời file cũ vào kho lưu trữ:**
   - Toàn bộ 3.000 dòng của `closeout_gate.py` cũ đã được di chuyển vĩnh viễn vào `D:/Taadaa/tools/_retired/closeout_gate_legacy.py` (nằm chung với `plan_exec_gate`, `evidence_gate_verifier`, `safe_push_legacy`).
2. **Biến `closeout_gate.py` thành Direct Forwarder:**
   - File `D:/Taadaa/tools/closeout_gate.py` ở root được thay thế hoàn toàn bằng forwarder trực tiếp gọi `closeout_v2.main()`.
   - Bổ sung `parse_known_args()` và nhận diện `--files` trong `closeout_v2.py` để tương thích 100% với mọi lời gọi cũ.
   - Bất kể agent hay tool nào gọi `closeout_gate.py` hay `closeout_v2.py`, hệ thống đều thực thi cơ chế mới O(1) (<0.05s), loại bỏ 100% việc gọi AI chấm điểm.
