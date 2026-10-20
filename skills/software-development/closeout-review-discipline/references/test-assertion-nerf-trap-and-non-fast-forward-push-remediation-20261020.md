# Test Assertion Nerf Trap & Non-Fast-Forward Auto-Push Remediation (20/10/2026)

## Context & Incident RCA

Trong phiên làm việc ngày 20/10/2026 khi thi công chốt chặn Canary Gate (`canary_runner.py` và `safe_push.py`), hệ thống gặp 2 sự cố điều phối liên tiếp trong quá trình Closeout Gate:

### 1. Bẫy Rút Gọn Test Quá Đà Làm Yếu Assertion (Test Assertion Nerf Trap)
- **Hiện tượng:** 
  - Lần chạy đầu tiên đạt 84/100 điểm (Grace Band). Tuy nhiên, `gate_common._grace_ok` kiểm tra `diff_lines <= 300` và `diff_files <= 4`. Tổng số dòng diff là 422 dòng (`canary_runner.py` + `safe_push.py` + 2 test files), vượt trần 300 dòng dẫn đến:
    `[CLOSEOUT_TOKEN_SKIPPED: score 84 rejected: grace_conditions_unmet]`.
  - Nhằm ép tổng dòng diff xuống dưới 300 dòng, Coordinator đã chỉ đạo rút gọn test suite: gọt bớt `check.assert_called_once()`, thay `assert len(events) == 1 and events[0]["event"] == "owner_override"` bằng `assert any(...)`, bỏ bớt kiểm tra `calls == [1, 2, 3]`.
  - Hậu quả: Reviewer Sol High lập tức phát hiện các assertion bị làm yếu và hạ điểm từ 84 xuống 78 (REJECTED):
    > *"Chấm 78/100. Một số assertion quan trọng đã bị loại bỏ hoặc làm yếu (assertion audit và call-count đã mất)... khiến chất lượng bằng chứng regression thấp hơn con số test pass gợi ý. Cần khôi phục assertion audit và call-count đã mất..."*

- **Nguyên tắc Invariant rút ra:**
  - **CẤM TUYỆT ĐỐI GỌT BỚT ASSERTION ĐỂ ÉP BUDGET:** Vượt qua 100% test pass không có ý nghĩa nếu assertion bị làm yếu. Reviewer Sol High chấm điểm dựa trên độ sâu và độ tin cậy của bằng chứng regression.
  - **Phân định rõ 2 ngưỡng:**
    - `STRICT_APPROVED` (Score >= 85): **KHÔNG giới hạn trần dòng `diff_lines <= 300`**. Nếu code và test chất lượng cao, sâu sắc và chặt chẽ, Sol High sẽ chấm >= 85 và hệ thống tự động cấp token strict mà không xét điều kiện dòng.
    - `GRACE_APPROVED` (Score 80–84): Chỉ dành cho các bản vá nhỏ O(1) thật sự (`<= 4 files`, `<= 300 lines`). Không được "cố đấm ăn xôi" bóp méo test suite để chui vào Grace Band.

---

### 2. Bẫy Amend Commit Đã Push Gây Non-Fast-Forward (Amended Commit Rejection)
- **Hiện tượng:**
  - Trong một lượt chạy `closeout_gate.py --push` trước đó, commit `e907a8a` đã được push thành công lên `origin/main` trên GitHub.
  - Sau đó, ở local thực hiện `git commit --amend` để sửa test suite. Thao tác amend tạo ra commit mới `bc58d46` có cùng parent nhưng khác SHA với `e907a8a` trên remote.
  - Khi chạy lại `closeout_gate.py --push`, Reviewer chấm APPROVED và phát hành Closeout Token thành công, nhưng bước auto-push văng lỗi:
    ```text
    ✘ [Closeout Auto-Push] Push origin main thất bại (exit 1):
    ! [rejected] main -> main (non-fast-forward)
    hint: Updates were rejected because the tip of your current branch is behind its remote counterpart.
    ```

- **Quy trình xử lý chuẩn hóa:**
  1. **Cấm amend commit đã lên remote:** Trước khi chạy `git commit --amend`, bắt buộc kiểm tra `git log HEAD..@{u}`. Nếu commit đã nằm trên remote, CẤM amend.
  2. **Cách phục hồi khi bị phân kỳ:**
     - Kiểm tra diff giữa local và remote: `git diff origin/main..HEAD`.
     - Nếu diff chỉ là các chỉnh sửa dở dang/làm yếu test: Dùng `git reset origin/main` để đưa HEAD về khớp remote, sau đó dùng `git checkout origin/main <files>` để hoàn nguyên chính xác trạng thái sạch của remote.
     - Nếu có thay đổi mới thực sự cần giữ lại: Tạo một commit mới (linear history), tuyệt đối không force-push hay amend đè.
