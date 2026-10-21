# Sol Reviewer NEED_CONTEXT & Multi-Scope Decomposition Invariant (2026-10-22)

## 1. Hiện Tượng Sự Cố (Symptom)
Khi chạy `closeout_gate.py` cho một phiên làm việc có nhiều file (ví dụ: 11 files gồm cả code lẫn tests), dù full test 19/19 passed, Sol Reviewer (:20129) vẫn từ chối chấm điểm với phán quyết:
`Verdict: NEED_CONTEXT`
`Model Response: NEED_CONTEXT:skill_lookup.py`

## 2. Căn Nguyên Kỹ Thuật (Root Cause)
1. **Bộ lọc an toàn Sol Payload Guard (`sol_payload_guard.py`):**
   - Hạn mức tổng budget mặc định cho Sol là `SOL_TARGET_BYTES = 36,000` bytes.
   - `split_budget(36000)` phân bổ 80% (~28.8KB) cho diff.
   - Khi gom 11 files vào 1 lần review, diff bị phình to. Hàm `digest_diff` chia đều ngân sách theo trọng số cho các file. Các file dài như `skill_lookup.py` (148 dòng) bị cắt cụt và gắn nhãn `(partial)` trong manifest:
     `NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>.`
2. **Kỷ luật khắt khe của Sol Reviewer:**
   - Khi thấy manifest cảnh báo file lõi bị cắt cụt `(partial)`, Sol tuân thủ triệt để chỉ thị: từ chối chấm điểm mù và lập tức yêu cầu cung cấp ngữ cảnh đầy đủ bằng `NEED_CONTEXT:<path>`.

## 3. Quy Chuẩn Khắc Phục (Gate 1 Decomposition O(1))
1. **Phân rã phạm vi review (Scope Decomposition):**
   - Tuyệt đối CẤM nhồi toàn bộ 10-15 files của nhiều tính năng độc lập vào 1 lần chạy `closeout_gate.py`.
   - Phân tách theo đúng ranh giới ngữ nghĩa của công việc:
     + Phân hệ A (ví dụ: Dynamic Skill Routing): 8 files (code + tests) -> Diff gọn gàng, đạt Level L0 (0% omitted/partial).
     + Phân hệ B (ví dụ: Farm Error KB): 3 files (code + tests) -> Diff Level L0.
2. **Kiểm tra trước mức độ Digest (Pre-flight Level L0 Check):**
   - Trước khi gửi lên OmniRoute, kiểm tra `digest.level == "L0"` và `digest.omitted == []`. Nếu xuất hiện `(partial)` trên file production, lập tức thu hẹp scope `--files`.
