# Closed-Loop Auto-Repair Architecture, Emitter Coalescing & Canary Gate 4 Adapter

> Kinh nghiệm thiết kế và thi công hệ thống tự sửa code khép kín (Autonomous Script Auto-Repair) cho Taadaa Phone Farm (tháng 10/2026).

## 1. Kiến trúc 6 Cổng Điều Phối (IncidentAutoHarness)
Thay vì để LLM tự do sửa code hoặc sửa trong luồng chính của session, Auto-Repair chạy trong tiến trình headless độc lập qua 6 cổng cơ học bất biến:
- **Cổng 0 (Telemetry Completeness):** Bắt buộc có cả cây UI XML và ảnh chụp màn hình PNG (> 0 bytes) kèm OCR text. Thiếu bằng chứng -> `BLOCKED_PENDING_TELEMETRY`, cấm sửa mò.
- **Cổng 1 (Mechanical Planner):** Tier 1 là Claude Sonnet CLI (`dispatch_planner.py`), Tier 2 dự phòng là Sol Planner (:20129) khi quota >= 85%. Bắt buộc anchor duy nhất (`grep -c == 1`), contract `old_string -> new_string`, test command < 30s.
- **Cổng 2 (Surgery Worker):** Thi công bản vá O(1) qua `dispatch_worker.py`, ngân sách cứng <= 2 files, <= 30 dòng diff (`git diff --numstat`). Vượt quá -> revert ngay.
- **Cổng 3 (Protected Regression Gate):** Kiểm tra các hằng số bảo vệ phần cứng và tài khoản qua `guardgate/runner.py` (Case 162 timeout micro-drop >= 20s, Case 161 follow ceiling <= 0, CREATE_NO_WINDOW flags).
- **Cổng 4 (Canary Gate):** Tự động kích hoạt `canary_runner.py` trên 1 máy thật/test, xuất `canary_evidence.json` kèm ảnh nghiệm thu thực tế.
- **Cổng 5 (Closeout Gate):** Reviewer Sol (:20129) chấm điểm độc lập qua `closeout_gate.py` (ngưỡng >= 85/100, grace band >= 80).

## 2. Dây Kích Nổ (Incident Emitter) & Thu Thập Telemetry < 2.5s
- **Phân loại Heuristic Lỗi Phần cứng vs Lỗi Code:**
  - Lỗi Phần cứng / ADB / USB: Return code lệnh ADB != 0 hoặc chứa chuỗi `('device offline', 'device not found', 'no devices', 'protocol fault', 'connection refused')` -> Không gửi LLM sửa code, ghi nhận lỗi runtime hạ tầng.
  - Lỗi Script / UI Drift: Lệnh ADB trước đó returncode == 0 (máy sống, phản hồi bình thường) nhưng Python crash (`NoSuchElement`, `KeyError`, vỡ selector) -> 100% là lỗi code/UI -> Kích hoạt Emitter.
- **Thu thập Telemetry song song:**
  - Bắn đồng thời 2 tiến trình: `p_cap = adb exec-out screencap -p` và `p_xml = adb shell uiautomator dump` với timeout cứng 2.5s.
  - Bắt buộc kiểm tra returncode của cả 2 tiến trình (`rc_cap == 0` và `rc_xml == 0`) trước khi pull XML về máy tính.
  - Khi timeout: BẮT BUỘC gọi `p.kill()` VÀ `p.wait()` để reap process, chống để lại zombie subprocess trên Windows.
- **Tích hợp WinRT OCR:**
  - Gọi `winrt_ocr_util.winrt_ocr(png_path)` để trích xuất text tiếng Việt/Anh trực tiếp từ ảnh chụp màn hình, nạp vào `telemetry.extra['ocr_text']` giúp Planner hiểu ngữ cảnh màn hình mà không cần tốn token vision.

## 3. Cơ Chế Chống Bão Sự Cố (Anti-Storm Coalescing)
- **Vấn đề:** Khi TikTok đổi giao diện hoặc bật popup mới, cả cụm 15-80 máy trong ca cùng nổ lỗi giống hệt nhau. Nếu bắn 15-80 tickets sẽ làm tràn queue và xung đột khóa NTFS `IncidentLock`.
- **Giải pháp Marker Atomic:**
  - Tính `error_signature = sha256(error_type + target_file + normalized_stack)[:16]`.
  - Dùng cờ `os.O_CREAT | os.O_EXCL` tạo file marker `pending/SIG_{signature}.marker`.
  - Máy đầu tiên: Tạo marker thành công -> Lưu vé sự cố chính thức vào `pending/<incident_id>.json`.
  - Các máy sau (cùng signature trong cửa sổ 20 phút của ca): Bị `FileExistsError` -> Không tạo vé mới, chỉ ghi số máy vào `pending/<incident_id>.affected.jsonl`.
  - Xử lý Marker hết hạn (> 1200s): Ghi đè nguyên tử bằng file tạm `.tmp.<pid>` và `os.replace` để triệt tiêu hoàn toàn race condition giữa các tiến trình.

## 4. Adapter Cổng 4 (Canary Gate) & Bẫy Stale Receipt
- **Lệch Schema giữa Canary Runner và Harness:**
  - `canary_runner.py` xuất ra file dùng chung toàn farm: `D:/Taadaa/.canary_receipt.json` với trường `runner_status` và `media_path`.
  - `IncidentAutoHarness` cần file per-incident `canary_evidence.json` với trường `final_status` và `media`.
- **Bẫy Stale Receipt:**
  - Nếu chỉ kiểm tra `receipt_file.is_file()`, Harness có thể nhặt nhầm receipt của một ca chạy từ nhiều giờ trước.
  - Bắt buộc ghi lại mốc thời gian bắt đầu `t_start = time.time()` trước khi gọi runner.
  - Kiểm tra `receipt_file.stat().st_mtime >= (t_start - 2.0)` và xác thực schema `runner_status in ('success', 'failed')` kèm file media tồn tại thật.
  - CẤM gọi `receipt_file.unlink()` vì đây là file dùng chung của toàn farm, xóa nó sẽ làm đứt luồng của các tiến trình giám sát khác.
