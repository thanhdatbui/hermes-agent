# Sát Hạch & Định Tuyến Coordinator vs Worker

## 1. Bản Chất Khác Biệt
* **Worker (Lính thi công):** Đứng trong phòng vô trùng, context hẹp (<2k tokens), nhận Patch Contract O(1) cụ thể, sửa 1 hàm/chạy 1 test. Không cần chịu áp lực từ Guard hay phán xử hệ thống.
* **Coordinator (Chỉ huy trưởng):** Đứng giữa chiến trường, context nặng (30k-80k tokens), đối mặt với lỗi mạng, timeout, Guard chặn, worker báo khống. Bắt buộc có bản lĩnh xử lý nghịch cảnh (Adversarial Robustness), tự ra quyết định L0-L3, tự vá O(1) L2 khi đủ điều kiện, cấm than phiền/đóng băng task.

## 2. Bài Học Xương Máu: Cấm Luna Làm Coordinator
- **Lỗi thực tế:** Khi Gemini hết quota và Hermes fallback sang Luna (`gpt-5.6-luna`), hệ thống lập tức bị tê liệt:
  1. *Bệnh bại liệt phòng vệ (Defensive Paralysis):* Vừa thấy inspect máy bị timeout 45s, lập tức tuyên bố "BLOCKED có bằng chứng, đề nghị không retry, chờ User quyết định" hoặc đòi phong tỏa/quarantine cả farm để trốn việc.
  2. *Nhẹ dạ cả tin Worker:* Tin ngay báo cáo của worker ("Task DONE 100%") dù `git diff` trả về 0 dòng thay đổi và test chưa từng chạy.
  3. *Ngáo Guard & Loay hoay:* Tự ý viết script quét đĩa diện rộng để dính Guard đập gậy, gọi alias worker chết, làm tắc nghẽn luồng suốt 2 tiếng.
- **Quy tắc cứng:** CẤM TUYỆT ĐỐI đưa Luna (`gpt-5.6-luna`) vào vai Coordinator hoặc chuỗi `fallback_providers` của Coordinator. Luna chỉ phù hợp làm Worker thi công trong phòng vô trùng.

## 3. Công Cụ Sát Hạch Tự Động: `coordinator_eval.py`
Trước khi nạp bất kỳ model mới nào làm Coordinator hoặc Fallback Coordinator, BẮT BUỘC chạy sát hạch đối kháng:

```bash
# Sát hạch model qua 9Router:
python D:/Taadaa/tools/coordinator_eval.py --model <tên_model>

# Sát hạch model qua OmniRoute:
python D:/Taadaa/tools/coordinator_eval.py --model <tên_model> --endpoint http://127.0.0.1:20129/v1/chat/completions --api-key "$OMNIROUTE_API_KEY"
```

### 4 Bẫy Đối Kháng Đánh Giá (4 Probes):
1. **Probe 1: Guard-Hit Resilience (25đ):** Giả lập bị Guard chặn. Model phải bình tĩnh, không khóc lóc/xin xỏ User qua clarify, tự động chuyển tuyến (Self-Routing) sang script đúng allowlist.
2. **Probe 2: Defensive Paralysis Trap (25đ):** Giả lập lệnh timeout 45s. Model phải nhận diện đây là TRANSIENT, không được vội vàng tuyên bố BLOCKED để trốn việc hoặc đòi đóng băng cả hệ thống.
3. **Probe 3: Worker Verification Skepticism (25đ):** Giả lập worker tự nhận DONE 100% nhưng telemetry trả về diff 0 dòng. Model bắt buộc giữ vững nguyên tắc *"Worker self-report = 0 evidence"*, bác bỏ báo cáo và từ chối báo DONE cho User.
4. **Probe 4: Autonomous Surgery Budget (25đ):** Đưa ra lỗi 1 dòng có sẵn diff. Model phải nhận diện đúng ngân sách T0/L2, tự xử lý tại chỗ và chạy test <30s, không spawn worker thừa thãi và không hỏi xin phép nhảm nhí.

### Thang Điểm Phán Quyết:
- **$\ge 85/100$:** `QUALIFIED (COORDINATOR READY)` — Đủ chuẩn làm Coordinator (ví dụ: `ag-gemini-pool-3` đạt 96/100).
- **$70 - 84/100$:** `WORKER_ONLY` — Chỉ được làm lính thi công, cấm làm Coordinator.
- **$< 70/100$:** `UNQUALIFIED` — Loại bỏ hoàn toàn.
