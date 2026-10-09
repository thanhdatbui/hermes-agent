# OmniRoute Pool Cleanup & Fallback Diagnosis

## 1. Triệu chứng rớt tầng giả (False Tier Failure)
Khi combo cấp cao (như `omni-worker`) bị lỗi hàng loạt hoặc timeout treo 30s liên tục:
- **Hiện tượng**: User báo combo "lỗi liên tục" hoặc "chậm/treo", nghi ngờ do tier đầu (Gemini).
- **Thực tế chẩn đoán**: Kiểm tra `api/usage/call-logs` (hoặc `api/usage/request-logs`) cho thấy:
  - Tier 1 (`ag-gemini-pool-3`): Vẫn trả lời 200 OK bình thường.
  - Tier 2 (`ag-claude`): Bị cạn quota hoặc upstream 429/403, dính `Semaphore timeout after 30000ms`. Request khi failover rớt sang Tier 2 sẽ bị giữ 30s rồi trả về lỗi, khiến toàn bộ worker cảm giác bị liệt.

## 2. Cơ chế Spillover (Tràn tầng) dù Tier 1 còn Acc và còn Quota
Tại sao `omni-worker` lại nhảy xuống `ag-claude` khi `ag-gemini-pool-3` còn hàng chục acc active đầy quota mà không hề được đụng tới?
Trong mã nguồn router (`open-sse/services/combo.ts`, `combo/targetResolution.ts`, `combo/sessionStickiness.ts`, `combo/targetExhaustion.ts`), có 4 thủ phạm cốt lõi:

1. **Thủ phạm số 1: Session Stickiness (Ghim phiên dồn tải vào 1-2 account)**:
   - Mặc định ở combo cha (`omni-worker`) hoặc combo con, hàm `applySessionStickiness()` hash nội dung message để ghim request vào **duy nhất 1 connectionId** đã từng thành công trong 15 phút.
   - Target được ghim luôn được đẩy lên **vị trí index 0** (`orderedTargets.unshift`), vô hiệu hóa việc xoay tua Round-Robin qua các account còn lại.
   - Khi connection đó nhận burst request hoặc subagents song song, nó chạm trần concurrency cap (2/2) hoặc dính lỗi tạm thời ➔ gây nghẽn semaphore 30s hoặc tràn tầng, trong khi 70 account còn lại trong pool hoàn toàn không được đụng tới!
   - **Cách fix**: Bắt buộc set `"disableSessionStickiness": true` trên cả combo cha và combo con trong `config`.

2. **Thủ phạm số 2: Nested Combo Mode mặc định làm phẳng (`nestedComboMode: "flatten"`)**:
   - Mặc định router gộp phẳng toàn bộ các targets của sub-combos (`ag-gemini-pool-3` + `omni-free` + `ag-claude`) thành một danh sách phẳng.
   - Khi strategy là `priority`, router duyệt tuần tự. Khi các account đầu của sub-combo 1 bị dính cooldown/concurrency cap, nếu không có barrier đóng, request tràn thẳng xuống các account của sub-combo tiếp theo.
   - **Cách fix**: Set `"nestedComboMode": "execute"` trên combo cha (`omni-worker`) để sub-combo được thực thi như một runtime unit độc lập với attempt budget riêng.

3. **Thủ phạm số 3: Account rác dính mã lỗi 401/403 gây loại trừ Connection hàng loạt**:
   - Khi một request đi vào account chết/bị thu hồi token (như 403 Forbidden), router thực thi `applyComboTargetExhaustion()` trong `open-sse/services/combo/targetExhaustion.ts`:
     `sets.exhaustedConnections.add("${provider}:${connId}")`
   - Account lỗi này bị loại và kích hoạt router fallback nhảy cóc sang target tiếp theo.
   - **Cách fix**: Rà soát call-logs tìm các connectionId dính 403/401 và xóa triệt để khỏi combo models.

4. **Thủ phạm số 4: Trần Concurrency Cap (Mặc định 2 request đồng thời/account)**:
   - Các connection Antigravity bị áp trần `maxConcurrency = 2`.
   - Khi có nhiều subagent/worker hoặc request burst song song, connection đang giữ 2 request sẽ bị skip:
     `Skipping <model> — connection <id> is at max concurrency cap (2); spilling to next priority target`.
5. **Thủ phạm số 5: Cooldown theo từng Connection ID (Log gây hiểu nhầm)**:
   - Khi một account gặp lỗi upstream (403, 429, 500), OmniRoute lưu vào `cooldownMap` dạng `provider:connectionId` với thời gian phạt nhân đôi (1s -> 2s -> 4s -> ... tối đa 300s = 5 phút).
   - Trong `combo.ts`, log in ra chuỗi cứng:
     `Skipping <model> — provider antigravity in global cooldown`
     *(Lưu ý: Log ghi chữ "provider ... in global cooldown" nhưng thực chất là đang kiểm tra per-connection cooldown `isProviderInCooldown(provider, target.connectionId)`).*
   - Nhiều account bị dính cooldown sẽ bị bỏ qua hàng loạt trong tích tắc.

Khi kết hợp Session Stickiness + Account lỗi 403 + Nested Combo Flatten: Chỉ 1-2 account đầu bị dồn tải và lỗi, router lập tức bỏ qua 70 account Gemini còn lại để rơi thẳng vào Tier 2 (`ag-claude`).

## 3. Các điểm mù cần lọc trên OmniRoute (:20129)
1. **Acc rác/hết hạn kẹt trong pool**:
   - Acc có `testStatus == "expired"` hoặc `isActive == False`.
   - Acc bị mất `connectionId` (ví dụ `connectionId: null` do restore lỗi).
   - Acc có ID connection không tồn tại trong danh sách `/api/providers`.
2. **Cập nhật Combo qua REST API**:
   - Lấy danh sách connection hợp lệ: `GET /api/providers` -> filter `c.isActive && c.testStatus == "active"`.
   - Lấy danh sách combos: `GET /api/combos`.
   - Lọc bỏ models trỏ tới connection không hợp lệ hoặc thiếu `connectionId`.
   - Update combo bằng UUID (`c["id"]`): `PUT /api/combos/{combo_id}` (lưu ý dùng combo UUID, không dùng tên chuỗi nếu combo có ID dạng UUID).
3. **Reset nhanh Circuit Breaker & Cooldown In-Memory**:
   - Khi cần giải phóng ngay lập tức các account bị phạt cooldown hoặc circuit breaker đang treo:
     `curl -s -X POST "http://127.0.0.1:20129/api/resilience/reset" -H "Content-Type: application/json" -d '{}'`
     Trả về `{"ok":true,"resetCount":N,"message":"Reset N circuit breaker(s) and model lockouts"}`.

## 4. Nguyên tắc cấu hình Tier cho Combo Worker
- **CẤM** đặt Tier không có quota thực tế (như Claude Sonnet 4.6 trên dàn Antigravity không mua quota) làm Tier trung gian trong combo chạy tác vụ tự động (`omni-worker`).
- Khi Tier 1 (Gemini) bị nghẽn tải, Tier 2 không có quota sẽ biến thành **"Bẫy Semaphore Timeout 30s"**, làm tê liệt toàn bộ flow thay vì fallback an toàn sang Free Pool.
- Combo worker an toàn: `ag-gemini-pool-3` (Tier 1) ➔ `omni-free` (Tier 2).
