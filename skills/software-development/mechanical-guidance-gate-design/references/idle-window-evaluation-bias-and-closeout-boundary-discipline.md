# Idle-Window Evaluation Bias and Closeout Boundary Discipline

## 1. Bối cảnh & Sự cố (Incident Analysis)
Trong phiên đối soát các rào chắn (Guard Hooks / Gates) tại Taadaa Farm, Coordinator đã mắc 2 sai lầm nghiêm trọng về phương pháp luận điều phối:
1. **Bẫy cửa sổ ngủ đông (Idle-Window Evaluation Bias):** Coordinator lấy số liệu vi phạm trong 4 giờ gần nhất khi User ít tương tác chat và Agent ít chạy lệnh (0 vi phạm) để ngụy biện rằng các chốt chặn "đã tự ổn định 100%, không cần thi công". Đây là sai lầm nguy hiểm vì 0 vi phạm chỉ phản ánh sự thiếu vắng hoạt động, chứ không chứng minh rào chắn đã hết lỗi. Khi đo toàn bộ lịch sử (All-Time), các ổ dịch thực sự hiện rõ: `FOREGROUND_TIMEOUT` (5.095 lần), `ROOT SCAN` (5.705 lần), `DISPATCH WORKER` (1.320 lần).
2. **Xâm phạm Closeout Gate (Closeout Boundary Invariant Violation):** Coordinator tự ý lôi `closeout_gate.py` vào danh sách mổ xẻ và đề xuất "Terminal Block", vi phạm trực tiếp bất biến: Closeout Gate đã hoạt động cực kỳ ổn định (chỉ 37 lần vi phạm toàn lịch sử, tự động remediate 3–7 phút qua Sol Repair, điểm >= 85), cấm tùy tiện can thiệp.

---

## 2. Quy Tắc Cốt Lõi (Invariants)

### Rule 1: Cấm Đánh Giá Ổn Định Bằng Cửa Sổ Ngủ Đông (No Idle-Window False Stability)
- **Sai lầm:** Nhìn vào khung giờ rảnh / ít tương tác rồi kết luận rào chắn an toàn hoặc không cần fix.
- **Tiêu chuẩn bắt buộc:** Mọi đánh giá ổn định rào chắn BẮT BUỘC phải chuẩn hóa theo:
  - Tỉ lệ vi phạm trên mỗi lượt dispatch / turn chat thực tế (Error rate per active turn).
  - Đối chiếu với mốc chuẩn (Baseline) lịch sử toàn thời gian.
  - Phân loại rõ ràng giữa **rào chắn ổn định thật sự** (như Closeout Gate: 37 lần all-time, tự remediate) và **ổ dịch thường trực** (hàng ngàn lần vi phạm mỗi khi Agent vào việc).

### Rule 2: Bất Biến Bất Khả Xâm Phạm Của Closeout Gate (Closeout Monopoly Protection)
- Closeout Gate thuộc vùng bảo vệ đặc quyền: Sol High độc quyền đề xuất patch O(1) qua `:20129` (First-Responder Monopoly), tự động remediate trong 3–7 phút.
- Coordinator và các phiên làm việc thông thường **CẤM TUYỆT ĐỐI** tự ý sửa đổi, thêm bớt quy tắc, hoặc gắn nhãn "Hard Block / Terminal Block" lên luồng Closeout.

### Rule 3: Triệt Tiêu 100% Khóc Lóc Bại Liệt (Zero-Block Action Mandate Hierarchy)
Mọi rào chắn khi phát hiện vi phạm BẮT BUỘC đi theo 3 nấc cơ giới hóa, TUYỆT ĐỐI CẤM dừng lại đùn việc cho User:
1. **REWRITE (Auto-Rewire):** Tự động nắn tham số/lệnh sang đường an toàn rồi cho chạy luôn (ví dụ: `delegate_task` sửa code $\to$ `dispatch_worker.py` O(1); timeout missing $\to$ clamp `timeout=60s`).
2. **MANDATE (Action Mandate O(1)):** Nếu không thể tự động sửa ngầm, Gate BẮT BUỘC trả về block `REQUIRED_ACTION_O1` kèm lệnh copy-paste chạy ngay trong turn để Agent tự thoát kẹt.
3. **PIVOT (Auto-Pivot):** Khi gặp giới hạn vật lý (máy bận ca chính):
   - Với tác vụ fungible (batch upload, reg hotmail): Tự động pivot sang máy rảnh tiếp theo trong pool.
   - Với tác vụ đích danh (`[MÁY N]`): Ghi nhận `SKIPPED_LOCKED` đưa vào hàng đợi chờ event nhả lock, Coordinator lập tức chuyển sang task độc lập khác trong hàng đợi, không đóng băng phiên.
