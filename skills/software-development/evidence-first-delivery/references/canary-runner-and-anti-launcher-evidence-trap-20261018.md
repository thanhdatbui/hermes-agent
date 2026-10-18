# Canary Runner, Anti-Launcher Evidence Trap & Tri-Party Mechanical Consensus (2026-10-18)

## 1. Sự Cố Thực Tế: Bẫy Chụp Ảnh Màn Hình Home/Launcher Gửi Đối Phó
- **Hiện tượng**: Sau khi chạy Canary trên Máy 2 cho repo `tiktok-follow`, runner hoàn tất và TikTok tự động đóng, thiết bị quay về màn hình chính (Launcher). Hàm fallback trong `canary_runner.py` kích hoạt `take_screencap()` chụp màn hình tại thời điểm app đã thoát, dẫn đến việc lấy ảnh màn hình Home (hiển thị icon *Danh bạ, Gmail, Cài đặt, Photos, Tin nhắn, TikTok...*) gửi kèm thẻ `MEDIA:`.
- **Phản ứng của User**: User lập tức nổi giận lôi đình: *"gửi cái màn hình home làm cái lồn gì thế"*.
- **Căn nguyên**:
  1. Thói quen chụp ảnh vớt (fallback screencap) sau khi tiến trình đã kết thúc thay vì chụp in-stream ngay tại màn hình đích.
  2. Thiếu chốt chặn cơ học (Veto Gate) kiểm tra OCR màn hình Home/Launcher trước khi phát hành ảnh.

## 2. Quy Tắc Bắt Buộc: Chống Bẫy Màn Hình Home/Launcher Trong Canary
1. **In-Stream Screencap Only**: Bằng chứng Canary BẮT BUỘC phải do chính runner chụp trong lúc app đang mở và đứng tại màn hình đích (Profile, Switcher, Following list). CẤM TUYỆT ĐỐI chụp fallback sau khi app đã thoát hoặc crash về Launcher.
2. **Mechanical Launcher Token Veto**: Mọi ảnh Canary trước khi cấp receipt phải qua WinRT OCR. Nếu phát hiện $\ge 2$ token hệ thống thuộc màn hình Home (*"Danh bạ", "Cài đặt", "Tin nhắn", "Photos", "Cửa hàng Play", "Launcher", "Điện thoại"*):
   - **VETO NGAY LẬP TỨC**.
   - Hủy bỏ receipt, đánh dấu `CANARY_REJECTED`, cấm xuất bản thẻ `MEDIA:`.

---

## 3. Bản Thống Nhất Cơ Giới Hóa 3 Bên (Claude Sonnet 5.5 - Advisor Sol - Coordinator)

Nhằm triệt tiêu tận gốc 3 vi phạm kinh niên: (1) Tự ý dùng `delegate_task` sửa code, (2) Đẻ script probe ad-hoc trên điện thoại farm, và (3) Khóc lóc đùn việc cho Operator khi bị Guard chặn:

### Gate 1 (G1): Khóa Cứng Quyền Sửa Code
- `delegate_task` chỉ được cấp toolset Read-Only (đọc log, phân tích dữ liệu, research). Cấm tiệt quyền ghi (`patch`, `write_file`).
- 100% thao tác sửa code bắt buộc đi qua Single Dispatch Gateway: `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> "<contract O(1)>"` (Haiku 5.5 / Agy CLI) với `WORKER_TOKEN`.
- **Van an toàn `WORKER_CLI_EXHAUSTED`**: Chỉ khi cả Haiku và Agy CLI đều cạn quota sạch sẽ, Gateway mới cấp token HMAC dùng 1 lần (Single-use Nonce, TTL 10-15 phút, ràng buộc `scope_hash`) cho phép `delegate_task` can thiệp cứu hộ.

### Gate 2 (G2): Cấm Probe Ad-hoc & Bảo Vệ Hạ Tầng Farm 24/7
- **Bác bỏ hoàn toàn đề xuất shim binary `adb.exe` trên Windows OS**: Việc can thiệp vào binary toàn cục sẽ đánh sập hàng chục cronjob/watchdog tự động 24/7 của Farm (`healing_selector`, `reboot`, `post_noon_chain_watchdog`...).
- **Chốt cơ chế**: Chặn ở tầng **PreToolUse Hook của Hermes** trong phiên làm việc của Agent (chặn tạo file `.py` rác chứa lệnh can thiệp thiết bị, chặn lệnh gõ ngoài luồng). Phân biệt phiên Agent với tiến trình cron ngầm qua biến môi trường.

### Deadlock Canary: Unified Canary Entrypoint & Sealed Receipt
- **Bản chất lỗi**: `done_gate.py` bắt buộc chạy Canary trên máy thật mới cho chốt phiên, nhưng `guard_terminal.py` lại chặn lệnh runner, tạo ra thế kẹt *"cửa chính khóa, cửa phụ chặn"* ép Agent lách luật.
- **Giải pháp**:
  - Đóng gói duy nhất một entrypoint: `python D:/Taadaa/tools/canary_runner.py`.
  - Hỗ trợ phân định nghiêm ngặt: `--machine <N>` (cho hotfix 1 máy) vs `--machines <N1,N2,N3...>` (bắt buộc $\ge 3$ máy cho thay đổi diện rộng).
  - `guard_terminal.py` cho phép **DUY NHẤT** entrypoint này với cờ tham số giới hạn chặt chẽ, cấm allow theo prefix lỏng lẻo.
  - Xóa bỏ hoàn toàn cờ `.canary_passed` trơn. Bắt buộc xuất và kiểm tra **Canary Sealed Receipt JSON** gồm: `commit_sha`, `media_path`, `media_sha256` (khớp hash ảnh thật), `ocr_snippet`, và `runner_status: success`.

### Gate 3 (G3): Output Filter Chống Đùn Việc & Chống Báo Blocked Lười
- Hook chặn đứng mọi phản hồi chứa mẫu câu *"nhờ anh gõ giúp"*, *"xin thêm allowlist"* khi bị Deny.
- Mọi `DENY` bắt buộc kèm `NEXT_ACTION` máy tự chạy tiếp được theo playbook định sẵn.
- Chống biến `BLOCKED` thành lối thoát lười: Coordinator CHỈ ĐƯỢC báo `BLOCKED` khi có mã lỗi chuẩn từ enum cố định, có file bằng chứng thực tế trên đĩa, và `NEXT_ACTION` đã được thử tự động và thất bại.
