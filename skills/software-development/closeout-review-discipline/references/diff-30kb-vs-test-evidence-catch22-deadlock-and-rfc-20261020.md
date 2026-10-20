# Bẫy Con Gà & Quả Trứng: Diff 30KB vs Test Evidence Deadlock & RFC Thẩm Định (20/10/2026)

## 1. Hiện Tượng & Bối Cảnh Sự Cố Sáng 20/10/2026
Trong phiên làm việc nâng cấp script `deploy/hermes-home/scripts/cron_night_tiktok_2fa_watchdog.py` từ đơn nhiệm (2FA TikTok) thành chuỗi **Night Chain liên hoàn** (Phase 1: Reg Gmail 00:00 -> Phase 2: Add 2FA TikTok, tách báo cáo Telegram 2 nhóm riêng biệt):
- Mã nguồn đã hoàn thiện 100%, 23/23 unit tests pass, `--dry-run` chạy thực tế thành công.
- Tuy nhiên, quy trình chốt phiên `closeout_gate.py` bị kẹt trong vòng lặp vô tận suốt cả buổi sáng, không thể đóng phiên.

---

## 2. Phân Tích Root Cause từ Claude Sonnet 5.5 Kiến Trúc Sư

### A. Mâu Thuẫn Cấu Trúc (Self-Contradiction / Catch-22)
Gate đang dùng **duy nhất một trục đo lường (byte-size của diff gộp)** để giải quyết **hai tiêu chí trực giao nhau**:
1. `MAX_DIFF_BYTES_GATE` = 30,000 bytes (30KB) là proxy cho *mức độ phức tạp / rủi ro* (diff càng nhỏ càng an toàn).
2. `test_evidence` của Reviewer Sol High (:20129) là proxy cho *độ tin cậy / chứng chỉ an toàn* (có test đầy đủ mới an toàn).

**Nghịch lý tự hủy:**
- Script Night Chain thực tế có diff ~23.3KB.
- File unit test `test_cron_night_tiktok_2fa_watchdog.py` có diff ~9.5KB.
- **Nếu đưa cả 2 file vào `--files`:** Tổng diff $23.3\text{KB} + 9.5\text{KB} = 32.8\text{KB} > 30\text{KB} \rightarrow$ Gate fail-fast ngay lập tức với lỗi `[Gate Fail-Fast: DIFF_TOO_LARGE]`.
- **Nếu chỉ đưa script vào `--files` để lách trần 30KB:** Reviewer chỉ thấy diff của script mà không thấy diff code test đi kèm, lập tức trừ nặng điểm ở tiêu chí `test_evidence` (chỉ cho 20/30 điểm), kéo tổng điểm xuống 76–78/100 (< 80 Grace Band, < 85 Strict Approved).

Không tồn tại bất kỳ điểm nào trên không gian nghiệm mà task "refactor chuỗi nghiệp vụ + test đầy đủ" thỏa mãn được cả hai điều kiện cùng lúc nếu tổng tự nhiên $> 30\text{KB}$.

### B. Vòng Lặp Strike-3 Reviewer Hand-off Vô Hạn
Khi trượt điểm 3 lần liên tiếp:
1. `closeout_gate.py` in cờ `[REVIEWER_HANDOFF_TRIGGERED]` và ép chuyển giao cho Reviewer CLI (Claude / Agy) tự sửa.
2. Reviewer CLI sửa thêm các tiêu chuẩn khắt khe (bổ sung khóa file liên tiến trình `_state_lock()`, kiểm tra status Telegram, atomic merge state)...
3. Mỗi lần sửa thêm tính năng an toàn, **diff của script lại càng phình to hơn**, đẩy tổng kích thước lên cao hơn.
4. Mỗi vòng remediation chỉ dịch chuyển agent qua lại giữa 2 trạng thái fail:
   $$\text{DIFF\_TOO\_LARGE (khi kẹp test)} \;\longleftrightarrow\; \text{THIẾU TEST\_EVIDENCE (khi bỏ test)}$$
   Đây là **Mechanical Deadlock (Tê liệt cơ học)**, chạy bao nhiêu vòng cũng không thể tự hội tụ.

---

## 3. RFC Giải Pháp Cơ Học Cho `closeout_gate.py`

### RFC-1: Tách Trục Đo Lường (Decouple Size vs. Evidence) — Khuyên Dùng Cao Nhất
- Quy định `MAX_DIFF_BYTES_GATE` (30KB) **chỉ tính trên diff của Production Code** (loại trừ các file thuộc `tests/**`).
- File test được kiểm duyệt độc lập: chạy pytest focused để lấy test execution evidence, và diff của test được truyền riêng cho Reviewer chấm điểm `test_evidence` mà không bị tính vào ngân sách trần của code thực thi.
- *Kết quả:* Script 23KB nằm an toàn dưới 30KB; test 10KB được đưa vào đầy đủ giúp Reviewer chấm điểm >= 85 ngay từ lượt đầu.

### RFC-2: Trần Diff Co Giãn Theo Bằng Chứng (Evidence-Adjusted Ceiling)
- Thiết lập công thức:
  $$\text{Effective\_Cap} = \text{BASE\_CAP} + \alpha \times \text{test\_diff\_bytes} \quad (\alpha = 0.5 \to 1.0)$$
- Nguyên lý kiến trúc: *Một diff lớn có bộ test bao phủ chặt chẽ an toàn hơn gấp nhiều lần một diff nhỏ nhưng không có test.*

### RFC-3: Strike-3 Escalation Thay Vì Vòng Lặp Tự Sửa Vô Hạn
- Khi phát hiện điều kiện:
  1. 100% focused tests pass (0 fail, 0 error).
  2. Điểm logic correctness đạt chuẩn.
  3. Duy nhất bị cản trở bởi trần byte-size hoặc thiếu diff test do phân rã scope.
- Strike-3 không được đùn cho Worker/Reviewer CLI lặp lại việc sửa code mò mẫm, mà phải kích hoạt **Lane Ngoại lệ có Audit (Operator Override Token - Fail-Closed)** để giải phóng phiên làm việc dứt điểm theo phê duyệt của Operator.
