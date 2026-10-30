---
name: farm-network-gate-contract
description: "Use when designing farm Wi-Fi/proxy safety gates."
version: 1.0.0
category: automation
tags: [farm, wifi, proxy, ssot, fail-closed, device-lock, evidence]
---
# Farm Network Gate Contract

Use this skill when a multi-device Android farm needs reliable Wi-Fi assignment, proxy mapping, recovery, or a guard against ad-hoc network changes. The goal is not merely to reconnect a phone: it is to make a wrong SSID/PSK/proxy mapping mechanically difficult or impossible.

## Design principles

1. **Single source of truth (SSOT).** Wi-Fi groups and proxy mappings are authoritative data, not caller-supplied strings. Keep Wi-Fi credentials and proxy endpoints in separate sources. Never infer a profile from the currently connected SSID.
2. **One canonical mutation primitive.** Expose an API shaped like `apply_profile(machine)`; the caller supplies only the machine identifier. The primitive resolves SSID, security, credential reference, subnet, and proxy endpoint from validated data. Reject caller-supplied SSID, PSK, host, or port.
3. **O(1) resolution after load.** Validate ranges once, reject overlaps/gaps and missing fields, then build an indexed `machine -> profile` map. Unknown or ambiguous machines fail closed; there is no fallback group and no guessed credential.
4. **Lock before mutation.** Acquire the machine/device lock before any write, reboot, profile removal, or join operation. Confirm serial provenance independently. A busy lock means untouched and blocked, not forceful takeover unless the operator explicitly authorizes preemption.
5. **Idempotency.** Read current state first. If the expected Wi-Fi, L3 route, and proxy are already healthy, return `NO_OP` without disrupting a running session.

6. **Profile and Proxy Session Isolation (User correction & Antifraud Invariant).** Đổi tài khoản mới hoặc đổi quốc gia/proxy bắt buộc tạo profile mới toanh (`Profile_name` qua API v3 GPM). CẤM TUYỆT ĐỐI tái sử dụng profile cũ vì sẽ bị dính vết fingerprint/tokens (`datr`, `device_id`, session tokens) dẫn tới kích hoạt chối bỏ tự động (`registration_rejected` / `Không thể tạo tài khoản mới`). Chi tiết tại `references/gpm-profile-and-proxy-session-isolation-invariant.md`.

7. **SSOT Proxy Identity Presentation & Hot Standby Pool.** Trên mọi bề mặt dữ liệu (Excel SSOT, SQLite `farm_master.db`, Web Ledger `kibe:1905`), proxy gán máy BẮT BUỘC hiển thị danh tính proxy thật (`tb.taadaa.click:51xx`, `test.taadaa.click:51xx`, `192.168.110.2:100xx`), CẤM hiển thị cổng trung chuyển nội bộ `:202xx`. MikroTik duy trì cố định 4 port dự phòng nóng `192.168.110.2:10028..10031` (Hot Standby) để hot-swap khi line lỗi hoặc cấp phát nuôi GPM/test. Chi tiết tại `references/ssot-proxy-identity-vs-mechanical-hop-and-isp-ceilings.md`.

## Required gate sequence

```text
validate SSOT
  -> resolve machine/profile/serial
  -> acquire device lock
  -> read current state and decide NO_OP vs apply
  -> apply exact resolved profile
  -> verify L2 Wi-Fi
  -> verify L3 address/route/gateway
  -> verify L4 proxy
  -> write sanitized evidence
  -> release lock
```

The sequence is one-way: if a gate fails, do not run downstream checks or change another layer to hide the failure.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
