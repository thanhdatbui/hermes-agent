# Tiếp quản phiên bị gián đoạn

## Mục tiêu
Khôi phục đúng checkpoint của một phiên dừng vì context window, API/provider hoặc app restart mà không lặp lại action live đã thành công.

## Checklist checkpoint

- Session ID và title chính xác.
- Yêu cầu gốc và scope live đã được user cho phép.
- Target/machine/serial cuối cùng.
- Action live cuối và tool output xác nhận exit.
- Process nền/reviewer cuối: running, exited, quota, hay không còn trong registry mới.
- Diff/worktree hiện tại và thay đổi chưa review.
- Test đã pass/fail/hang; artifact chẩn đoán.
- Completion gate còn thiếu: recovery proof, test, reviewer `APPROVED`, commit/push hay báo cáo.

## Quy trình

1. Dùng session history đọc bookend và cửa sổ quanh message cuối có tool call.
2. Nếu output quá lớn, cuộn vào vùng cuối thay vì đọc toàn transcript.
3. Re-check state dễ thay đổi bằng probe read-only/live-safe phù hợp: device online, VPN interface và connectivity, central locks, process tree, git status.
4. Nếu proof hiện tại đã đạt, đánh dấu phần đó hoàn tất; không reboot/retry/rerun batch.
5. Nếu coding agent báo đã sửa, chạy lại test trọng tâm và `git diff --check` độc lập.
6. Tiếp tục reviewer từ toàn bộ diff hiện tại, không chỉ patch cuối.
7. Với reviewer quota nhưng process không exit: kill, smoke-test fallback, review lại; không chờ reset.

## Ví dụ failure signature bền vững

### Unit test lock bị treo sau khi thêm proxy-readiness preflight

Triệu chứng: test dùng serial giả tạo `DeviceLock.acquire()` và chờ khoảng timeout readiness mặc định; full suite có vẻ treo, test nghiệp vụ khác chạy riêng vẫn pass.

Chẩn đoán:
- Chạy từng test trong subprocess với timeout ngoài process để tìm test cụ thể.
- Kiểm tra fixture có đang vô tình gọi preflight production không.

Fix cho test thuần lock:
- Truyền `bypass_proxy_readiness=True` vào fixture lock khi test chỉ kiểm tra reservation/promotion/takeover và không kiểm tra VPN.
- Không đổi default production và không mock bỏ toàn bộ central lock policy.
- Chạy lại từng test từng treo, full file, suite consumer và `git diff --check`.

## Cách báo trạng thái

- `Xong` chỉ khi mọi gate yêu cầu đều đạt.
- `Chưa — còn reviewer APPROVED; code/test đã pass.` là đủ khi user hỏi ngắn.
- Không dùng tiến độ dài thay cho câu trả lời nhị phân.
