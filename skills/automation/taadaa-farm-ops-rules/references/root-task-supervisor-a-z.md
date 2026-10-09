# Root-task Supervisor và A-Z Continuation

## Khi áp dụng
Dùng khi User yêu cầu làm từ A-Z/đến khi xong qua nhiều phase code, test, live canary, rollout hoặc closeout.

## Lỗi kiến trúc cần tránh
`delegate_task` là child có vòng đời hữu hạn; child hoàn tất/timeout không đảm bảo parent tự nối phase. Không dùng chuỗi child rời rạc làm workflow engine và không bắt User nhắn để kick phase tiếp theo.

## Contract bắt buộc
Duy trì persistent `state.json`/`ledger.json` với `incident_id`, `phase`, `status`, target cursor, last evidence, resume token và `next_action`. Phase live chuẩn:

`CODE_VERIFY → M7_CANARY → M11_CANARY → M40_CANARY → M66_CANARY → FLEET_REOPEN → CLOSEOUT`

Child report chỉ dùng: `DONE`, `CHECKPOINT`, `FAILED_RETRYABLE`, `FAILED_FINAL`, `NEEDS_DECISION`. Mọi trạng thái khác `DONE` phải có `next_action`. `CHECKPOINT: LOCK_HELD` không kết thúc root task; supervisor/job runner phải tiếp tục theo dõi ngoài LLM.

## Phân vai
- **code-surgery:** patch/fixture/focused test offline; không giữ device lock.
- **monitor/preemption:** đọc PID, lock, heartbeat, progress; gửi drain nếu có API; trả checkpoint nhanh; không chờ lock.
- **live-runner:** chạy official canary/rollout khi đã acquire lock và thu exit code, screenshot, XML/OCR, artifact/log.
- **detached job runner:** poll lock/heartbeat, ghi state/events, resume phase idempotently; không để LLM child ngủ/chờ.

## Anti-excuse
Fixture stale, dirty file ngoài scope, canonical repo khác consumer, thiếu live evidence cho phần offline, timeout transient hoặc scope của child không được dùng để dừng root task. Phải reroute/retry/escalate. Child `DONE` chỉ đóng phase được giao; supervisor tự chuyển phase kế tiếp. Khi timeout, resume từ ledger/checkpoint, không làm lại từ đầu.

## Khi nào hỏi User
Chỉ hỏi credential/2FA thiếu, identity mismatch không thể tự resolve, destructive/force-stop run healthy, hoặc quyết định nghiệp vụ. Không hỏi lại để xin phép hành động reversible đã được ủy quyền.

## Closeout gate
Không báo `DONE` trước khi các canary bắt buộc có exit code và screenshot/XML/OCR/artifact evidence, fleet reopen được verify, smoke hậu reopen pass và ledger closeout ghi xong. Seed ledger bằng facts/tree hash đã xác minh để skip code/test đã pass.

## Budget gợi ý
- code-surgery: 35 iterations / 1200s.
- monitor: 12 iterations / 300s.
- live-runner: 20 iterations / 600s.
- hard cap incident: 24 children, 8 giờ; task cần vượt cap phải tách hoặc hỏi theo NON_OVERRIDABLE.
