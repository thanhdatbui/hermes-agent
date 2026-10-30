# Unified Pipeline Architecture: Gate A-B-C, Gate 6 Canary Evidence, & Closeout Gate Decoupling

## 1. Context & Operational Problem
Khi triển khai quy trình sửa code và vận hành trên farm, thường nảy sinh 2 hiểu lầm hoặc lỗ hổng:
1. **Lầm tưởng Gate A-B-C thay thế nghiệm thu:** Coordinator nghĩ rằng sau khi qua Gate A-B-C (sửa code và pass unit test offline) thì đã xong việc và muốn chốt phiên ngay.
2. **Quy trình rời rạc trên giấy (Fragmented Tooling):** Gate B (`gate_b_planner.py`), Gate C (`dispatch_worker.py`), Canary (`canary_runner.py`), và Closeout (`closeout_gate.py`) là các script riêng rẽ. Nếu Coordinator đãng trí hoặc lười, nó có thể bỏ qua bước chạy Canary máy thật và báo cáo mồm.

## 2. Decoupled Lifecycle: Tách bạch rõ 3 giai đoạn

```text
[User Task / Bug Alert]
         ↓
[GIAI ĐOẠN 1: BẾP NÚC (GATE A-B-C)]
  - Gate A: Thu thập log, diff, lỗi, target file.
  - Gate B (Planner): Gemini Web (timeout 120s) -> Claude CLI (150s) -> Sol Worker (120s).
    Xuất Contract O(1): target_file, old_string (duy nhất, LF normalized), new_string.
    Log telemetry vào D:/Taadaa/logs/gate_b_audit.jsonl.
  - Gate C (Worker): Qoder T0 (DeepSeek-Flash) -> Sol T1 -> Agy T2 -> Haiku T3.
    Hậu kiểm độc lập: applied() verify trực tiếp trên file, không tin receipt.
         ↓
[GIAI ĐOẠN 2: THỰC ĐỊA & NGHIỆM THU (GATE 6 / CANARY)]
  - BẮT BUỘC Canary trên 1 thiết bị thật qua `canary_runner.py`.
  - Gate 6 Invariant: Soi mắt bằng vision, đính kèm `MEDIA:<screencap_path>` về Telegram.
  - Coordinator DỪNG LẠI CHỜ USER KIỂM DUYỆT. Tuyệt đối không tự đóng phiên.
         ↓
[User xem ảnh thực tế và gõ lệnh: "Done" / "chốt phiên"]
         ↓
[GIAI ĐOẠN 3: THẨM ĐỊNH TỐI CAO (CLOSEOUT GATE)]
  - Kích hoạt `closeout_gate.py --repo <repo> --base HEAD~1 --json-output`.
  - Reviewer độc lập (Sol / Claude) chấm điểm >= 85/100 (APPROVED).
  - Push code an toàn lên origin. Kết thúc phiên làm việc.
```

## 3. Telemetry & Timeout Governance
- **Gate B Audit Log:** `D:/Taadaa/logs/gate_b_audit.jsonl`
  Ghi nhận: `ts`, `planner`, `status` (SUCCESS/TIMEOUT/FAILED), `latency_s`, `reason`, `target_files`.
- **Worker Audit Log:** `D:/Taadaa/logs/dispatch.jsonl`
  Ghi nhận phân loại lỗi: `TIMEOUT`, `NO_DIFF`, `QUOTA`, `ENV`, `TASK_FAIL`.
- Khi latency vượt ngưỡng hoặc xuất hiện chuỗi timeout, audit log này là nguồn bằng chứng để bảo trì pool account (refresh cookie `__Secure-1PSID`, xoay proxy hoặc đổi tier) thay vì phỏng đoán mò mẫm.
