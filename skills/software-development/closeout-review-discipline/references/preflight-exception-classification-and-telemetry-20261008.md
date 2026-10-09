# Preflight Exception Classification & Structured Telemetry Remediation (2026-10-08)

## 1. Context & The 81/100 Rejection Signature
In session closeout for `D:/Taadaa/Tiktok-video`, commit `893b5d9` attempted to separate device connection loss (`DEVICE_OFFLINE`) from VPN misconfigurations (`PREFLIGHT_VPN_BLOCKED`) inside `run_post.py`.

The Sol Auditor closeout gate initially scored 81/100 with the following critique:
> *"Logic nhận diện lỗi vẫn phụ thuộc vào so khớp chuỗi trong message exception ('device is offline' hoặc 'disconnected'), có nguy cơ phân loại sai nếu thông báo lỗi thay đổi hoặc dùng wording khác... Bằng chứng test chỉ bao phủ 5 test pass, chưa kiểm tra hành vi ngược khi lỗi VPN thực sự xảy ra, và không có thay đổi telemetry cấu trúc."*

Subsequent attempt scored 84/100, still below the 85 threshold, citing lack of structured telemetry fields in the failure report.

## 2. Root Cause Analysis
1. **Ad-hoc Substring Matching Fragility:**
   Using simple `if "device is offline" in str(cpe)` ignores established core helpers (e.g. `automation_core.adb.is_connection_lost`) which contain the full canonical tuple of disconnection signatures (`CONNECTION_LOST_MARKERS`).
2. **Missing Exception `__cause__` Inspection:**
   When exceptions are wrapped (`raise ConsumerPreflightError(...) from adb_err`), the outer message might be reworded while the inner exception carries the diagnostic signal.
3. **Absence of Negative / Inverse Behavioral Tests:**
   Testing only offline errors does not prove that true VPN failures (such as `vpn interface tun0 not found` or `timeout waiting for vpn`) are preserved and not erroneously misclassified as offline.
4. **Unstructured Telemetry:**
   Placing raw formatted strings only in `reason` makes automated downstream categorization impossible; reviewers require structured classification fields.

## 3. The 86/100 Remediation Pattern

### A. Production Exception Handler (`run_post.py`)
```python
    except ConsumerPreflightError as cpe:
        cpe_str = str(cpe).strip()
        from automation_core.adb import is_connection_lost
        cause = getattr(cpe, "__cause__", None)
        if is_connection_lost(cpe_str) or (cause and is_connection_lost(str(cause))):
            err_type = "DEVICE_OFFLINE"
        else:
            err_type = "PREFLIGHT_VPN_BLOCKED"
        logger.error(
            f"[{err_type}] device={device_id} "
            f"vpn_required={vpn_required} error={cpe}"
        )
        reporter = Reporter(config.runtime_root, run_id)
        reporter.save_report({
            "status": "FAILED",
            "device_id": device_id,
            "reason": f"[{err_type}] {cpe}",
            "error_type": err_type,
            "error_classification": err_type,
            "offline_cause": str(cause) if cause else None,
            "vpn_required": bool(vpn_required),
        })
        return 2
```

### B. Comprehensive Parameterized & Negative Tests (`test_vpn_preflight_post.py`)
```python
# 1. Negative test: verify true VPN failure still produces PREFLIGHT_VPN_BLOCKED
def test_vpn_preflight_failure_blocks_execute_and_saves_failed_report(monkeypatch, tmp_path):
    patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "automation_core.preflight.require_android_vpn",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ConsumerPreflightError("vpn interface tun0 not found")
        ),
    )
    result = run_post.run_real(make_config(tmp_path), "serial-1")
    assert result == 2
    report = FakeReporter.reports[0]
    assert report["error_type"] == "PREFLIGHT_VPN_BLOCKED"
    assert report["error_classification"] == "PREFLIGHT_VPN_BLOCKED"

# 2. Comprehensive offline variants test
@pytest.mark.parametrize(
    "error_msg",
    [
        "device is offline or ADB/USB disconnected for serial-offline",
        "error: device offline",
        "error: device not found",
        "error: device unauthorized",
        "cannot connect to daemon",
        "adb command timed out",
    ],
)
def test_vpn_preflight_device_offline_saves_device_offline_report(monkeypatch, tmp_path, error_msg):
    patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "automation_core.preflight.require_android_vpn",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ConsumerPreflightError(error_msg)
        ),
    )
    result = run_post.run_real(make_config(tmp_path), "serial-offline")
    assert result == 2
    report = FakeReporter.reports[0]
    assert report["error_type"] == "DEVICE_OFFLINE"
    assert report["error_classification"] == "DEVICE_OFFLINE"
```

## 4. Verification & Score Outcome
- Focused pytest: `pytest tests/test_vpn_preflight_post.py -v` $\rightarrow$ 10/10 passed in 0.95s.
- Diff size: <= 2 files, 25 total lines numstat (micro-diff).
- Closeout Gate: **86 / 100 — APPROVED (Exit 0)**.
