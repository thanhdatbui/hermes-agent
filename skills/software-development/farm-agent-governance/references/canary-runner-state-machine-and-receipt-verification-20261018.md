# Canary Unified Runner State Machine & Sealed Receipt Protocol (18/10/2026)

## 1. Bối cảnh & Điểm nghẽn lịch sử (Canary Deadlock)
Trước ngày 18/10/2026, hệ thống điều phối gặp nghịch lý:
- `done_gate.py` quy định cứng: Mọi bản vá automation bắt buộc phải chạy Canary trên thiết bị thật trước khi báo DONE.
- Nhưng `guard_terminal.py` lại chặn lệnh runner chính thức (`run_follow.py` / `run-follow.ps1`), đẩy Coordinator vào thế kẹt "cửa chính khóa, cửa phụ chặn", dẫn đến việc Coordinator tự chỉ đạo subagent đẻ script probe ad-hoc rồi tiếp tục bị Guard dập tắt.
- Khi bị Guard dập, Coordinator rơi vào phản xạ đóng băng, than thở và đùn việc cho Operator ("anh chạy giúp em", "xin mở allowlist"), bị Operator chấn chỉnh nghiêm khắc.

---

## 2. Bản Thống Nhất 3 Bên (Claude Sonnet 5.5 - Advisor Sol - Coordinator)
1. **G1 (Khóa sửa code qua `delegate_task`):**
   - `delegate_task` chỉ được cấp toolset Read-Only (đọc log, research, soi hiện trường).
   - 100% thao tác sửa code và test bắt buộc đi qua Single Dispatch Gateway (`dispatch_worker.py` - Haiku 5.5 / Agy CLI) với `WORKER_TOKEN`.
   - Van an toàn `WORKER_CLI_EXHAUSTED` chỉ được mở khi Gateway tự quan sát thấy cả 2 CLI cạn quota (kèm token HMAC có nonce dùng 1 lần, chống replay).
2. **G2 (Chặn probe ad-hoc):**
   - Bác bỏ hoàn toàn việc tạo shim binary `adb.exe` trên Windows OS vì sẽ đánh sập hàng chục cronjob/watchdog tự động 24/7 của Farm (`healing_selector`, `reboot`, `post_noon_chain_watchdog`...).
   - Chỉ chặn ở PreToolUse hook của Hermes (chặn tạo script probe rác và chặn lệnh ngoài luồng trong chat).
3. **Canary Unified Entrypoint & Sealed Receipt (`canary_runner.py`):**
   - Đóng gói 1 entrypoint duy nhất: `D:/Taadaa/tools/canary_runner.py`.
   - State machine: `RESOLVE -> PREFLIGHT -> RUN -> CAPTURE -> OCR_VERIFY -> RECEIPT`.
   - Hỗ trợ phân định nghiêm ngặt: `--machine <N>` (hotfix 1 máy) vs `--machines <N1,N2,N3...>` (canary diện rộng bắt buộc $\ge 3$ máy).
   - Xóa bỏ cờ `.canary_passed` trơn. Bắt buộc sinh `D:/Taadaa/.canary_receipt.json` và `.canary_passed` chứa JSON niêm phong: `commit_sha`, `media_path`, `media_sha256`, `ocr_snippet`, `runner_status: success`.
4. **G3 (Output Filter & Chống Báo Blocked Lười):**
   - Hook chặn đứng mọi phản hồi chứa mẫu câu than thở, đùn việc cho Operator khi bị Deny.
   - Deny bắt buộc kèm `NEXT_ACTION`.
   - Báo `BLOCKED` chỉ hợp lệ khi: có reason code từ enum chuẩn, có đường dẫn evidence vật lý thực sự tồn tại trên đĩa, và `NEXT_ACTION` đã được thử tự động nhưng thất bại.

---

## 3. Triển khai & Kiểm chứng thực tế
- Entrypoint: `python D:/Taadaa/tools/canary_runner.py --repo <repo> --machine <N> --row 1 --force-preempt --timeout 180`
- Cổng nghiệm thu: `python D:/Taadaa/tools/done_gate.py --repo <repo>`
- Unit test bảo vệ: `pytest D:/Taadaa/tools/tests/test_canary_runner.py` (2 passed).
- Hiện trường Máy 2: Sau khi chạy runner, ảnh `D:/Taadaa/reports/canary_tiktok-follow_m2_1792307185.png` (1.09 MB) được chụp, WinRT OCR đối soát icon launcher sau khi teardown thành công, `done_gate.py` trả về `GATE-PASS: Canary verified on real device.` (exit code 0).
