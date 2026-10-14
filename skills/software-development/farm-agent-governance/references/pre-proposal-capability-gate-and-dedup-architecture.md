# Pre-Proposal Capability Gate & De-duplication Architecture (`capability_gate.py`)

## 1. Bối cảnh & Căn nguyên sự cố
- **Bệnh lý "Hứng lên là đẻ file mới":** Khi tiếp nhận ý tưởng mới (từ video Laurin Tran / Cursor hoặc tài liệu bên ngoài), Coordinator thường bị phấn khích thái quá, lập tức đề xuất và code ngay script mới (`benny_farm_triage.py`) mà không kiểm tra xem hệ thống đã có những gì.
- **Hiện trường thực tế:** Hệ thống Taadaa Phone Farm đã có sẵn 90% công năng trong `inspect_machine.py`, `recover_stuck_s7.py` và cron `farm_idle_screen_and_app_healer.py`.
- **Hậu quả:** Gây over-engineering, rác repository, phân mảnh logic và đặc biệt nguy hiểm: xung đột `device_lock`, xung đột SQLite database và deadlock giữa 50 cronjob ngầm đang chạy song song.

## 2. Kiến trúc 2 tầng: Registry & De-duplication Pipeline
Được Claude Code CLI (v2.1.281) thiết kế và thẩm định APPROVED (28/28 unit tests pass):

```
 Ý tưởng mới (User yêu cầu / Video / Alert)
        │
        ▼
 [S0] Proposal Card (JSON: goal, intents, would_touch, new_files)
        │
        ▼
 [S1] Deterministic Filter (O(1) Python — BM25 + Resource Collision)
        │  • Quét index.json (341 capabilities từ tools/ và automation-core/src)
        │  • Phát hiện va chạm tài nguyên: device_lock, sqlite, adb, cron
        ▼
 [S2] Semantic / Architectural Audit (LLM / 9Router / claude-sonnet-4-6)
        │  • Đối soát 3 câu hỏi: Trùng mục tiêu? Trùng pipeline? Có phá hỏng ca nuôi?
        ▼
 [V] Hard Validator (Ép luật cứng lên kết quả LLM)
        │
        ├─ REUSE  ──► Trả về exact script có sẵn + lệnh chạy. CẤM tạo file.
        ├─ EXTEND ──► Chỉ định file canonical cần sửa + flag mới (diff <= 30 dòng).
        └─ NEW    ──► Chỉ cấp khi chứng minh được delta_proof thật → Cấp RECEIPT.
```

## 3. Physical Write Guard (`capability_gate.py guard <file_path>`)
- **Chặn vật lý tại cửa ngõ:**
  - File đã tồn tại trên đĩa: Cho phép chỉnh sửa (Exit 0).
  - File tạo mới: Kiểm tra xem có file `runtime/capabilities/receipts/<hash>.json` còn hạn (khớp sha1 fingerprint hiện tại của registry) cấp phép cho file này hay không.
  - **Không có receipt:** Trả về **Exit code 2: `NO_RECEIPT`** và chặn đứng hành động tạo file!

## 4. Kỷ luật bắt buộc cho Coordinator
- Trước khi đề xuất tạo tool / script mới, Coordinator BẮT BUỘC chạy:
  ```bash
  python D:/Taadaa/tools/capability_gate.py propose <proposal.json>
  ```
- Nếu Gate trả về `REUSE` hoặc `EXTEND`, Coordinator TUYỆT ĐỐI CẤM tạo file mới, bắt buộc tái sử dụng hoặc mở rộng script canonical.
