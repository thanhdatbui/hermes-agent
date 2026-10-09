# Closeout Gate Payload Truncation & Fail-Closed Partial Approval Trap

> 📌 **Bối cảnh thực tế (02-03/10/2026):**  
> Khi chốt phiên, Sol Auditor (:20129) chấm điểm chuyên môn đạt **89 / 100** (ngưỡng pass $\ge 85$, test suite 49/49 passed in 3.8s).  
> Tuy nhiên `closeout_gate.py` vẫn trả về `Verdict: REJECTED`, `ready_to_close: false`, `exit code 1`.

---

## 1. Cơ Chế Bản Chất Của Sự Cố

### 1.1 Trần Payload An Toàn Của Sol High (`:20129`)
* `sol_payload_guard.py` đặt trần cứng vật lý:
  - `ABSOLUTE_CEILING_BYTES = 40_000` (40KB).
  - `CALCULATED_MAX_ALLOWED = 37_952` bytes.
  - `SOL_TARGET_BYTES = 32_768` bytes.
* Khi repo tích tụ uncommitted changes qua nhiều phiên (ví dụ: `cron_gpm_gmail_nurture.py` và test suite tích tụ 1.466 dòng diff, kích thước 86.910 chars = ~87KB), kích thước diff vượt gấp hơn 2 lần trần an toàn.

### 1.2 Invariant Fail-Closed Tuyệt Đối Trong `closeout_gate.py`
Khi diff vượt quá trần, `SolPayloadGuard` bắt buộc phải digest và cắt tỉa diff ở level L4, đồng thời gán cờ:
```python
meta["truncated"] = True
```

Khi model trả về điểm $\ge 85$, `closeout_gate.py` kiểm tra:
```python
elif verdict == "APPROVED" and meta.get("truncated"):
    verdict = "APPROVED_PARTIAL"
    meta["partial_approval"] = True
    if scorecard and isinstance(scorecard, dict):
        scorecard["verdict_qualifier"] = "APPROVED_PARTIAL"
        scorecard["ready_to_close"] = False  # ❌ Ép hạ ready_to_close xuống False
```

Và hàm thẩm định tính hợp lệ của scorecard:
```python
if scorecard.get("ready_to_close") is not True:
    return "REJECTED", scorecard
```
**Hệ quả:** Dù điểm chuyên môn của Auditor đạt rất cao (89/100), gate vẫn trả về `REJECTED` vì một phần diff bị che khuất, vi phạm nguyên tắc "chỉ duyệt khi Auditor nhìn thấy 100% diff".

---

## 2. Dấu Hiệu Nhận Biết Bẫy Truncation

1. `Overall Score >= 85` (ví dụ: 89/100).
2. `Status: ❌ FAIL` và `Verdict: REJECTED`.
3. Trong `Model Response`: `"ready_to_close": false`.
4. Key findings của Reviewer luôn có nhận xét:
   - *"Diff được cung cấp bị truncation, một phần logic chưa được review..."*
   - *"Không thể xác nhận toàn bộ hành vi runtime vì diff bị truncation..."*
5. `git diff --cached --stat` cho thấy tổng diff > 500-1000 dòng (> 35KB).

---

## 3. Kỷ Luật Điều Phối (Anti-Loop & Minh Bạch Báo Cáo)

### 3.1 CẤM VÒNG LẶP MÙ (ANTI-LOOP)
* **CẤM TUYỆT ĐỐI**: Cố chạy lại `closeout_gate.py` liên tiếp với cùng một diff 86KB khổng lồ. Việc chạy lại không làm thay đổi kích thước payload; gate sẽ luôn fail-closed ở level L4.
* **CẤM TUYỆT ĐỐI**: Tự ý bypass gate, tự ý sửa code `closeout_gate.py` hay ép `git commit/push` trái quy định Hard Invariant.

### 3.2 HÀNH ĐỘNG ĐÚNG
1. **Kiểm tra numstat**: `git diff --cached --numstat` để xem chính xác bao nhiêu dòng và bao nhiêu file đang nằm trong staged.
2. **Nhận diện nguyên nhân gốc**: Phân biệt rành mạch giữa:
   - *Lỗi chất lượng mã nguồn* (logic sai, test rớt, điểm < 85).
   - *Lỗi trần hạ tầng payload* (điểm $\ge$ 85 nhưng diff bị truncate do nợ kỹ thuật tích tụ uncommitted qua nhiều ca).
3. **Báo cáo trung thực, minh bạch**:
   - Trình bày rõ ràng cho User: Điểm chuyên môn thực tế (89/100), kết quả test (49/49 pass), các điểm đã fix.
   - Nêu rõ cơ chế bảo vệ fail-closed của gate đang chặn commit do trần 37KB.
   - Để User quyết định nghiệm thu hiện trường hoặc tách commit theo từng atomic changeset nhỏ để diff luôn $\le 30$KB.
