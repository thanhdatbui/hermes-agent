# False-Failure Accounting and Cooldown Guard

## Trigger
Use this reference when reviewing TikTok follow state, `fail_streak`, account cooldowns, proxy/IP breakers, Path-B verification, anchor-follow logic, or any report that a nick was punished without a confirmed follow drop.

## Ground truth contract
A follow failure is confirmed only when all of these are true:

1. A real follow tap was actually delivered and recorded.
2. A fresh post-tap or post-reload observation was captured.
3. The observed profile identity is bound to the expected UID/handle.
4. The action state is freshly classified as `not_followed`.
5. The navigation/reload/restore steps needed for that observation completed successfully.

Anything else is `MANUAL_REVIEW` / unknown. In particular, do not call `set_follow_failed()` for:
- failed reload or refresh;
- no Follow button found or tap exception;
- wrong screen, stale XML, OCR-only evidence without identity binding;
- target not found, no-video, or external priority target resolution failure;
- an anchor tap whose result cannot be bound to the anchor identity.

## State-mutation rules
- Put the active `cooldown_until_at` guard before every other mutation. A duplicate callback during active cooldown must be a byte-level no-op: no save, timestamp update, streak change, ceiling change, or breaker call.
- Account-level `set_follow_failed()` must not trip or consult a machine/IP circuit breaker. IP risk is an independent aggregate signal and must be evaluated by monitor/audit logic, not by one account mutator.
- Preserve the distinction between a clean business outcome (`FOLLOW_FAILED` with account cooldown) and a dirty technical failure (`MANUAL_REVIEW`, reload failure, identity mismatch, persistence failure). The latter must remain fail-closed and must not silently punish the account.
- Only a fresh, identity-bound `not_followed` result after a real tap/reload may increment failure state.

## Tail-drop reporting: accepted follows are not jail

When a machine has `followed_count > 0` or a non-empty `followed` list but ends with `status=FOLLOW_FAILED`, classify it as **tail-drop / account ceiling**, not as a zero-success failure or persistent jail. The runner may fail-closed after a later profile verification rejects the next follow even though earlier follows were accepted.

### Root cause of "Thành công (0 máy)" contradiction in watchdog
In `watchdog/formatters.py` (`classify_machine_follow_result`), checking status before `len(flist)` causes machines that achieved successful follows before a terminal drop to be misclassified:
```python
# ❌ Anti-pattern: Status check takes precedence over actual work delivered
if status == "FOLLOW_FAILED" and fd.get("follow_failed") is True:
    return "released", f_reason
if str(status).upper() in {"OK", "SUCCESS", "COMPLETED"} and len(flist) > 0:
    return "success", f_reason
```
If a machine followed 3 UIDs and hits a drop on the 4th, `status` is `FOLLOW_FAILED` with `follow_failed=True`. The classifier puts it into `fl_released` and leaves `fl_success` empty (0 machines), outputting:
`  + Thành công (0 máy | 0.0%): Không có`
while simultaneously reporting `Follow chéo (3 lượt)` and `Nhả follow: M59: 3 lượt`.

### Required report semantics:
- `used > 0`: accepted follows are real; report the accepted count and the terminal rejection separately. Do not increment `fail_streak`; apply only the short cooldown defined by the state machine; do not trip the IP breaker from this event alone.
- `used == 0`: only the zero-follow path may advance `fail_streak`; persistent-jail classification requires the configured repeated zero-follow threshold, not one `FOLLOW_FAILED` status.
- Never classify from `FOLLOW_FAILED` alone. Inspect `follow_result.json` and the matching `log.jsonl` event, including `followed`, `followed_count`, `failed`, `follow_failed`, `reason`, `fail_streak`, and cooldown fields.
- Prevent contradictory output such as `Follow chéo (N lượt)` together with `Thành công (0 máy)`:
  Trong `feed_session_watchdog.py`, khi `category == "released"`, BẮT BUỘC kiểm tra `if len(flist) > 0: fl_success.append(m)`. Máy ăn nhả đuôi vẫn phải có mặt trong `fl_success` để ghi nhận số lượt follow thành công vào nhóm tương ứng (Hồi phục 1/2, Cấp Khỏe), đồng thời vẫn xuất hiện ở `fl_released` kèm số lượt `(M59: 3 lượt)`.
  Mẫu số tổng máy chạy BẮT BUỘC dùng tập hợp hợp: `total_fl_candidates = len(set(fl_success) | set(fl_released))` để tỷ lệ % không bị nhân đôi.

### Bẫy ngộ nhận "Nhả liền cả đống (0 lượt)" trong Watchdog (Anchor Drop vs Cooldown Skip vs Bug State)
Khi Watchdog báo danh sách dài các máy bị "Nhả liền (0 lượt | 100.0%)" (ví dụ 49 máy fl=0), Operator thường nghi ngờ "script báo láo" hoặc Coordinator ngộ nhận "TikTok ban hàng loạt IP". Cần nắm vững bản chất kỹ thuật để đối soát và giải trình:

1. **Căn nguyên cấu thành số liệu trong Watchdog (`watchdog/formatters.py`):**
   - `format_released_follows` gom toàn bộ máy có `status == "FOLLOW_FAILED"` và `followed_count == 0` vào nhóm `rel_0` ("Nhả liền (0 lượt)").
   - Thực chất con số này gồm 3 nhóm hoàn toàn khác nhau:
     * **Live Anchor Drop (Nhả Anchor thật tại trận):** Bot vào video của Anchor, bấm follow, back ra profile rồi pull-to-refresh. Server TikTok silent-drop (nút đỏ Follow bật lại, không lên Nhắn tin). Theo invariant "Anchor nhả = block", bot ngắt phiên ngay tại giây thứ 30 để cứu nick (`status: FOLLOW_FAILED, reason: anchor @... bị nhả sau vuốt — dừng session`). Đây là vấn đề trust/độ ấm cá nhân của nick (đặc biệt các nick slot phụ Row 3/Row 4), KHÔNG PHẢI do TikTok ban IP hàng loạt.
     * **Daily Cooldown Skip (Kế thừa án phạt từ ca trước trong ngày):** Nick đã bị dính `follow_failed: True` ở ca trước. Khi ca sau chạy, `run_session` fail-closed ngay lập tức trước khi đụng vào app (`reason: follow trước đó không lên (TikTok không nhận) — dừng session, cooldown trong ngày`), trả về payload `FOLLOW_FAILED` với 0 lượt follow.
     * **State Parser Trap (`cooldown_until_at: null`):** Bug logic trong `FollowState._check_and_sync_cooldown_expiry()`: lệnh `if "cooldown_until_at" in self._data:` trả về `True` ngay cả khi giá trị là `null` (None trong Python). Khi đó `_parse_utc_iso(None)` trả về `None`, rơi vào nhánh `if until_dt is None: return True`, khiến máy bị kẹt cooldown vĩnh viễn dù nick không hề dính án phạt.
2. **Quy trình đối soát chuẩn xác giải trình cho Operator:**
   - **Đối soát tính chuẩn xác:** Xem dòng `Đối soát TikTok Web (+N Following thật - Khớp 100% so với script báo)`. Nếu các máy thành công (như M5, M17, M21) khớp 100% với Web cào $\rightarrow$ khẳng định script đếm thật, Web cào thật, không báo ảo.
   - **Bóc tách các nhóm từ artifacts:** Quét nhanh `follow_result.json` của phiên gom theo `(status, reason, follow_failed, count)` để phân định chính xác số lượng máy Live Anchor Drop vs Cooldown Skip ca trước vs State Parser Trap.
   - **CẢNH BÁO BẪY DIỄN GIẢI `ip_risk_audit.py` (CẤM ĐỔ THỪA BAN IP BỪA BÃI):**
     * `ip_risk_audit.py` chỉ là script thống kê cơ học dựa trên `internal_follows == 0` trong `daily_account_actions`.
     * Nếu ca trước đó (ví dụ Ca 1 sáng) bị lỗi máy / lỗi runner (crash, fail hàng loạt không chạy đến bước follow) thì `internal_follows` cũng bằng 0. Script audit sẽ tự động đếm đó là "immediate drops" và dán nhãn proxy là `[CRITICAL]`.
     * **CẤM TUYỆT ĐỐI** Coordinator nhìn vào nhãn `[CRITICAL]` của script audit để phán bừa "TikTok ban hàng loạt IP" khi máy còn chưa thực sự chạy follow! Bắt buộc kiểm tra `run_manifest.json` và log ca trước xem máy có chạy thật hay bị lỗi hạ tầng.

## Concurrent Multi-Session Workspace Hazard (Anti-Blind Checkout)
- Khi user gửi lệnh đồng loạt trên nhiều session/tab chat khác nhau, các agent chạy ngầm (đặc biệt là model worker như Luna) có xu hướng quét thấy file dirty thì chạy `git checkout -- <files>` bừa bãi để dọn dẹp, gây xóa mất mã nguồn vừa vá.
- **Quy tắc bảo vệ mã nguồn:** Ngay khi patch của Worker hoặc Coordinator chạy qua focused tests (`pass 100%`) và xác nhận diff chuẩn O(1), BẮT BUỘC tạo commit git cục bộ ngay (`git commit -m "..."`).
- TUYỆT ĐỐI KHÔNG để uncommitted changes treo lơ lửng qua nhiều lượt hội thoại khi đang có nhiều session cùng trỏ vào một workspace vật lý.

## Review procedure
1. Trace every `set_follow_failed()` caller and classify its evidence contract.
2. Check whether a reload return value is ignored or whether a loop `break` falls through to failure mutation.
3. Check whether OCR/classification can run on a wrong screen before identity verification.
4. Check whether `follow_tap_done` is actually read before post-tap waiting/reload.
5. Verify the active-cooldown guard precedes legacy migration, graduation, ceiling, timestamp, and `_save()` operations.
6. Verify no account state mutation imports or invokes IP-breaker code.
7. Add focused mocked regressions for each false-positive path; do not run the full farm suite during debugging.
8. For report discrepancies, compare the machine-scoped result artifact with the watchdog classifier input. Do not rely on the human-facing summary alone.

## Regression matrix
- State: second `set_follow_failed()` while cooldown active leaves state file bytes unchanged.
- State: graduated and non-graduated failures never invoke `trip_ip_breaker`.
- Verify: reload returns false -> `VerifyResult("manual")`, zero failure callbacks.
- Mode 2: missing Follow tap or unbound identity -> manual outcome, zero failure callbacks.
- Mode 2: identity-bound fresh `not_followed` -> the only path that may produce `FOLLOW_FAILED`.
- Reporting: `FOLLOW_FAILED` with `followed_count=3` is rendered as tail-drop/account-ceiling with 3 accepted follows, not as `success=0` or zero-follow jail.
- Reporting: `FOLLOW_FAILED` with `followed_count=0` remains eligible for zero-follow streak accounting, subject to the configured streak threshold.

## Evidence/reporting
Separate `tap_attempted`, `runner_verified`, and later web/snapshot reconciliation. Never infer a dead external priority target from HTTP 200 or an anti-bot placeholder. If the account is absent from the tracking DB, report that as “not present in tracker”; do not delete or disable the configured target without direct profile evidence and user authorization.

## Operator handoff discipline (Anti-hedging)
- Khi code và focused tests đã pass (ví dụ 357/357 passed), CẤM kết thúc bằng tràng phân trần rào đón ("chưa chạy canary vì máy ngủ, chưa dám báo DONE, chưa commit...") khiến Operator thấy do dự, đứng im than khóc ("Là h sao cứ dừng lại khóc thế").
- Cấu trúc bàn giao dứt khoát 3 phần:
  1. **Khẳng định kết quả:** Liệt kê các điểm lỗi đã bẻ lại và số test focused pass.
  2. **Hiện trạng môi trường ngắn gọn:** Nêu sự thật khách quan (ví dụ: máy đang sleep, không chạy mù).
  3. **Hành động tiếp theo rõ ràng:** Đưa ra lựa chọn dứt khoát: (a) commit git đợt fix, hay (b) chạy closeout gate cho Sol chấm điểm để chốt phiên.

## Git line-ending hygiene in follow repo
- Repo `tiktok-follow` có file dùng LF và file dùng CRLF ở HEAD (ví dụ `test_follow_state.py` ở HEAD là CRLF 100%, trong khi các flow modules là LF).
- Chuyển sai line ending sẽ làm `git diff --numstat` nhảy thành toàn bộ file hoặc `git diff --check` báo lỗi trailing whitespace trên hàng nghìn dòng.
- BẮT BUỘC kiểm tra format của HEAD trước khi lưu hoặc convert:
  `git show HEAD:<file> | python -c "import sys; b=sys.stdin.buffer.read(); print(b.count(b'\r\n'), b.count(b'\n'))"`
- File đang dùng CRLF ở HEAD thì giữ đúng CRLF; file dùng LF thì giữ đúng LF.
