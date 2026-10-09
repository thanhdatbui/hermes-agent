# Farm Alert Auto-Remediation and Cluster Routing

## Mandatory loop
A Farm Alert is an execution trigger, not a diagnosis-only request:

`ALERTED → EVIDENCE_CAPTURED → CLASSIFIED → WORK_ASSIGNED → PATCH_VERIFIED → CANARY_APPROVED → CANARY_RESULT → CLOSED/BLOCKED`

- Read the exact current log using a bounded window, then open matching XML and screenshot artifacts from the same run/attempt.
- Group machines by fingerprint before dispatch. Separate `INFRA` (offline/not-found/ADB transport), `STRUCTURAL` (same detector/selector/parser failure across machines), and `BUSINESS/MANUAL` (OTP, phone verification, ownership ambiguity). For mixed detector/business states, fix recognition only; never automate the human verification.
- Diagnosis is never terminal. Dispatch one narrowly scoped worker per structural fingerprint with exact files/function anchor, real fixture paths, focused offline test, diff budget, and no-live-device contract.
- Coordinator independently checks allowlisted diff/numstat, `git diff --check`, reruns the focused test, and verifies the fixture postcondition. Worker prose is not proof.
- Only then run one bounded official-runner canary on one correctly resolved machine, with host/cluster config, ADB route, device lock, and Safe Resume checkpoint. Do not use manual tap/keyevent/`ime set` or bypass the official runner.
- Count attempts by `(machine, fingerprint, alert chain)`; max two meaningful attempts. Repetition becomes BLOCKED with an audit packet and preserved handoff lock, not an infinite retry loop.

## Cluster routing pitfall
Before declaring a Device ID missing, resolve the machine against the correct cluster workbook and host config. Kibe covers machines 1–80; Admin covers machines 200+. For Admin machine M243, the correct invocation must include:

```text
TAADAA_HOST_CONFIG=D:/Taadaa/machine-config/admin.yaml
ADB_SERVER_SOCKET=tcp:192.168.110.119:5037
```

A Kibe environment can falsely report `Total targets: 0` or `device not found` even when the serial exists in Admin workbooks. Verify runner output for resolved machine, serial, source workbook, tracking workbook, and artifact root before canary.

## Incident evidence pattern
For the Row 2 incident, M243 serial `ce01171182ee820501` exists in Admin `PROXYgandienthoai.xlsx` and Admin tracking/safe workbooks. The earlier false blocker came from running with Kibe host config. The correct distinction is `routing/config blocker`, not `Device ID absent`.

## Reporting contract
Retain exact log/XML/screenshot paths, timestamps, run/attempt identity, host config, serial, lock owner, and focused-test output. An offline patch PASS is not a live fix; live success requires a fresh official-runner canary artifact.
