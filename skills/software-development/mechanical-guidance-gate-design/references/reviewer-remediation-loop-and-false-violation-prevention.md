# Reviewer Remediation Loop & False Violation Prevention (Chống Báo Động Giả Khi Đang Sửa Code)

## 1. Bối Cảnh Sự Cố & Nỗi Đau Vận Hành
Trong kiến trúc tự phục hồi khép kín (Closed-Loop Auto-Repair), việc nộp candidate diff lên Reviewer LLM (Sol Reviewer qua `:20129` hoặc Closeout Gate) thường trải qua nhiều vòng lặp thẩm định (Multi-Turn Remediation):
- Lần 1: Reviewer chấm điểm < 85 -> Ghi `verdict: REJECTED` vào `logs/gate_audit.jsonl`.
- Strike 1 & 2 Remediation: Sol Repair hoặc Worker tự động sinh patch khắc phục, chạy focused test.
- Lần 2/3: Reviewer chấm lại đạt >= 85 -> Ghi `verdict: APPROVED` vào `logs/gate_audit.jsonl`.
- Pre-push hook (`safe_push.py`): Đối soát bản ghi `APPROVED` khớp commit HEAD và mở rào cho git push remote.

### Lỗi Thiết Kế Ngây Thơ Của Watchdog Giám Sát (Naive Line-by-Line Regex):
Watchdog đối soát định kỳ (`gate_compliance_watchdog.py`) quét qua các dòng log và dùng regex thô:
- `pass_re: verdict\W+APPROVED\b`
- `fail_re: verdict\W+(?:REJECTED|CHANGES_REQUESTED|NEEDS_FIX)\b`
Hễ dòng nào chứa `REJECTED`, watchdog tăng biến đếm `fail_hits += 1` và phán quyết:
`❌ G1 Model review: FAIL (hợp lệ: 18, vi phạm: 7) -> Kết luận: FAIL`.

### Hệ Quả:
- **Báo Động Giả (False Positive Alarm):** Hệ thống đang đi đúng quy trình sửa lỗi nghiêm ngặt (Closed-Loop Fix) và đã được duyệt `APPROVED`, nhưng Watchdog lại gán nhãn vi phạm nghiêm trọng và bắn chuông báo động đỏ về Telegram Farm Alert.
- **Mâu Thuẫn Kiến Trúc:** Đánh đồng việc Reviewer từ chối bản nháp trong phòng thí nghiệm với hành vi vi phạm kỷ luật đẩy code bậy ra production.

---

## 2. Tiêu Chuẩn Cơ Học Phân Loại Remediation Loop (4 Chốt Chặn Bắt Buộc)

### Chốt Chặn 1: Context/Repo Grouping (Gom Nhóm Theo Ngữ Cảnh)
CẤM TUYỆT ĐỐI đếm vi phạm line-by-line độc lập cho Model Review. Bắt buộc gom nhóm các sự kiện review theo định danh nguồn (`repo` hoặc `source_file`):
```python
g1_by_repo = {}  # repo -> [pass_count, fail_count]
```

### Chốt Chặn 2: Remediation State Accounting (Chuyển Hóa Thành Tích Khắc Phục)
- Nếu trong cùng `repo`/ngữ cảnh có `pass_count > 0` (tức là đã có lần review đạt `APPROVED` sau hoặc cùng ca):
  + Toàn bộ các lần `fail_count` của repo đó được tính là **`remediation_hits`** (các bước thử và khắc phục lỗi hợp lệ).
  + Số lần vi phạm **`fail_hits = 0`**.
- Trạng thái của Gate 1 đối với repo đó là **`PASS`**.

### Chốt Chặn 3: Strict Violation Criterion (Chỉ Phạt Khi Bỏ Dở Không Sửa)
Một lần `REJECTED` CHỈ ĐƯỢC TÍNH LÀ VI PHẠM (`fail_hits += fail_count`) khi và chỉ khi:
- Trong suốt cửa sổ quan sát (6h), repo đó kết thúc với `pass_count == 0` (tức là bị Reviewer từ chối nhưng không hề có lần nào sửa đạt `APPROVED` để giải quyết).
- Đây là bằng chứng xác thực của việc bỏ dở task (Unremediated Abandonment) hoặc cố tình trốn tránh Closeout Gate.

### Chốt Chặn 4: Transparent Telemetry & Report Rendering
Báo cáo gửi về Operator / Telegram phải phản ánh trung thực nỗ lực tự sửa chữa của hệ thống:
```python
extra = f", remediation: {g['remediation_hits']}" if g.get("remediation_hits") else ""
lines.append(f"{icon} *{g['id']} {g['name']}*: {g['status']} (hợp lệ: {g['pass_hits']}, vi phạm: {g['fail_hits']}{extra})")
```
- **Ví dụ đầu ra chuẩn:**
  `✅ *G1 Model review*: PASS (hợp lệ: 18, vi phạm: 0, remediation: 7)`
- Operator nhận tin nhắn nhìn thấy ngay: Có 7 lần reviewer chấm fail trong ca và cả 7 lần đều đã được tự động fix thành công đạt Approved!
