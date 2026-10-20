# Cross-Repo Capability Discovery & Mechanical Reuse Discipline (20/10/2026)

## 1. Bối cảnh & Sự Cố Thực Địa (Wheel Reinvention & Single-Repo Blindness)

### A. Sự Cố Kẹt Vòng Lặp Do Tự Viết Lại Bánh Xe
- **Hiện tượng:** Trong task cuốn chiếu đổi tên TikTok (`do_rename_canonical_runner.py`), Coordinator tự code lại cơ chế Switcher bằng OCR (`ocr_boxes` -> dò text -> tap tọa độ).
- **Hậu quả:** Trên Máy 2 (`@maixinh075`), nick mục tiêu đã active sẵn trên Profile. Khay Switcher mở ra hiện nick ở dòng 1; script tap vào dòng 1 khiến TikTok không đổi trạng thái; script lại thấy dòng 1 và tap tiếp. Hệ quả là kẹt vòng lặp giữa `PROFILE` và `SWITCHER` suốt 35 lần liên tiếp trước khi văng `exit_2`.
- **Nguyên nhân:** Bỏ qua các module sẵn có đã được tôi luyện thực địa (`automation_core.tiktok.account_switcher`, `account_switcher_bridge.py`, `_core_switcher`).

### B. Bẫy Thiển Cận "Chỉ Ép Automation-Core" (Single-Repo Blindness)
- Khi bị nhắc nhở, Coordinator có xu hướng co cụm, chỉ nghĩ đến duy nhất `automation-core`.
- **Chỉ đạo chấn chỉnh của Operator (20/10/2026):**
  > *"Tại sao lại ép automation core, lỡ script đó ở repo khác thì sao? Tao bảo là phải kiểm tra all hàm all script có logic tương tự trước khi định xây một cái gì đó."*
- Hệ sinh thái Farm gồm **8 repo độc lập**, logic đã được giải quyết nằm rải rác:
  1. `automation-core`: ADB client, ATX JSON-RPC 7912, Persistent UI, Startup, Core Switcher.
  2. `Tiktok_Reg`: Login chuẩn (`tiktok_login_v1.py`), 2FA TOTP bypass OTP mail, Graph API Hotmail, Switcher Bridge.
  3. `tiktok-follow`: Follow Engine, Profile Navigation Adapter.
  4. `tiktok-luot nuoi acc`: Nurture feed, dead-owner lock reaper, sync-safe workbook.
  5. `tiktok-add-bao-mat-f2a`: Batch 2FA runner, TOTP secret decoding.
  6. `GPM auto`: GPMLogin CDP browser automation, Gmail nurture, proxy lifecycle.
  7. `tools`: Hiện trường O(1) (`inspect_machine.py`), sinh tên tiếng Việt, dọn rác Recycle Bin.
  8. `Hermes`: Gateway, Watchdogs, Cronjobs, Healers.

### C. Bẫy Nhồi Nhét Prompt Khi Đã Có Cơ Giới Hóa (Prompt-Stuffing Anti-Pattern)
- **Chỉ đạo chấn chỉnh của Operator (20/10/2026):**
  > *"Đã có cơ giới hoá sao cứ nhồi nhét prompt chi mệt v. R gọi claude review chưa?"*
- Khi một quy tắc hay công cụ đã được code thành file Python và có unit test bảo vệ, **TUYỆT ĐỐI CẤM** nhồi nhét các đoạn văn directive dài dòng vào prompt hay Persistent Memory. Kỷ luật cơ học thắng mọi prompt mềm.

---

## 2. Giải Pháp Cơ Học: `find_existing_logic.py`

Thay vì dựa vào trí nhớ hay lời hứa của agent, hệ thống trang bị công cụ tra cứu AST cơ học trước khi thi công:

```bash
# Tra cứu logic có sẵn trên cả 8 repo farm (dưới 0.3s)
python D:/Taadaa/tools/find_existing_logic.py "<keywords>" --top 5 --receipt

# Xác minh receipt token trong gate / script
python D:/Taadaa/tools/find_existing_logic.py --verify <RECEIPT_TOKEN>
```

### Đặc tính kỹ thuật:
1. **AST Extraction:** Quét toàn bộ hàm (`def`), class (`class`), tham số, kiểu trả về và docstring từ hơn 1.000 file Python của 8 repo.
2. **Index Caching & TTL:** Lưu trữ cache `farm_logic_index.json` kèm `built_at`, tự động rebuild nếu cache cũ quá 24h hoặc chạy với `--reindex`.
3. **Atomic File Write:** Ghi cache qua file tạm `.tmp` rồi `os.replace` để chống xung đột race condition giữa các tiến trình.
4. **Secret Scrubbing:** Tự động che giấu các default argument nhạy cảm (`=...`) để không leak mật khẩu/token vào index hay stdout.
5. **Audit Receipt Ledger:** Mỗi lần search hợp lệ (có kết quả) sinh ra token `RECEIPT: ELR-...` và ghi vào sổ cái append-only `find_existing_logic_receipts.jsonl`.

---

## 3. Vòng Lặp Đối Kháng Với Claude Reviewer (Sonnet 5.5)

Theo kỷ luật *"Thi công đến khi Claude CLI duyệt"*, code mới bắt buộc phải qua Claude Reviewer (`claude_worker.py --role reviewer`):
- **Vòng 1 - REJECTED:** Reviewer phát hiện 6 lỗi fail-open nghiêm trọng:
  - *P0-1:* Repo vắng mặt (chưa mount) nhưng vẫn ghi cache rỗng và cấp receipt sai sự thật.
  - *P0-2:* Cache thiếu TTL và fingerprint khiến code mới không bao giờ được nhận diện.
  - *P1-3:* File lồng sâu ném `RecursionError` / `MemoryError` làm crash toàn bộ CLI.
  - *P1-4:* Cache sai schema làm sập công cụ.
  - *P1-5:* Receipt tự khai không có sổ cái đối soát.
  - *P2-6:* Lộ bí mật qua default argument unparse.
  - *P2-8:* Ghi cache không atomic.
- **Kỷ luật khắc phục:** Không phân trần, áp dụng đúng danh sách findings vào code, bổ sung 30/30 unit tests hồi quy (`test_find_existing_logic.py`) và nộp lại cho đến khi `VERDICT: APPROVED`.
