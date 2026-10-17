# Ad-Hoc Script Ban & Claude Architect / Worker Builder Division (2026-10-17)

## 1. Sự Cố Hiện Trường: Coordinator Tự Ý Đẻ Script Chữa Cháy
- **Nhu cầu**: Kênh `@huy010822` (Máy 18) đang có 3 video ghim (22K - 1.6K - 5.2K), cần nhả ghim 1.6K để ghim video 4.3K.
- **Vi phạm nặng nề**: Thay vì dùng và mở rộng canonical tool `pin_top_videos.py` (vốn đã có sẵn parser action sheet ghim/bỏ ghim), Coordinator lại tự viết một loạt script ad-hoc vụn vặt: `do_unpin_step1.py`, `do_unpin_step2.py`, `capture_m18.py`.
- **Hậu quả kép**:
  1. *Làm bẩn repo*: Các script tạm bợ không có telemetry, không có unit test, không có cơ chế timeout/guard.
  2. *Gây lỗi nghiêm trọng (Lạc nick & Gửi ảnh mù)*: Script ad-hoc tap mù theo tọa độ khi TikTok trên Máy 18 đang đứng ở nick `@hollybsulliv33` (Ly Bé), dẫn đến việc gửi nhầm ảnh của nick khác và báo cáo láo.
- **User bức xúc và chấn chỉnh**:
  > *"Bữa có đóng gói tool ghim r, h thêm nhả ghim nx chứ. Mày giỡn mặt tao hả"*
  > *"K những đi đẻ script ngu học, mày còn gửi tao cái kênh khác đéo liên quan kênh t yêu cầu sửa lúc đầu"*
  > *"vkl mày ơi vi phạm tùm lum thế t dã thiết kế gate rule guard cc gì đó dùng script có sẵn mày vẫn tự đi đẻ script, gọi claude cli vào tư vấn"*

---

## 2. Phân Vai Chuẩn Mực: "Bảo Nó Thiết Kế, Mày Thi Công"
Khi User chỉ thị: *"bảo nó thiết kế mày thi công"*, quy trình phối hợp phân tầng tối ưu giữa các model được xác lập:

1. **Claude CLI (Sonnet 5.5) — Vai Trò Kiến Trúc Sư (Planner / Solution Architect)**:
   - Gọi qua: `python D:/Taadaa/tools/claude_worker.py --role planner --timeout 120 "<prompt>"`
   - Khóa cứng: `--disallowedTools Edit,Write,NotebookEdit` (read-only, cấm đụng file).
   - Nhiệm vụ: Phân tích nguyên nhân gốc rễ, thiết kế blueprint chuẩn O(1) (dataclass, signatures, luồng rollback, confusable set). Không để Sonnet tự ý sửa code làm hao hụt token/quota.

2. **Coordinator / Worker (Haiku / Agy) — Vai Trò Thợ Thi Công (Builder / Execution)**:
   - Gọi qua: `python D:/Taadaa/tools/dispatch_worker.py --workdir D:/Taadaa/tools --file <file> --timeout 75 "<prompt>"`
   - Nhiệm vụ: Bám sát 100% blueprint của Architect để thi công code, viết test suite pytest bao phủ các nhánh.

3. **Claude CLI (Sonnet 5.5) — Vai Trò Giám Sát / Thẩm Định Độc Lập (Reviewer)**:
   - Gọi qua: `python D:/Taadaa/tools/claude_worker.py --role reviewer --max-turns 6 --timeout 75 "<review prompt>"`
   - Nhiệm vụ: Chạy pytest, rà soát lỗ hổng logic/security (như lọt case trailing digits khác nhau, fail-open switch check), ra phán quyết độc lập `VERDICT: APPROVED` hoặc `VERDICT: REJECTED`.

---

## 3. Quy Tắc Bất Biến Đóng Gói Canonical (`pin_top_videos.py`)
Mọi thao tác quản lý video ghim trên Farm BẮT BUỘC sử dụng duy nhất tool canonical `D:/Taadaa/tools/pin_top_videos.py`:

1. **Auto-Swap Logic**:
   - Khi kênh đã đạt trần 3 video ghim (`max_pins=3`):
   - So sánh view candidate mới với video ghim có view thấp nhất (`lowest = min(pinned, key=lambda t: t['views'])`).
   - Nếu candidate view cao hơn ➔ Tự động unpin lowest và pin candidate lên ➔ Trả về `status: "SWAPPED"`.
2. **Fail-Closed Account Assertion**:
   - Sau khi chuyển đổi tài khoản: BẮT BUỘC kiểm tra `curr.lower() != account.lstrip("@").lower(): raise RuntimeError(f'SWITCH_ACCOUNT_FAILED: expected @{account}, got @{curr or "UNKNOWN"}')`.
   - CẤM bỏ sót trường hợp `curr == ""` (TikTok chưa load xong profile).
3. **UI Transition Handling**:
   - Khi thoát video player về profile grid, xử lý phím BACK và chờ profile tiles render hoàn tất trước khi verify readback độc lập (`pinned_after < pinned_before` cho unpin, `pinned_after > pinned_before` cho pin).
