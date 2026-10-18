# Bản Thống Nhất Cơ Giới Hóa 3 Bên: G1, G2, Canary Entrypoint & G3 Output Filter (2026-10-18)

Đồng thuận tuyệt đối giữa **Claude Sonnet 5.5 (Kiến trúc sư)**, **Advisor Sol (Chiến lược Farm)** và **Hermes Coordinator (Hiện trường)** nhằm triệt tiêu vĩnh viễn 3 sai phạm kinh niên:
1. Tự ý dùng `delegate_task` sửa code thay vì Single Dispatch Gateway.
2. Chỉ đạo Worker viết script probe ad-hoc trên điện thoại farm.
3. Rơi vào tê liệt, khóc lóc đùn việc cho Operator khi bị Guard chặn.

---

## 1. Gate 1 (G1): Khóa Cứng Quyền Sửa Code (delegate_task Read-Only)
- **PreToolUse Enforcement:** `delegate_task` chỉ được cấp toolset Read-Only (đọc log, thám nghiệm hiện trường, phân tích dữ liệu, research) với ngân sách giới hạn (<= 8 calls). CẤM TUYỆT ĐỐI giao subagent `delegate_task` nhiệm vụ sửa code, patch file hoặc commit.
- **Single Dispatch Gateway (Lối đi duy nhất):** 100% thao tác sửa code, refactor, viết focused test O(1) bắt buộc phải dispatch qua:
  `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> "<contract O(1)>"` (Haiku 5.5 / Agy CLI) với `WORKER_TOKEN`.
- **Van An Toàn `WORKER_CLI_EXHAUSTED` (Kẹp Chì Bảo Mật):**
  * Gateway tự động quan sát tín hiệu cạn worker (khi cả Haiku lẫn Agy CLI đều cạn quota sạch sẽ). Coordinator tuyệt đối không được tự bịa cờ này.
  * Gateway cấp token HMAC dùng 1 lần (Single-use Nonce), TTL ngắn (10–15 phút), ràng buộc chặt chẽ với `scope_hash` của đúng task đó.
  * Khi mở van, `delegate_task` chỉ được cấp quyền ghi đúng file trong scope, tuyệt đối không cấp quyền can thiệp thiết bị hay chạy ADB.

---

## 2. Gate 2 (G2): Cấm Probe Ad-hoc & Bảo Vệ Hạ Tầng Farm 24/7
- **Bác bỏ hoàn toàn đề xuất shim binary `adb.exe` trên Windows OS:**
  * Việc can thiệp vào binary `adb.exe` toàn cục Windows sẽ đánh sập hàng chục cronjob/watchdog tự động 24/7 của Farm (`healing_selector`, `reboot`, `post_noon_chain_watchdog`...).
  * Cả Claude Sonnet 5.5 và Advisor Sol đều thống nhất không đụng vào binary hệ điều hành.
- **Chốt cơ chế chặn:**
  * Chặn ở tầng **PreToolUse Hook của Hermes** trong phiên làm việc của Agent: chặn tạo file `.py` rác chứa lệnh can thiệp thiết bị (`input tap`, `input swipe`, `adb`), chặn lệnh gõ ADB ngoài luồng trong chat.
  * Phân biệt rõ phiên Agent với tiến trình cron ngầm qua biến môi trường để không chặn nhầm hệ thống tự động.

---

## 3. Gỡ Deadlock Canary: Unified Canary Entrypoint & Sealed Receipt
- **Bản chất lỗi:** `done_gate.py` bắt buộc chạy Canary trên máy thật mới cho chốt phiên, nhưng `guard_terminal.py` lại chặn lệnh runner, tạo ra thế kẹt *"cửa chính khóa, cửa phụ chặn"* ép Agent lách luật.
- **Entrypoint Duy Nhất:** Đóng gói `python D:/Taadaa/tools/canary_runner.py` theo State Machine chuẩn: `RESOLVE -> PREFLIGHT -> RUN -> CAPTURE -> OCR_VERIFY -> RECEIPT`.
- **Phân định phạm vi nghiêm ngặt:**
  * `--machine <N>`: Dành cho hotfix cục bộ 1 máy hiện trường.
  * `--machines <N1,N2,N3...>`: Dành cho thay đổi diện rộng (bắt buộc $\ge 3$ máy; nếu $< 3$ máy thì runner từ chối ngay).
  * `done_gate.py` đối chiếu scope: hotfix chấp nhận `single`, thay đổi diện rộng bắt buộc `wide`. Chống chiêu trò lấy kết quả 1 máy để pass gate diện rộng.
- **Canary Sealed Receipt JSON (Xóa bỏ cờ trơn):**
  * Xóa bỏ hoàn toàn cờ `.canary_passed` rỗng/trơn.
  * Bắt buộc kiểm tra Receipt JSON gồm: `commit_sha`, `media_path` (file ảnh thật, mtime sau commit), `media_sha256` (khớp hash ảnh thật), `ocr_snippet`, và `runner_status: success`.

---

## 4. Gate 3 (G3): Output Filter Chống Đùn Việc & Chống Báo Blocked Lười
- **Chặn đùn việc Operator:** Hook kiểm duyệt output cuối cùng, chặn đứng mọi phản hồi chứa mẫu câu *"nhờ anh gõ giúp"*, *"xin thêm allowlist"* khi bị Deny.
- **Mọi `DENY` bắt buộc kèm `NEXT_ACTION`:** Máy tự chạy tiếp được theo playbook định sẵn.
- **Chống biến `BLOCKED` thành lối thoát lười:** Coordinator CHỈ ĐƯỢC báo `BLOCKED` khi thỏa mãn đủ 3 điều kiện:
  1. Có mã lỗi chuẩn từ enum cố định (ví dụ: `DEVICE_OFFLINE`, `HARDWARE_DISCONNECT`).
  2. Bắt buộc có file bằng chứng thực tế trên đĩa (log/ảnh) mà hook kiểm tra được.
  3. `NEXT_ACTION` đã được thử tự động và thất bại.

---

## 5. Kỷ Luật Bằng Chứng Thị Giác Canary (In-Stream vs Home Screencap Veto)
- **Cấm Fallback Screencap Sau Khi Thoát App:** Bằng chứng Canary BẮT BUỘC phải do chính runner chụp trong lúc app đang chạy tại đúng màn hình đích (`--canary-screencap`). CẤM TUYỆT ĐỐI chụp fallback sau khi app đã thoát hoặc crash về Launcher.
- **Mechanical Launcher Token Veto:** Quét WinRT OCR trên ảnh trước khi cấp receipt. Nếu phát hiện $\ge 2$ token hệ thống (*"cửa hàng play", "photos", "tin nhắn", "xóa bộ nhớ đệm", "danh bạ", "điện thoại", "launcher", "home screen"*):
  * **VETO NGAY LẬP TỨC**.
  * Đánh dấu `CANARY_REJECTED`, hủy bỏ receipt, cấm xuất bản thẻ `MEDIA:`.
