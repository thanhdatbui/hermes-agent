# Reboot-máy-khi-lỗi-proxy (2026-08-10)

## Rule (phủ all repo + core automation-core + skill này)

**Lỗi proxy readiness/VPN verifier fail khi ACQUIRE_LOCKS/preflight**
(vd: `proxy readiness timed out`, `live VPN verifier failed: ConsumerPreflightError`)
→ **KHÔNG retry mù, KHÔNG sửa lock thủ công**:

1. Reboot máy (soft reboot bounded, `--recovery-mode --allow-device-reboot-recovery`)
2. Gan-proxy watcher (chạy ngầm: `gan_proxy_fleet.py watch --all --workers 80`, poll 30s) tự gán VPN lại + publish readiness sau boot
3. Chờ watcher publish readiness (timeout 60–90s) rồi mới chạy lại workflow

## Context

- Ngày: 2026-08-10, máy 36: `[DEVICE_LOCK_FAILED] ACQUIRE_LOCKS: proxy readiness timed out cho ce10160ac8f1962305; live VPN verifier failed` sau PC sleep.
- Quy tắc này song song với RULE 3 BƯỚC FIX LỖI UI (B1 ATX-kill → B2 force-stop+relaunch 1 → B3 soft reboot 1; budget máy/turn).