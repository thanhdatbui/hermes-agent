# Claude CLI Reviewer Hand-off: Scope Isolation and Test Mapping Timeout Defense (2026-10-09)

## 1. Bối cảnh & Hiện tượng (Incident 09/10/2026)
Trong phiên chốt phiên repository `D:/Taadaa/Tiktok-video`:
- Candidate commit gặp 3 lần liên tiếp bị Reviewer Sol High (:20129) từ chối tại ngưỡng điểm 82–84/100 (yêu cầu $\ge 85$).
- Cổng kích hoạt tín hiệu `[REVIEWER_HANDOFF_TRIGGERED]` sau 3 lần từ chối cho cùng `scope_hash`.
- User phê duyệt chuyển giao cho Claude CLI: *"Đẻ claude cli sửa nốt"*.
- Claude Code CLI (`claude -p "$(< ...)" --dangerously-skip-permissions --model sonnet`) được điều phối để tự sửa mã nguồn theo đúng các finding của Reviewer. Claude đã sửa xuất sắc 4 file và viết mới bộ test `tests/test_pipeline_common.py`.

## 2. Bẫy Timeout 120s do Monolith Test Mapping (The Monolith Test Mapping Trap)
- **Hiện tượng**: Khi Coordinator gom commit và chạy `closeout_gate.py`, cổng fail ngay ở Step 3 với lỗi:
  ```
  · Chạy tests: python -m pytest tests/test_pipeline_common.py tests/test_tiktok_workflow.py --tb=short -q
  ✘ Tests timeout sau 120s
  ✘ Focused tests FAILED (0 failed, 1 errors) in 120.0s
  ```
- **Nguyên nhân**:
  1. Trong commit vô tình sót lại file `scripts/tiktok_workflow/path_resolver.py` từ thao tác trước đó.
  2. Bảng ánh xạ `TEST_MAP_RULES` trong `closeout_gate.py` có quy tắc:
     `("scripts/tiktok_workflow/", "tests/test_tiktok_workflow.py")`
  3. File `tests/test_tiktok_workflow.py` là một test suite khổng lồ (>7.500 dòng, 433 tests, chứa nhiều test cũ chậm và phụ thuộc phức tạp), khiến pytest chạy quá 120s và bị cổng ngắt với `TEST_FAILED` (score 0).
  4. Mặc dù `tests/test_pipeline_common.py` đã có mặt, hàm `run_tests` gộp toàn bộ các test tìm được vào danh sách chạy.

## 3. Quy trình Cô lập Scope & Phòng ngừa (Remediation Discipline)
1. **Strict Candidate Scope Isolation**:
   - Khi áp dụng bản vá của Claude CLI, Coordinator **BẮT BUỘC** chỉ stage và commit đúng các file thuộc phạm vi remediation của Claude CLI (`scripts/pipeline_common.py`, `scripts/download_by_niche.py`, `scripts/auto_rescan_loop.py`, `tests/test_pipeline_common.py`).
   - Unstage và restore sạch sẽ bất kỳ file nào không thuộc phạm vi (dùng `git restore --staged` và `git checkout -- <file>`).
2. **Direct Test Bypass**:
   - Khi commit CHỈ chứa các file thuộc package chung kèm file test chuyên biệt (`tests/test_pipeline_common.py`), `closeout_gate.py` nhận diện `direct_tests = ["tests/test_pipeline_common.py"]`.
   - Kết quả: Pytest chỉ chạy đúng 6 tests focused trong **0.3s** (100% PASS).
3. **Nghiệm thu dứt điểm**:
   - Sol High chấm ngay: **86 / 100 (APPROVED)** (Logic 31/35, Test 22/25, Telemetry 12/15, Safety 13/15, Architecture 8/10).
   - Ngay sau đó tiến hành `git push origin main` thành công và ghi sổ cái `gate_audit.jsonl`.
