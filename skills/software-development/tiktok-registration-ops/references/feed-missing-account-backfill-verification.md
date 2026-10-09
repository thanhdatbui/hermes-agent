# Feed thiếu tài khoản → xác minh Reg bù

## Mục tiêu
Phân biệt Reg TikTok chạy theo chuỗi/lịch trước Feed với Reg bù được trigger trực tiếp bởi danh sách máy thiếu acc trong phiên Feed.

## Quy trình evidence
1. Đọc `run_manifest.json` của đúng run, đúng row, đúng cluster; lấy `multi_machine_summary` và danh sách `empty_machines` từ các item có reason chứa `account row ... empty (no username)`.
2. Tìm cầu nối từ danh sách đó tới canonical registration launcher: target machine list, command/dispatch record, start/end, exit code, log và artifact kết quả.
3. Kiểm tra `Total targets: 0` riêng: đây là “không có target”, không đồng nghĩa hook bị bỏ qua.
4. Đối soát cả lịch sử artifact/output và process hiện tại. Process không còn chạy chỉ chứng minh hiện tại đã rảnh, không chứng minh chưa từng chạy.
5. Nếu chỉ có `empty_machines` nhưng không có dispatch record, kết luận `UNPROVEN/BLOCKED`, không kết luận chắc “chưa kích hoạt”.

## Quy tắc báo cáo
- Ghi riêng: `pre-feed/night-chain Reg` và `feed-triggered backfill Reg`.
- Nêu cluster, row, session/run, số máy, target list, log/artifact path, exit code.
- Không biến phần parser `empty_machines` thành bằng chứng hook Reg bù đã tồn tại; cần thấy call/dispatch thực tế.
