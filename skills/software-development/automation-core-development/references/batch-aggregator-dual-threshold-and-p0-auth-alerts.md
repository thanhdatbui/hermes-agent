# Batch Aggregator: Dual-Threshold Systemic Errors & P0 Auth Alerts

## Overview
`automation_core.batch_aggregator` provides batch error aggregation and automated alerting for the Taadaa phone farm. It protects operators against alert fatigue by separating systemic fleet-wide issues from sporadic failures, while ensuring zero-delay escalation for critical account/login issues (P0).

## 1. Dual-Threshold Systemic Failure Detection
An error cluster is deemed **systemic** if and only if:
$$\text{count} \ge \text{min\_count (default 3)} \quad \text{AND} \quad \frac{\text{count}}{\text{total}} \ge \text{min\_rate (default 10\%)}$$

Sporadic failures failing either condition are filtered out of general systemic alerts.

## 2. P0 Auth / Login Escalation Bypass
Keywords detecting lost session, account checkpoint, or auth challenges:
```python
AUTH_CRITICAL_KEYWORDS = ("login", "account screen", "verification", "checkpoint", "auth", "văng", "identity")
```
If any failed machine matches these keywords, an immediate alert MUST be dispatched regardless of whether systemic thresholds are met.

## 3. Alert Formatting Invariants (`format_alert_message`)

### Case A: Only P0 Auth Failures (`len(systemic_signatures) == 0 and auth_failures`)
When no systemic failure has occurred but accounts are lost/logged out:
* **Header**:
  ```html
  🚨 <b>[FARM ALERT: P0 MẤT PHIÊN ĐĂNG NHẬP / VĂNG ACCOUNT]</b>
  • Quy mô batch: <b>{total_machines} máy</b> | Thành công: {succeeded_count} | Thất bại: {failed_count}
  • Phát hiện: <b>{len(auth_failures)} máy dính lỗi login/xác minh cần cứu acc khẩn cấp!</b>
  ```
* **Body structure**:
  1. Print list of machines affected by auth failure first (`📋 CHI TIẾT MÁY DÍNH LỖI LOGIN / XÁC MINH:`).
  2. Follow with Canary Policy & Recovery instructions using the first auth failure machine as canary target.
  3. Attach representative screenshot/XML if available.

### Case B: Systemic Errors Present (`len(systemic_signatures) > 0`)
* **Header**:
  ```html
  🚨 <b>[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG</b>
  • Quy mô batch: <b>{total_machines} máy</b> | Thành công: {succeeded_count} | Thất bại: {failed_count}
  • Số cụm lỗi hệ thống: <b>{len(systemic_signatures)}</b>
  ```
* **Body structure**:
  1. Dual-threshold systemic error clusters and affected machine lists.
  2. Canary Policy instructions.
  3. If `auth_failures` also exists, append `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]:` at the end.

## 4. Test Verification
Always verify using the automation environment Python:
```bash
D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest tests/test_batch_aggregator.py -v
```
Ensure assertions check both the distinct header formats and canary target assignments.
