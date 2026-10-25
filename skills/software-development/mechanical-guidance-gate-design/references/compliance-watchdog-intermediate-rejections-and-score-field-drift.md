# Compliance Watchdog Intermediate Rejections Triage & Schema Drift Governance

## 1. Bối Cảnh Thực Tế (Case Study 6H Gate Compliance Watchdog)
Khi cronjob đối soát 6h (`gate_compliance_watchdog.py`) chạy định kỳ quét `logs/gate_audit.jsonl` và `logs/safe_push_audit.jsonl`, nó ghi nhận:
```text
🛡️ [FARM GATE COMPLIANCE WATCHDOG — 6H REPORT] ❌
Khung giờ: 2026-10-24 17:00:43 UTC -> 2026-10-24 23:00:43 UTC (6h qua)
G1 Model review: FAIL (hợp lệ: 18, vi phạm: 7)
Kết luận: FAIL
```
Khi Coordinator nhận được báo cáo này, phản xạ sai lầm là hoảng loạn tưởng hệ thống có code vi phạm bị lọt lên repo hoặc vội vã kết luận Farm bị hỏng.

---

## 2. Bản Chất Kỹ Thuật: Intermediate Rejection vs Actual Bypass

### A. Vòng Lặp Phát Triển & Remediation Hợp Pháp
Trong kiến trúc Closeout Gate và Sol Repair (Strike 1 & Strike 2 Remediation):
1. Candidate diff được tạo ra bởi Worker/Sol Proposal.
2. `closeout_gate.py` chạy độc lập thẩm định 5 tiêu chí: Logic, Test, Telemetry, Safety, Architecture.
3. Nếu score < 85 (ví dụ: 76, 78), Gate trả về `verdict: REJECTED` và ghi vào `gate_audit.jsonl`.
4. Sol Repair / Developer tiếp tục hoàn thiện mã nguồn, bổ sung test coverage và re-run closeout gate.
5. Khi đạt score >= 85, Gate cấp `verdict: APPROVED`.
6. Chỉ khi có bản ghi APPROVED khớp đúng commit SHA, `safe_push.py` mới cho phép đẩy code lên git remote.

### B. Bẫy Đếm Gộp Thô Sơ (Binary Flag Aggregation Trap)
Nếu watchdog áp dụng logic nhị phân cào bằng:
```python
passed, failed = hits[g.gate_id]
status = "FAIL" if failed else "PASS" if passed else "NO_EVIDENCE"
```
Bất kỳ phiên dev/fix nào trải qua 2-3 lần review fail trước khi pass đều sẽ bị gán nhãn `FAIL` trên toàn bộ báo cáo 6H. Đây là tỷ lệ từ chối tự nhiên của khâu kiểm định chất lượng, KHÔNG PHẢI là vi phạm rào chắn an toàn (Gate Breach).

---

## 3. Quy Trình 4 Bước Triage Siêu Tốc O(1) Cho Coordinator

Khi nhận alert `G1 Model review: FAIL`:

1. **Kiểm Tra Chuỗi Audit Log (`gate_audit.jsonl`):**
   - Xác nhận các bản ghi REJECTED có đi liền trước một bản ghi APPROVED trên cùng scope/repo hay không:
   ```bash
   python -c "import json; [print(json.loads(l)['verdict'], json.loads(l).get('score')) for l in open(r'D:\Taadaa\logs\gate_audit.jsonl', encoding='utf-8').readlines()[-15:]]"
   ```
   - Nếu bản ghi cuối cùng của phiên làm việc đó là `APPROVED`, kết luận vòng đời kiểm duyệt đã thành công khép kín.

2. **Đối Soát Pre-Push Hook (`safe_push_audit.jsonl`):**
   - Kiểm tra nhật ký push gần nhất:
   ```bash
   python -c "import json; [print(l.strip()) for l in open(r'D:\Taadaa\logs\safe_push_audit.jsonl', encoding='utf-8').readlines()[-6:]]"
   ```
   - Chứng minh: Mọi nỗ lực push trong lúc score < 85 đều bị chặn (`returncode: 1`), và lệnh push chỉ thành công (`returncode: 0`) sau khi đã có token APPROVED.

3. **Kiểm Tra Trạng Thái Git Commit (`git log`):**
   - Kiểm tra repo liên quan (`git log -n 5 --oneline`): Tất cả commit đã push đều có tag `[gate-approved]`.

4. **Kiểm Tra Trạng Thái Hàng Đợi Sự Cố:**
   - Xác nhận `runtime/incidents/pending` và `runtime/incidents/locks` bằng 0.

---

## 4. Bẫy Lệch Schema Log Regex (Field Drift Trap: `closeout_score` vs `score`)

### A. Triệu Chứng
Watchdog báo `⚪ G5 Closeout score: NO_EVIDENCE (hợp lệ: 0, vi phạm: 0)` mặc dù trong 6h qua có hàng chục lượt chạy `closeout_gate.py`.

### B. Nguyên Nhân
- Regex trong watchdog: `_rx(r"closeout_score\W+(?:8[5-9]|9\d|100)\b")`.
- Schema thực tế xuất ra từ `closeout_gate.py`:
  ```json
  {"entry_id": "...", "timestamp_utc": "...", "repo": "...", "verdict": "REJECTED", "score": 78, "threshold": 85}
  ```
  Tên trường thực tế là `"score"`, không phải `"closeout_score"`.

### C. Giải Pháp Kiến Trúc (Schema Resilience)
1. **Multi-Key Regex Matching:** Regex của Watchdog bắt buộc phải bao quát cả 2 định dạng:
   ```python
   _rx(r"(?:closeout_score|(?<!\w)score)\W+(?:8[5-9]|9\d|100)\b")
   ```
2. **Schema Contract Parity Test:** Bắt buộc có test trong `test_gate_compliance_watchdog.py` đọc trực tiếp mẫu dòng log thực tế từ `gate_audit.jsonl` để bảo đảm regex không bị trượt khi schema log tiến hóa.
