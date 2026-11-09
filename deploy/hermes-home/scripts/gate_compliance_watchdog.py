#!/usr/bin/env python3
"""Audit 8 farm gates over a rolling time window in logs/ and runtime/audit_logs/."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Single Source of Truth for Farm Gate & Agent Compliance
DEFAULT_ROOT = Path(r"D:\Taadaa")
LOG_DIRS = ("logs", "runtime/audit_logs", "tools/guardgate")
LOG_SUFFIXES = {".log", ".jsonl", ".txt", ".json"}
MAX_FILE_BYTES = 20 * 1024 * 1024
TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})")
LOCAL_NAIVE_LOGS = {"dispatch_audit.jsonl", "console_block_audit.jsonl"}
FARM_ALERT_CHAT_ID = "-5373649734"


@dataclass(frozen=True)
class Gate:
    gate_id: str
    name: str
    pass_re: re.Pattern
    fail_re: re.Pattern
    source_file: str = ""


def _rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


GATES = (
    Gate("G1", "Visual Evidence Gate",
         _rx(r"MEDIA:\S+|\"reason_code\":\s*\"OK\"|\"receipt_id\":\s*\"rec_"),
         _rx(r"EVIDENCE_MISSING|VERIFIED_SUCCESS_WITHOUT_EVIDENCE\b"),
         "vision_receipts"),
    Gate("G2", "Planning Gate",
         _rx(r"SOL_PLAN_ID|SOL_PLAN_SOURCE|\"tier\":\s*\"(?:sonnet|sol|coordinator)\""),
         _rx(r"PLAN_MISSING|PLAN_FAILED|PLANNER_BYPASSED\b"),
         "dispatch_planner"),
    Gate("G3", "Worker Dispatch Gate",
         _rx(r"\"category\":\s*\"OK\"|\"action\":\s*\"allow\""),
         _rx(r"\"category\":\s*\"(?:TIMEOUT|QUOTA|NO_DIFF|NEEDS_INPUT|COMMAND_ERROR)\"|\"action\":\s*\"block\""),
         "dispatch"),
    Gate("G4", "Invariant GuardGate",
         _rx(r"\"status\":\s*\"ALLOW\""),
         _rx(r"\"status\":\s*\"(?:DENY|BLOCK|QUARANTINE)\"|\"event\":\s*\"rule_block\"|\"error\":\s*\"(?:INVARIANT_VERIFICATION_FAILED|MISSING_INVARIANT_OR_WAIVER|RULES_INTEGRITY_VIOLATION)\""),
         "ledger"),
    Gate("G5", "Closeout Gate",
         _rx(r"verdict\W+APPROVED\b|\[GuardEngine\s+ALLOW\]|CLOSEOUT_PASSED|Invariant Crystallized:"),
         _rx(r"verdict\W+(?:REJECTED|CHANGES_REQUESTED|NEEDS_FIX|INVARIANT_OR_WAIVER_MISSING|GUARDGATE_INVARIANT_VIOLATION|RULES_INTEGRITY_VIOLATION)\b|\[Crystallize\s+DENY\]|\[GuardGate\s+DENY\]"),
         "gate_audit"),
    Gate("G6", "Pre-Push Safe Guard",
         _rx(r"\"returncode\":\s*0|\"success\":\s*true\b"),
         _rx(r"\"returncode\":\s*[1-9]\d*|\"success\":\s*false\b"),
         "safe_push_audit"),
    Gate("G7", "Anti-Scan & Terminal Guard",
         _rx(r"\"action\":\s*\"allow\""),
         _rx(r"\"action\":\s*\"block\""),
         "guard_scan_audit"),
    Gate("G8", "Cronjob Window Guard",
         _rx(r"\"decision\":\s*\"allow\""),
         _rx(r"\"decision\":\s*\"block\""),
         "console_block_audit"),
    Gate("G9", "Farm & GPM Proxy Guard",
         _rx(r"android_proxy_allow|gpm_proxy_allow"),
         _rx(r"android_proxy_domain_block|ANDROID_PROXY_BLOCKED|gpm_profile_no_proxy_block|GPM_PROXY_BLOCKED"),
         "proxy_guard_audit"),
    Gate("G10", "Claude Quota Gate",
         _rx(r"EXEC_ALLOW|EXEC_EXEMPT|EXEC_USER_OVERRIDE"),
         _rx(r"EXEC_BLOCKED_QUOTA|AGENT_OVERRIDE_BLOCKED"),
         "claude_quota_audit"),
    Gate("G11", "Patch Surgery Gate",
         _rx(r"\"status\":\s*\"(?:SUCCESS|OK)\""),
         _rx(r"\"status\":\s*\"(?:ANCHOR_FAIL|PATCH_FAIL|SYNTAX_FAIL|BUDGET_EXCEEDED)\""),
         "patch_audit"),
    Gate("G12", "Safety Valve Gate",
         _rx(r"\"status\":\s*\"(?:RESOLVED|CLEAR|RESUMED)\""),
         _rx(r"\"trigger_flag\":\s*\"(?:SOL_FALLBACK|SAFETY_VALVE_INTERCEPT|LOOP_INTERCEPT|EMERGENCY_ABORT)\"|\"status\":\s*\"TRIGGERED\""),
         "safety_valve_trigger"),
    Gate("G13", "Canary Verification Gate (Gate 6)",
         _rx(r"CANARY_PASSED|CANARY_VERIFIED|\"canary_status\":\s*\"PASS\"|canary_receipt_valid|Canary OK"),
         _rx(r"BLOCKED_CANARY_REQUIRED|BLOCKED_CANARY_VERIFY_FAILED|CANARY_FAIL|CANARY_TIMEOUT|CANARY_STALE"),
         "safe_push_audit"),
    Gate("G14", "Investigation Gate (Gate A)",
         _rx(r"\"route\":\s*\"investigate_allowed\"|\"action\":\s*\"allow\"|\"stage\":\s*\"investigate_done\""),
         _rx(r"subagent_edit_blocked|INVESTIGATION_BUDGET_EXCEEDED|INVESTIGATION_UNAUTHORIZED"),
         "dispatch_audit"),
)


def iter_sources(root: Path, cutoff: datetime):
    for rel in LOG_DIRS:
        base = root / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in LOG_SUFFIXES:
                continue
            try:
                if not path.is_file():
                    continue
                st = path.stat()
            except OSError:
                continue
            file_mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            if file_mtime >= cutoff:
                yield path, st.st_size, file_mtime


def read_tail(path: Path, size: int) -> list[str]:
    try:
        with path.open("rb") as fh:
            if size > MAX_FILE_BYTES:
                fh.seek(size - MAX_FILE_BYTES)
            data = fh.read()
    except OSError:
        return []
    return data.decode("utf-8", errors="replace").splitlines()


TEST_MOCK_SIGNATURES = (
    "pytest", "tmp_path", "target.py", "pytest-of-Kibe",
    "Review then apply constant change", "Review \"quoted\"", "Review 'quoted'", "backtick",
    "Batch constant changes", "Create a helper", "Investigate D:/Taadaa/tools/x.py",
    "count_active_locks", "grep -R lock", "--recursive token", "rg count_active",
    "rg.exe pattern", "rg pattern", "grep -rn foo", "audit_test",
    "os_walk_mock_signature", "os_walk_double_mock", "list_path_d_rglob_mock",
    "list_path_d_rglob_double_mock", "glob_glob_d_star_mock", "glob_glob_d_star_double_mock",
    "find . -name", "Get-ChildItem -Recurse",
    "script.py", "script.ps1", "bad.py", "bad_sub.py", "lookalike_flags", "other_alias_flags",
    "does_not_exist", "farm_action.py", "farm_burst.py", "fake_lock.py", "fake_fn.py",
    "fake_module.py", "empty_body.py", "nonexistent_runner",
    # Additional mock signatures for cron, farm contracts, injected keys, and SSH tests.
    "cron_agent_policy", "farm_contract", "fake_module", "attacker_injected_key", "farm_burst", "test_ssh_powershell", "unsafe_ssh.py", "bad_runner.py", "powershell -command get-process",
)


def is_test_log_line(line: str) -> bool:
    line_lower = line.lower()
    return any(sig.lower() in line_lower for sig in TEST_MOCK_SIGNATURES)


def parse_line_timestamp(line: str, path_name: str = "") -> datetime | None:
    line_s = line.strip()
    if line_s.startswith("{") and line_s.endswith("}"):
        try:
            d = json.loads(line_s)
            for k in ("timestamp_utc", "timestamp", "ts", "time", "created_at"):
                v = d.get(k)
                if isinstance(v, (int, float)):
                    try:
                        if v > 1e11:
                            v /= 1000.0
                        return datetime.fromtimestamp(v, tz=timezone.utc)
                    except (ValueError, OSError, OverflowError):
                        return None
                if isinstance(v, str):
                    try:
                        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = (dt.astimezone().astimezone(timezone.utc)
                                  if path_name in LOCAL_NAIVE_LOGS
                                  else dt.replace(tzinfo=timezone.utc))
                        return dt
                    except ValueError:
                        pass
        except Exception:
            pass
    match = TS_RE.search(line)
    if not match:
        return None
    try:
        dt = datetime.fromisoformat(f"{match.group(1)}T{match.group(2)}")
        if dt.tzinfo is None:
            dt = (dt.astimezone().astimezone(timezone.utc)
                  if path_name in LOCAL_NAIVE_LOGS
                  else dt.replace(tzinfo=timezone.utc))
        return dt
    except ValueError:
        return None


BLOCK_SUSPECT_RE = re.compile(r'\"action\":\s*\"block\"|\b(?:DENY|REJECTED|BLOCKED|QUARANTINE|ABORT)\b', re.IGNORECASE)


def in_window(line: str, cutoff: datetime, file_mtime: datetime | None = None,
              path_name: str = '') -> bool:
    ts = parse_line_timestamp(line, path_name=path_name)
    if ts is None:
        if file_mtime is not None and file_mtime >= cutoff and BLOCK_SUSPECT_RE.search(line):
            return True
        return False
    if cutoff.tzinfo is None and ts.tzinfo is not None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    elif cutoff.tzinfo is not None and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts >= cutoff


def evaluate(root: Path, hours: float, now: datetime | None = None) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.astimezone()
    cutoff = now - timedelta(hours=hours)
    hits = {g.gate_id: [0, 0] for g in GATES}
    g5_events_by_repo = {}
    blocked_rules = {}
    files = lines = 0
    for path, size, file_mtime in iter_sources(root, cutoff):
        files += 1
        for line in read_tail(path, size):
            if is_test_log_line(line):
                continue
            if not in_window(line, cutoff, file_mtime=file_mtime, path_name=path.name):
                continue
            lines += 1
            any_gate_matched = False
            for g in GATES:
                if g.source_file and path.name not in ("gates.log", "audit.jsonl", "review.jsonl") and g.source_file not in path.name:
                    continue
                passed = bool(g.pass_re.search(line))
                failed = bool(g.fail_re.search(line))
                if passed or failed:
                    any_gate_matched = True
                if g.gate_id == "G5" and (passed or failed):
                    try:
                        repo = json.loads(line).get("repo") or "default"
                    except (json.JSONDecodeError, AttributeError):
                        repo = "default"
                    line_ts = parse_line_timestamp(line, path_name=path.name) or file_mtime or cutoff
                    verdict = "REJECTED" if failed else "APPROVED"
                    g5_events_by_repo.setdefault(repo, []).append((line_ts, verdict))
                else:
                    if passed:
                        hits[g.gate_id][0] += 1
                    if failed:
                        hits[g.gate_id][1] += 1
                        # Collect actionable blocked rules
                        line_s = line.strip()
                        if line_s.startswith("{") and line_s.endswith("}"):
                            try:
                                d = json.loads(line_s)
                                r_id = d.get("rule_id") or d.get("route") or d.get("category") or d.get("reason") or d.get("event")
                                if r_id:
                                    tag = g.name.replace(" Gate", "").replace(" Guard", "")
                                    key = f"[{tag}] {r_id}"
                                    blocked_rules[key] = blocked_rules.get(key, 0) + 1
                            except Exception:
                                pass
            if not any_gate_matched and BLOCK_SUSPECT_RE.search(line):
                try:
                    d = json.loads(line.strip())
                    r_id = d.get("rule_id") or d.get("reason") or d.get("message") or "Unclassified-Block"
                except Exception:
                    clean = line.strip().lstrip('": \'"').strip()
                    r_id = clean[:50].strip() if clean else "Unclassified-Block"
                if str(r_id).startswith("["):
                    key = str(r_id)[:60]
                else:
                    key = f"[Unclassified] {r_id}"
                blocked_rules[key] = blocked_rules.get(key, 0) + 1

    # Scan sol_plans directory for G2 Planning Gate only if no hits in logs (anti-double-counting)
    if hits["G2"][0] == 0:
        sol_plans_dir = root / "runtime" / "sol_plans"
        if sol_plans_dir.is_dir():
            try:
                for p_file in sol_plans_dir.iterdir():
                    if p_file.is_file() and p_file.suffix.lower() == ".json":
                        try:
                            p_data = json.loads(p_file.read_text(encoding="utf-8"))
                            if isinstance(p_data, dict) and ("plan" in p_data or "plan_id" in p_data or "tasks" in p_data or "tier" in p_data):
                                st_dt = datetime.fromtimestamp(p_file.stat().st_mtime, tz=timezone.utc)
                                if st_dt >= cutoff:
                                    hits["G2"][0] += 1
                        except Exception:
                            pass
            except Exception:
                pass

    remediation_hits = 0
    g5_passed = 0
    g5_failed = 0
    for repo, events in g5_events_by_repo.items():
        sorted_events = sorted(events, key=lambda x: x[0])
        last_verdict = sorted_events[-1][1]
        rejections = sum(1 for _, v in sorted_events if v == "REJECTED")
        approvals = sum(1 for _, v in sorted_events if v == "APPROVED")
        g5_passed += approvals
        if last_verdict == "APPROVED":
            remediation_hits += rejections
        else:
            g5_failed += rejections

    hits["G5"][0] = g5_passed
    hits["G5"][1] = g5_failed

    gates = []
    for g in GATES:
        passed, failed = hits[g.gate_id]
        remediated = remediation_hits if g.gate_id == "G5" else 0
        status = "FAIL" if failed else "PASS" if passed else "NO_EVIDENCE"
        gates.append({"id": g.gate_id, "name": g.name, "status": status,
                      "pass_hits": passed, "fail_hits": failed,
                      "remediation_hits": remediated})

    statuses = {g["status"] for g in gates}
    if "FAIL" in statuses or any(k.startswith("[Unclassified]") for k in blocked_rules):
        overall = "FAIL"
    elif statuses == {"NO_EVIDENCE"}:
        overall = "NO_EVIDENCE"
    elif "NO_EVIDENCE" in statuses:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    top_blocked = sorted(blocked_rules.items(), key=lambda x: -x[1])[:8]
    is_heartbeat = (now.hour == 2 and now.minute < 30)

    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "window_hours": hours,
        "cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "files_scanned": files,
        "lines_scanned": lines,
        "overall": overall,
        "gates": gates,
        "top_blocked_rules": top_blocked,
        "is_heartbeat": is_heartbeat,
    }


def render_markdown(report: dict) -> str:
    gates = report.get("gates", [])
    failing_gates = [
        g for g in gates
        if g["fail_hits"] > 0 or g.get("remediation_hits", 0) > 0
    ]
    total_violations = sum(g["fail_hits"] for g in gates)
    has_unclassified = any(r[0].startswith("[Unclassified]") for r in report.get("top_blocked_rules", []))
    if total_violations == 0 and not any(
        g.get("remediation_hits", 0) > 0 for g in gates
    ) and not has_unclassified:
        if report.get("is_heartbeat"):
            cutoff = report.get("cutoff", "N/A")
            gen_at = report.get("generated_at", report.get("cutoff", "N/A"))
            files_scanned = report.get("files_scanned", 0)
            lines_scanned = report.get("lines_scanned", 0)
            return (
                f"🛡️ *[FARM GATE COMPLIANCE — 24H HEARTBEAT]* ✅\n"
                f"⏰ Chu kỳ 24h: {cutoff} -> {gen_at}\n"
                f"📁 Đối soát: {files_scanned} log files ({lines_scanned} dòng) — 0 vi phạm.\n"
                f"ℹ️ Hệ thống 10 Gate cơ giới hóa và Hook Guard đang vận hành bình thường."
            )
        return ""
    files_scanned = report.get("files_scanned", 0)
    status_icon = "❌" if total_violations else "⚠️"
    gen_at = report.get("generated_at", report.get("cutoff", "N/A"))
    cutoff = report.get("cutoff", "N/A")
    win_h = report.get("window_hours", 6.0)
    lines_scanned = report.get("lines_scanned", 0)
    overall = report.get("overall", "NO_EVIDENCE")
    lines = [
        f"🛡️ *[FARM GATE COMPLIANCE WATCHDOG — 6H REPORT]* {status_icon}",
        f"⏰ Khung giờ: {cutoff} -> {gen_at} ({win_h:g}h qua)",
        f"📁 Đối soát: {files_scanned} log files ({lines_scanned} dòng)",
        f"🎯 Kết luận: *{overall}*",
        "",
        "📋 *Chi tiết Gate Có Vi Phạm:*",
    ]
    for g in failing_gates:
        icon = "❌" if g["fail_hits"] else "⚠️"
        extra = f", remediation: {g['remediation_hits']}" if g.get("remediation_hits") else ""
        lines.append(f"{icon} *{g['id']} {g['name']}*: {g['status']} (hợp lệ: {g['pass_hits']}, vi phạm: {g['fail_hits']}{extra})")

    top_blocked = report.get("top_blocked_rules", [])
    if top_blocked:
        lines.append("")
        lines.append("🔥 *Top Quy Tắc Bị Chặn:*")
        for i, (rule_name, count) in enumerate(top_blocked, 1):
            lines.append(f"{i}. `{rule_name}`: *{count}* lần")

    return "\n".join(lines)


def send_telegram_alert(message: str, chat_id: str = FARM_ALERT_CHAT_ID) -> bool:
    """Gửi thông báo tới Telegram channel/group Farm Alert."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        cfg_path = Path.home() / "AppData" / "Local" / "hermes" / "config.yaml"
        if cfg_path.exists():
            try:
                import yaml
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    token = cfg.get("telegram", {}).get("bot_token") or cfg.get("telegram_token")
            except Exception:
                pass
    if not token:
        env_path = Path.home() / "AppData" / "Local" / "hermes" / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            except Exception:
                pass

    if not token:
        return False

    try:
        import urllib.request
        import urllib.parse
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        safe_text = message[:4000] if len(message) > 4000 else message
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": safe_text,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"User-Agent": "Taadaa-Gate-Watchdog/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status == 200 and body.get("ok") is True
    except Exception as exc:
        sys.stderr.write(f"[WARN] send_telegram_alert error: {exc}\n")
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=6.0)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--silent-if-empty", action="store_true")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--send-telegram", action="store_true", help="Gửi báo cáo trực tiếp về Telegram Farm Alert (-5373649734)")
    parser.add_argument("--heartbeat", action="store_true", help="Bắt buộc phát xung Heartbeat kể cả khi 0 vi phạm")
    parser.add_argument("--chat-id", default=FARM_ALERT_CHAT_ID)
    args = parser.parse_args(argv)
    if args.hours <= 0:
        parser.error("--hours must be greater than 0")

    report = evaluate(args.root, args.hours)
    try:
        health_dir = Path(str(args.root / 'runtime' / 'cron_health'))
        health_dir.mkdir(parents=True, exist_ok=True)
        ov = report.get('overall')
        h_status = 'NOMINAL' if ov == 'PASS' else ('NO_EVIDENCE' if ov == 'NO_EVIDENCE' else 'ANOMALY')
        (health_dir / 'gate_compliance_watchdog.json').write_text(
            json.dumps({
                'script_name': 'gate_compliance_watchdog',
                'last_end': datetime.now(timezone.utc).isoformat(),
                'status': h_status,
                'anomalies': report.get('top_blocked_rules', [])
            }, indent=2, ensure_ascii=False), encoding='utf-8'
        )
    except Exception:
        pass
    if args.heartbeat:
        report["is_heartbeat"] = True
    if args.silent_if_empty and report["overall"] == "NO_EVIDENCE":
        return 0

    text = (json.dumps(report, indent=2, ensure_ascii=False)
            if args.json else render_markdown(report))
    if not text.strip():
        return 0
    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(text + "\n", encoding="utf-8")
    
    print(text)

    if args.send_telegram:
        sent = send_telegram_alert(text, chat_id=args.chat_id)
        if sent:
            print("[INFO] Báo cáo đã gửi thành công tới Telegram Farm Alert!")
        else:
            print("[WARN] Không thể gửi báo cáo tới Telegram!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
