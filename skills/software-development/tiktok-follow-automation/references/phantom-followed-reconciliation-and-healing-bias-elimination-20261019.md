# Phantom Followed Reconciliation & Dynamic Weak Healing Bias Elimination (2026-10-19)

## 1. Sự Cố Dữ Liệu Phantom Followed Trước 01/10 & Tool Đối Soát
- **Bản chất sự cố**: Trước đợt vá verify Path-B ngày 01/10, runner thực hiện tap nút follow nhưng không kiểm chứng hậu thao tác (pull-to-refresh). Khi TikTok âm thầm nhả nút (shadow drop), runner vẫn ghi nhận UID đó vào từ điển `followed` trong file state JSON.
- **Hậu quả kép nghiêm trọng**:
  1. *Cháy tệp target nội bộ*: State ghi nhận đã follow 115–145 UID (trong khi thực tế web chỉ có 30–43 follow). Bộ lọc `is_followed(uid)` loại bỏ sạch các nick trong farm, ép runner phải tìm đến các target lạ hoặc anchor ngoài luồng, dễ bị TikTok quét rate-limit.
  2. *Phân loại sai Cohort*: Hệ thống thấy `len(followed) > 100` tưởng nhầm là cựu binh dày dặn (`veteran`), cấp quota cao khiến nick non bị quá tải.
- **Công cụ khắc phục chuẩn hóa (`tools/reconcile_phantom_followed.py`)**:
  * Đối soát danh sách following thực tế từ snapshot web (`tiktok_tracker.db` / snapshot JSON) với từ điển `followed` trong `runs/state/follow_state_*.json`.
  * Chỉ dọn dẹp các UID ghi nhận trước mốc `2026-10-01T00:00:00+00:00` mà thực tế web không có.
  * Tự động sao lưu bản gốc `.bak_reconcile_<timestamp>` trước khi áp dụng `--apply`.
  * Ghi audit log chi tiết tại `runtime/reconcile_phantom_followed/reconcile_audit.jsonl`.

## 2. Kỷ Luật Warmup Sau Cooldown & Chống Đổ Lỗi Anchor
- **Quy tắc cấp Quota sau án phạt dài**:
  * Khi một nick vừa mãn hạn cooldown sau chuỗi án dài (`fail_streak >= 2` hoặc $\ge 3$): **TUYỆT ĐỐI CẤM ép nick chạy 3–4 follow ngay cữ đầu tiên**.
  * Bắt buộc cấp ngân sách thận trọng: **1 – 2 follow dò đường** trong Phiên 1 (06:00).
  * Mục tiêu tối thượng của cữ ra tù là **LẤY THÀNH TÍCH SẠCH (Clean Day)** để xả án tích, tích lũy `clean_days` để tốt nghiệp, tuyệt đối không tham sản lượng.
- **Không quy chụp lỗi Anchor lên tài khoản cá nhân**:
  * Khi nick thực hiện follow Anchor (nick Tik 1/Tik 2) mà bị nhả: Đây là tín hiệu do phía tài khoản Anchor hoặc TikTok shadow-drop chung, không phải vi phạm hành vi spam của nick đang chạy.
  * CẤM tăng `fail_streak` hay tống nick vào chu kỳ cooldown dài ngày nếu nick chỉ mới trượt ở bước kết nối Anchor.

## 3. Xóa Bỏ Thiên Kiến Row Trong Ca Dưỡng Sinh N3 Tối & N4 (`healing_selector.py`)
- **Sai lầm kiến trúc cũ**:
  * Cho rằng Row 1, Row 2 là hàng cựu binh khỏe nên trong 4 ca dưỡng sinh (ca tối Ngày 3 và cả 3 ca Ngày 4) chỉ ưu tiên đưa các Row 7, Row 8 ra chạy.
  * *Hậu quả thực tế*: 50 nick Row 1 và 58 nick Row 2 đang dính án phạt `streak >= 2` (giam 5–15 ngày) bị bỏ đói nhịp dưỡng sinh, thiếu tương tác lướt feed để xả cờ bot của TikTok.
- **Công thức chấm điểm áp lực án phạt mới**:
  $$\text{Score} = 100 \times \text{fail\_rate} + \mathbf{60 \times avg\_streak} + 20 \times \text{young\_rate}$$
  * Trong đó `avg_streak = sum(fail_streak) / total_accounts` đo mật độ án phạt thực tế của cả hàng.
  * Kết quả chấm điểm thực tế: Row 2 đạt **254.62**, Row 1 đạt **213.75** (vượt trội so với Row 5–8 ở mức 70–95), đưa Row 2 và Row 1 lên vị trí ưu tiên cứu hộ hàng đầu.
- **Phân định 2 chế độ vận hành Farm**:
  * *Chế độ 1 — Ca Cày Sản Lượng (N1, N2, N3 sáng/trưa)*: Chạy đồng loạt theo Row để tối ưu KPI follow và video. Row 1 & 2 chạy sáng N1, N2 để acc khỏe mở đường trên dải IP mới làm nguội sau ngày nghỉ.
  * *Chế độ 2 — Ca Dưỡng Sinh (N3 tối, N4 cả ngày)*: Chạy theo mô hình **Per-Device Dynamic Slot** (0-follow, chỉ lướt feed + up video). Mỗi máy tự bốc slot/row có `fail_streak` dài nhất trên chính máy đó để cấp cứu.
- **Tại sao không chuyển sang Pure Random**:
  * Bốc ngẫu nhiên thuần túy dẫn tới bẫy Coupon Collector (có nick bị bỏ đói 10–14 ngày, có nick bị bốc trùng liên tục), phá vỡ chỉ tiêu 1 video/ngày và mất dấu vết truy vết khi xảy ra sự cố.

## 4. Ngân Sách Diff Thẩm Định Closeout Gate (Sol High 20KB Cap vs Gate 30KB)
- **Cạm bẫy cắt tỉa ngầm**:
  * `closeout_gate.py` có giới hạn cứng `MAX_DIFF_BYTES_GATE = 30_000` (Step 2 fail-fast).
  * Tuy nhiên, `sol_payload_guard.py` chỉ cấp tối đa ~20.8KB payload cho diff text.
  * Nếu candidate diff nằm trong khoảng 21KB – 30KB: Gate không chặn ở Step 2, nhưng payload guard sẽ tự động cắt tỉa diff và chèn `TRUNCATION_MANIFEST`.
  * Reviewer Sol High lập tức bắt lỗi thiếu ngữ cảnh (`NEED_CONTEXT`, test bị lược một phần) và chấm rớt 76–79/100.
- **Biện pháp khống chế**:
  * Luôn kiểm tra `git diff <base>..HEAD -- <files> | wc -c` đảm bảo $\le 18.000 - 20.000$ bytes trước khi chạy Gate.
  * Dùng helper dùng chung tinh gọn (`_safe_int(v, d, lo, hi)`) thay vì lặp lại các khối try-except cồng kềnh.
  * Rút gọn docstrings trong test suite, giữ assertions tập trung vào các bất biến hành vi.
  * Nếu thay đổi logic lớn đi kèm test dày: phân rã thành các commit O(1) tuần tự để closeout từng phần.
