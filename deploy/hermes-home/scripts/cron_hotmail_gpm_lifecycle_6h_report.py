#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Báo cáo định kỳ 6h tình trạng vòng đời Hotmail -> GPM -> ChatGPT -> Web Pool -> Change Info.
Hỗ trợ cả 2 Farm: Kibe (1-80) và Admin (201-280).
Deliver: telegram:-5373649734 (Farm Alerts)

Kiến trúc:
  Telemetry          -> sự kiện JSON có correlation_id / timestamp / error_class
  load_farm_state    -> đọc file state (fail-safe, phân loại lỗi)
  normalize_profiles -> chuẩn hoá schema profile, phát hiện dữ liệu hỏng
  aggregate_records  -> gom số liệu theo bucket loại trừ lẫn nhau
  collect_omni_pool  -> đọc SQLite OmniRoute (read-only, từng truy vấn độc lập)
  render_report      -> định dạng báo cáo văn bản
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import uuid
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

KIBE_STATE_PATH = Path("D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json")
ADMIN_STATE_PATH = Path("D:/Taadaa/runtime/admin/cron-state/batch_gpm_5profiles_supervisor_state.json")
PREV_SNAPSHOT_PATH = Path(os.environ.get('HOTMAIL_LIFECYCLE_PREV_SNAPSHOT', r'D:\Taadaa\runtime\kibe\cron-state\hotmail_gpm_lifecycle_last_snapshot.json'))
DB_PATH = Path(os.environ.get("OMNI_DB_PATH", "C:/Users/Kibe/.omniroute/storage.sqlite"))
ROUTER9_DB_PATH = Path(os.environ.get("ROUTER9_DB_PATH", r"C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite"))

STAGE_HOTMAIL_LOGIN = "HOTMAIL_LOGIN"
STAGE_CHATGPT_REG = "CHATGPT_REG"
STAGE_WAIT_7D = "WAIT_7D"
STAGE_CHANGE_INFO = "CHANGE_INFO"
STAGE_DONE = "DONE"
STAGE_BLOCKED = "BLOCKED"
STAGE_UNKNOWN = "UNKNOWN"

ACTIVE_STAGES = (STAGE_HOTMAIL_LOGIN, STAGE_CHATGPT_REG, STAGE_WAIT_7D, STAGE_CHANGE_INFO)
BUCKETS = ACTIVE_STAGES + (STAGE_DONE, STAGE_BLOCKED, STAGE_UNKNOWN)
POST_LOGIN_STAGES = frozenset({STAGE_CHATGPT_REG, STAGE_WAIT_7D, STAGE_CHANGE_INFO, STAGE_DONE})
FAILURE_STATES = frozenset({"BLOCKED", "FAILED", "ERROR", "QUARANTINE"})
REGISTRATION_VOID_STAGES = frozenset({"BLOCKED", "FAILED"})

FARM_LABELS = {"kibe": "Kibe", "admin": "Admin"}
SCHEMA_SAMPLE_LIMIT = 5


# ── Telemetry ────────────────────────────────────────────────────────────────

class Telemetry:
    """Phát sự kiện JSON một dòng ra stderr và giữ lại để tổng hợp."""

    def __init__(self, correlation_id: str | None = None, stream: Any = None) -> None:
        self.correlation_id = correlation_id or uuid.uuid4().hex[:12]
        self.events: list[dict[str, Any]] = []
        self.stream = stream if stream is not None else sys.stderr

    def emit(self, event: str, *, level: str = "info", error_class: str | None = None, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self.correlation_id,
            "level": level,
        }
        if error_class:
            record["error_class"] = error_class
        record.update(fields)
        self.events.append(record)
        print(json.dumps(record, ensure_ascii=False, default=str), file=self.stream)
        return record

    def warnings(self) -> list[dict[str, Any]]:
        return [e for e in self.events if e.get("level") in {"warning", "error"}]

    def error_classes(self) -> list[str]:
        return sorted({e["error_class"] for e in self.warnings() if e.get("error_class")})


def classify_sqlite_error(exc: BaseException) -> str:
    msg = str(exc).lower()
    if "no such table" in msg:
        return "DB_MISSING_TABLE"
    if "no such column" in msg:
        return "DB_MISSING_COLUMN"
    if "unable to open" in msg:
        return "DB_OPEN_FAILED"
    if "locked" in msg or "busy" in msg:
        return "DB_LOCKED"
    if "malformed" in msg or "not a database" in msg:
        return "DB_CORRUPT"
    return "DB_ERROR"


# ── Parsing helpers ──────────────────────────────────────────────────────────

def _parse_time(s: Any) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hours_ago(dt: datetime | None, now: datetime) -> float | None:
    if dt is None:
        return None
    return (now - dt).total_seconds() / 3600


def _pct(part: int, total: int) -> float:
    return part / max(1, total) * 100


def _token(value: Any) -> tuple[str, bool]:
    """Trả về (token viết hoa, hợp lệ). Giá trị None/rỗng hợp lệ; kiểu khác str là không hợp lệ."""
    if value is None:
        return "", True
    if isinstance(value, str):
        return value.strip().upper(), True
    return "", False


# ── State loading ────────────────────────────────────────────────────────────

def load_farm_state(path: Path, telemetry: Telemetry, farm: str = "") -> dict[str, Any]:
    """Đọc dict profile thô từ file state. Không bao giờ raise; mọi lỗi đều thành sự kiện telemetry."""
    started = time.perf_counter()
    duplicate_keys: list[str] = []

    def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _ in pairs:
            if key in seen:
                duplicate_keys.append(key)
            seen.add(key)
        return dict(pairs)

    def _elapsed() -> float:
        return round((time.perf_counter() - started) * 1000, 2)

    if not path.exists():
        telemetry.emit("state_missing", level="warning", error_class="STATE_NOT_FOUND",
                       farm=farm, path=str(path), duration_ms=_elapsed())
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs_hook)
    except json.JSONDecodeError as exc:
        telemetry.emit("state_parse_warning", level="warning", error_class="STATE_INVALID_JSON",
                       farm=farm, path=str(path), error=str(exc), duration_ms=_elapsed())
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        telemetry.emit("state_parse_warning", level="warning", error_class="STATE_IO_ERROR",
                       farm=farm, path=str(path), error=str(exc), duration_ms=_elapsed())
        return {}

    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, dict):
        telemetry.emit("state_parse_warning", level="warning", error_class="STATE_SCHEMA_INVALID",
                       farm=farm, path=str(path), duration_ms=_elapsed(),
                       error="top-level phải là object chứa 'profiles' là object")
        return {}

    if duplicate_keys:
        telemetry.emit("duplicate_json_keys", level="warning", error_class="STATE_DUPLICATE_KEYS",
                       farm=farm, path=str(path), count=len(duplicate_keys),
                       sample=duplicate_keys[:SCHEMA_SAMPLE_LIMIT])
    telemetry.emit("state_loaded", farm=farm, path=str(path), profiles=len(profiles), duration_ms=_elapsed())
    return profiles


def normalize_profiles(raw_profiles: dict[str, Any], telemetry: Telemetry, farm: str = "",
                       now: datetime | None = None) -> list[dict[str, Any]]:
    """Chuẩn hoá từng profile; profile hỏng vẫn được đếm (bucket UNKNOWN) thay vì bị bỏ qua."""
    now = now or datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []
    issues: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}

    def _flag(issue: str, key: str) -> None:
        issues[issue] += 1
        bucket = samples.setdefault(issue, [])
        if len(bucket) < SCHEMA_SAMPLE_LIMIT:
            bucket.append(key)

    for raw_key, raw in raw_profiles.items():
        key = str(raw_key)
        if not isinstance(raw, dict):
            _flag("non_dict_profile", key)
            raw = {}

        stage, stage_ok = _token(raw.get("stage"))
        status, status_ok = _token(raw.get("status"))
        if not stage_ok:
            _flag("invalid_stage_type", key)
        if not status_ok:
            _flag("invalid_status_type", key)

        has_login = _has_valid_timestamp(raw, "hotmail_login_at", key, _flag)
        reg_ok = _has_valid_timestamp(raw, "chatgpt_registered_at", key, _flag)
        has_chatgpt = raw.get("has_chatgpt") is True or reg_ok
        has_tiktok = bool(raw.get("has_tiktok") or (raw.get("username") and raw.get("password")))
        anchor = _parse_time(raw.get("hotmail_login_at") or raw.get("codex_oauth_at") or raw.get("chatgpt_registered_at"))
        matured_7d = anchor is not None and now - anchor >= timedelta(days=7)
        retry_count = raw.get("login_retry_count")
        quarantine = status == "QUARANTINE" or (
            isinstance(retry_count, int) and not isinstance(retry_count, bool) and retry_count >= 3
        )

        failed = status in FAILURE_STATES or stage in FAILURE_STATES
        if failed:
            bucket = STAGE_BLOCKED
        elif stage == STAGE_DONE or status == STAGE_DONE:
            bucket = STAGE_DONE
        elif stage in ACTIVE_STAGES:
            bucket = stage
        else:
            bucket = STAGE_UNKNOWN
            if stage_ok and stage:
                _flag("unknown_stage", key)

        records.append({
            "key": key,
            "stage": stage,
            "status": status,
            "bucket": bucket,
            "has_login": has_login,
            "has_chatgpt": has_chatgpt,
            "has_tiktok": has_tiktok,
            "matured_7d": matured_7d,
            "quarantine": quarantine,
        })

    if issues:
        telemetry.emit("profile_schema_warning", level="warning", error_class="PROFILE_SCHEMA_INVALID",
                       farm=farm, issues=dict(issues), samples=samples)
    return records


def _has_valid_timestamp(raw: dict[str, Any], field: str, key: str, flag: Callable[[str, str], None]) -> bool:
    value = raw.get(field)
    if not value:
        return False
    if _parse_time(value) is None:
        flag(f"invalid_timestamp:{field}", key)
        return False
    return True


# ── Aggregation ──────────────────────────────────────────────────────────────

def _is_chatgpt_registered(rec: dict[str, Any]) -> bool:
    """Xác định tài khoản đã đăng ký ChatGPT thành công (has_chatgpt hoặc đã hoàn tất chu kỳ DONE)."""
    return rec.get("stage") not in REGISTRATION_VOID_STAGES and (bool(rec.get("has_chatgpt")) or rec.get("bucket") == STAGE_DONE)


def aggregate_records(records: list[dict[str, Any]], telemetry: Telemetry | None = None,
                      farm: str = "") -> dict[str, Any]:
    """Mỗi profile rơi vào đúng một bucket nên tổng các bucket luôn bằng total."""
    buckets = {name: 0 for name in BUCKETS}
    login_ok = login_pending = login_blocked = chatgpt_ok = 0
    login_quarantine = matured_7d = missing_tiktok = 0
    done_without_chatgpt: list[str] = []
    for rec in records:
        buckets[rec["bucket"]] += 1
        if rec.get("quarantine"):
            login_quarantine += 1
        if rec["bucket"] == STAGE_WAIT_7D:
            if rec.get("matured_7d"):
                matured_7d += 1
            if not rec.get("has_tiktok"):
                missing_tiktok += 1
        if rec["has_login"] or rec["stage"] in POST_LOGIN_STAGES:
            login_ok += 1
        elif rec["bucket"] == STAGE_HOTMAIL_LOGIN:
            login_pending += 1
        elif rec["bucket"] == STAGE_BLOCKED and rec["stage"] == STAGE_HOTMAIL_LOGIN:
            login_blocked += 1
        if rec["bucket"] == STAGE_DONE and not rec.get("has_chatgpt"):
            done_without_chatgpt.append(rec["key"])
        if _is_chatgpt_registered(rec):
            chatgpt_ok += 1
    if done_without_chatgpt and telemetry is not None:
        telemetry.emit("done_without_chatgpt", level="warning", error_class="DONE_WITHOUT_CHATGPT_REG",
                       farm=farm, count=len(done_without_chatgpt),
                       sample=done_without_chatgpt[:SCHEMA_SAMPLE_LIMIT])
    return {
        "total": len(records),
        "buckets": buckets,
        "login_ok": login_ok,
        "login_pending": login_pending,
        "login_blocked": login_blocked,
        "chatgpt_ok": chatgpt_ok,
        "done_without_chatgpt": len(done_without_chatgpt),
        "wait_7d": buckets[STAGE_WAIT_7D],
        "change_info": buckets[STAGE_CHANGE_INFO],
        "done": buckets[STAGE_DONE],
        "blocked": buckets[STAGE_BLOCKED],
        "login_quarantine": login_quarantine,
        "matured_7d": matured_7d,
        "missing_tiktok": missing_tiktok,
    }


METRIC_KEYS = ("total", "login_ok", "login_pending", "login_blocked", "chatgpt_ok", "done_without_chatgpt", "wait_7d", "change_info", "done", "blocked")
EXTRA_COUNT_KEYS = ("login_quarantine", "matured_7d", "missing_tiktok")


def merge_metrics(*farms: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {"buckets": {name: 0 for name in BUCKETS}}
    for key in METRIC_KEYS + EXTRA_COUNT_KEYS:
        merged[key] = sum(f[key] for f in farms)
    for name in BUCKETS:
        merged["buckets"][name] = sum(f["buckets"][name] for f in farms)
    return merged


RECENT_KEYS = ("total_processed", "new_done", "new_chatgpt", "new_login", "failed_login", "ready_change")
RECENT_EVENT_BY_STAGE = {STAGE_HOTMAIL_LOGIN: "new_login", STAGE_CHATGPT_REG: "new_chatgpt",
                         STAGE_WAIT_7D: "ready_change", STAGE_CHANGE_INFO: "new_done", STAGE_DONE: "new_done"}
FAILED_RESULT_STATUSES = frozenset({"FAILED", "ERROR", "BLOCKED", "QUARANTINE"})


def aggregate_recent_activity(raw_profiles: dict[str, Any], cutoff: datetime,
                              now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    recent = {key: 0 for key in RECENT_KEYS}
    for raw in raw_profiles.values():
        if not isinstance(raw, dict):
            continue
        history = raw.get("history")
        hist_timestamps: set[str] = set()
        for entry in history if isinstance(history, list) else []:
            if not isinstance(entry, dict):
                continue
            at_raw = entry.get("at")
            at = _parse_time(at_raw)
            if at is None or at < cutoff or at > now:
                continue
            if isinstance(at_raw, str):
                hist_timestamps.add(at_raw)
            recent["total_processed"] += 1
            event = RECENT_EVENT_BY_STAGE.get(_token(entry.get("stage"))[0])
            if event:
                recent[event] += 1
        last = raw.get("last_result")
        if not isinstance(last, dict):
            continue
        last_at_raw = last.get("at")
        if isinstance(last_at_raw, str) and last_at_raw in hist_timestamps:
            continue
        at = _parse_time(last_at_raw)
        status = _token(last.get("status"))[0]
        if at is None or at < cutoff or at > now or status not in FAILED_RESULT_STATUSES:
            continue
        recent["total_processed"] += 1
        if _token(last.get("stage"))[0] == STAGE_HOTMAIL_LOGIN:
            recent["failed_login"] += 1
    return recent


def merge_recent_activity(*farms: dict[str, Any]) -> dict[str, Any]:
    return {key: sum(int(f.get(key, 0)) for f in farms if isinstance(f, dict)) for key in RECENT_KEYS}


# ── OmniRoute pool (SQLite)────────────────────────────────────────────────

def _coerce_active(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    if isinstance(value, str) and value.strip() in {"0", "1"}:
        return int(value.strip())
    return None


def _readonly_uri(path: Path) -> str:
    return path.resolve().as_uri() + "?mode=ro"


def _read_connections(conn: sqlite3.Connection, pool: dict[str, Any], telemetry: Telemetry) -> None:
    started = time.perf_counter()
    try:
        rows = conn.execute("SELECT is_active FROM provider_connections WHERE provider='chatgpt-web'").fetchall()
    except sqlite3.Error as exc:
        telemetry.emit("db_parse_warning", level="warning", error_class=classify_sqlite_error(exc),
                       path=str(DB_PATH), query="provider_connections", error=str(exc))
        return
    states = [_coerce_active(r[0]) for r in rows]
    pool["connections_ok"] = True
    pool["total"] = len(rows)
    pool["active"] = states.count(1)
    pool["soaking"] = states.count(0)
    pool["unknown"] = states.count(None)
    if pool["unknown"]:
        telemetry.emit("db_row_warning", level="warning", error_class="DB_INVALID_IS_ACTIVE",
                       query="provider_connections", count=pool["unknown"])
    telemetry.emit("db_query_ok", query="provider_connections", rows=len(rows),
                   duration_ms=round((time.perf_counter() - started) * 1000, 2))


def _read_combo(conn: sqlite3.Connection, pool: dict[str, Any], telemetry: Telemetry) -> None:
    started = time.perf_counter()
    try:
        rows = conn.execute("SELECT data FROM combos WHERE name='chatgpt-web-pool'").fetchall()
    except sqlite3.Error as exc:
        telemetry.emit("db_parse_warning", level="warning", error_class=classify_sqlite_error(exc),
                       path=str(DB_PATH), query="combos", error=str(exc))
        return
    if not rows:
        pool["combo_ok"] = True
        telemetry.emit("combo_missing", level="warning", error_class="COMBO_NOT_FOUND", query="combos")
        return
    if len(rows) > 1:
        telemetry.emit("combo_duplicate", level="warning", error_class="COMBO_DUPLICATE_ROWS",
                       query="combos", rows=len(rows))
    try:
        combo = json.loads(rows[0][0])
    except (TypeError, ValueError) as exc:
        telemetry.emit("combo_parse_warning", level="warning", error_class="COMBO_INVALID_JSON",
                       query="combos", error=str(exc))
        return
    models = combo.get("models") if isinstance(combo, dict) else None
    if not isinstance(models, list):
        telemetry.emit("combo_parse_warning", level="warning", error_class="COMBO_SCHEMA_INVALID",
                       query="combos", error="'models' phải là list trong object combo")
        return
    pool["combo_ok"] = True
    pool["models"] = len(models)
    telemetry.emit("db_query_ok", query="combos", rows=len(rows),
                   duration_ms=round((time.perf_counter() - started) * 1000, 2))


def collect_omni_pool(db_path: Path, telemetry: Telemetry) -> dict[str, Any]:
    pool: dict[str, Any] = {
        "connections_ok": False, "combo_ok": False,
        "total": 0, "active": 0, "soaking": 0, "unknown": 0, "models": 0,
    }
    if not db_path.exists():
        telemetry.emit("db_missing", level="warning", error_class="DB_NOT_FOUND", path=str(db_path))
        return pool
    try:
        conn = sqlite3.connect(_readonly_uri(db_path), uri=True, timeout=5)
    except sqlite3.Error as exc:
        telemetry.emit("db_parse_warning", level="warning", error_class=classify_sqlite_error(exc),
                       path=str(db_path), query="connect", error=str(exc))
        return pool
    with closing(conn):
        _read_connections(conn, pool, telemetry)
        _read_combo(conn, pool, telemetry)
    return pool


def check_ip_cooldown(path: Path, profiles: dict[str, Any], now: datetime) -> dict[str, Any]:
    try:
        ip_h = json.loads(path.read_text(encoding="utf-8")).get("ip_action_history", {})
    except Exception:
        return {"count": 0, "ports": 0, "min_h": 0.0}
    cd_accs, cd_ports, min_rem = 0, set(), None
    for p in profiles.values():
        if isinstance(p, dict) and p.get("stage") == "HOTMAIL_LOGIN" and p.get("status") == "PENDING":
            port = str(p.get("proxy_port") or "")
            ts = _parse_time((ip_h.get(port) or {}).get("HOTMAIL_LOGIN"))
            if ts and (now - ts).total_seconds() < 86400:
                cd_accs, min_rem = cd_accs + 1, min(min_rem or 86400, 86400 - (now - ts).total_seconds())
                cd_ports.add(port)
    return {"count": cd_accs, "ports": len(cd_ports), "min_h": round(min_rem / 3600, 1) if min_rem else 0.0}


# ── Snapshot & rendering ─────────────────────────────────────────────────────

def collect_snapshot(telemetry: Telemetry, now: datetime | None = None, window_hours: float = 6.0) -> dict[str, Any]:
    started = time.perf_counter()
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    farm_metrics: dict[str, dict[str, Any]] = {}
    farm_recent: dict[str, dict[str, Any]] = {}
    farm_keys: dict[str, set[str]] = {}
    farm_cooldown: dict[str, dict[str, Any]] = {}
    for farm, path in (("kibe", KIBE_STATE_PATH), ("admin", ADMIN_STATE_PATH)):
        raw = load_farm_state(path, telemetry, farm)
        farm_keys[farm] = set(raw)
        farm_metrics[farm] = aggregate_records(normalize_profiles(raw, telemetry, farm, now), telemetry, farm)
        farm_recent[farm] = aggregate_recent_activity(raw, cutoff, now)
        farm_cooldown[farm] = check_ip_cooldown(path, raw, now)

    overlap = farm_keys["kibe"] & farm_keys["admin"]
    if overlap:
        telemetry.emit("duplicate_profile_keys", level="warning", error_class="PROFILE_KEY_COLLISION",
                       count=len(overlap), sample=sorted(overlap)[:SCHEMA_SAMPLE_LIMIT])

    totals = merge_metrics(farm_metrics["kibe"], farm_metrics["admin"])
    recent = merge_recent_activity(farm_recent["kibe"], farm_recent["admin"])
    pool = collect_omni_pool(DB_PATH, telemetry)

    warnings = telemetry.warnings()
    snapshot = {
        "correlation_id": telemetry.correlation_id,
        "timestamp": now.isoformat(),
        "farms": farm_metrics,
        "farm_recent": farm_recent,
        "recent": recent,
        "totals": totals,
        "pool": pool,
        "ip_cooldown": farm_cooldown,
        "warning_count": len(warnings),
        "error_classes": telemetry.error_classes(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }
    telemetry.emit(
        "lifecycle_report_snapshot",
        level="warning" if warnings else "info",
        status="degraded" if warnings else "ok",
        total=totals["total"],
        buckets=totals["buckets"],
        login_ok=totals["login_ok"],
        chatgpt_ok=totals["chatgpt_ok"],
        done_without_chatgpt=totals["done_without_chatgpt"],
        pool_connections=pool["total"],
        pool_models=pool["models"],
        warning_count=len(warnings),
        error_classes=snapshot["error_classes"],
        duration_ms=snapshot["duration_ms"],
    )
    return snapshot


def _fmt_delta(curr: int, prev: Any) -> str:
    if isinstance(prev, int) and not isinstance(prev, bool) and prev > 0:
        return f' [{curr - prev:+d}]'
    return ''


def _has_metric_ints(metrics: Any) -> bool:
    return isinstance(metrics, dict) and all(
        isinstance(metrics.get(k), int) and not isinstance(metrics.get(k), bool) for k in METRIC_KEYS
    )


def _is_valid_snapshot_metrics(data: dict[str, Any]) -> bool:
    if not _has_metric_ints(data.get("totals")):
        return False
    farms = data.get("farms")
    return isinstance(farms, dict) and all(_has_metric_ints(farms.get(farm)) for farm in FARM_LABELS)


def load_previous_snapshot(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    timestamp = _parse_time(data.get("timestamp"))
    if timestamp is None or timestamp > datetime.now(timezone.utc):
        return None
    if not _is_valid_snapshot_metrics(data):
        return None
    return data


def save_current_snapshot(path: Path, snapshot: dict[str, Any], telemetry: Telemetry | None = None) -> None:
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
        tmp.write_text(json.dumps(snapshot, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        if telemetry is None:
            raise
        telemetry.emit("snapshot_save_error", level="warning", error_class="SNAPSHOT_IO_ERROR",
                       path=str(path), error=str(exc))


def render_report(snapshot: dict[str, Any], prev_snapshot: dict[str, Any] | None = None) -> list[str]:
    kibe, admin, t = snapshot["farms"]["kibe"], snapshot["farms"]["admin"], snapshot["totals"]
    pool = snapshot["pool"]
    total = t["total"]
    if not (prev_snapshot and _is_valid_snapshot_metrics(prev_snapshot)):
        prev_snapshot = None
    prev = prev_snapshot or {}
    pt = prev.get("totals", {})
    pk = prev.get("farms", {}).get("kibe", {})
    pa = prev.get("farms", {}).get("admin", {})

    lines = [
        "📊 [BÁO CÁO 6H: VÒNG ĐỜI HOTMAIL -> GPM -> CHATGPT TOÀN FARM]",
        f"• Tổng số tài khoản trong Queue: {total} (Kibe: {kibe['total']} | Admin: {admin['total']})",
        "",
        "🔑 TIẾN ĐỘ HOTMAIL LOGIN:",
        f"  • Toàn Farm Đã Login Hotmail : {t['login_ok']}/{total} ({_pct(t['login_ok'], total):.1f}%){_fmt_delta(t['login_ok'], pt.get('login_ok'))}",
        f"    - Farm Kibe (M1-80)        : {kibe['login_ok']}/{kibe['total']}{_fmt_delta(kibe['login_ok'], pk.get('login_ok'))}",
        f"    - Farm Admin (M201-280)    : {admin['login_ok']}/{admin['total']}{_fmt_delta(admin['login_ok'], pa.get('login_ok'))}",
        f"  • Đang Chờ Login (PENDING)   : {t['login_pending']}{_fmt_delta(t['login_pending'], pt.get('login_pending'))} (Kibe: {kibe['login_pending']} | Admin: {admin['login_pending']})",
        f"  • Đang Cooldown 48h (BLOCKED): {t['login_blocked']}{_fmt_delta(t['login_blocked'], pt.get('login_blocked'))} (Kibe: {kibe['login_blocked']} | Admin: {admin['login_blocked']})",
        "",
        "🤖 TIẾN ĐỘ CHATGPT REG:",
        f"  • Toàn Farm Đã Reg Thành Công : {t['chatgpt_ok']}/{total} ({_pct(t['chatgpt_ok'], total):.1f}%){_fmt_delta(t['chatgpt_ok'], pt.get('chatgpt_ok'))}",
        f"    - Farm Kibe (M1-80)        : {kibe['chatgpt_ok']}/{kibe['total']}{_fmt_delta(kibe['chatgpt_ok'], pk.get('chatgpt_ok'))}",
        f"    - Farm Admin (M201-280)    : {admin['chatgpt_ok']}/{admin['total']}{_fmt_delta(admin['chatgpt_ok'], pa.get('chatgpt_ok'))}",
        "",
        "🔐 TIẾN ĐỘ CHANGE HOTMAIL & BẢO MẬT:",
        f"  • Đã Hoàn Tất Đổi Pass (DONE) : {t['done']}/{total} ({_pct(t['done'], total):.1f}%){_fmt_delta(t['done'], pt.get('done'))}",
        f"    - Farm Kibe (M1-80)        : {kibe['done']}/{kibe['total']}{_fmt_delta(kibe['done'], pk.get('done'))}",
        f"    - Farm Admin (M201-280)    : {admin['done']}/{admin['total']}{_fmt_delta(admin['done'], pa.get('done'))}",
        f"  • Hàng đợi đổi pass (CHANGE_INFO): {t['change_info']} (Kibe: {kibe['change_info']} | Admin: {admin['change_info']})",
        f"  • Đang ngâm 7 ngày chờ đổi (WAIT_7D): {t['wait_7d']}{_fmt_delta(t['wait_7d'], pt.get('wait_7d'))} (Kibe: {kibe['wait_7d']} | Admin: {admin['wait_7d']})",
        f"    - Đã đủ 7 ngày ngâm: {t['matured_7d']} (Kibe: {kibe['matured_7d']} | Admin: {admin['matured_7d']})",
        f"    - Thiếu thông tin TikTok: {t['missing_tiktok']} (Kibe: {kibe['missing_tiktok']} | Admin: {admin['missing_tiktok']})",
    ]
    cd = snapshot.get("ip_cooldown") or {}
    k_cd, a_cd = cd.get("kibe", {}), cd.get("admin", {})
    tot_cd = k_cd.get("count", 0) + a_cd.get("count", 0)
    if tot_cd > 0:
        cd_parts = [f"{lbl}: {d['count']}/{d['ports']} cổng (mở sau ~{d['min_h']}h)" for lbl, d in (("Kibe", k_cd), ("Admin", a_cd)) if d.get("count")]
        idx_b = next((i for i, l in enumerate(lines) if "Đang Cooldown 48h" in l), len(lines))
        lines.insert(idx_b, f"    - Chờ giãn cách IP 24h     : {tot_cd} ({' | '.join(cd_parts)})")

    if prev_snapshot:
        lines.insert(2, f"• So sánh với lần trước: {prev_snapshot.get('timestamp', 'không rõ')}")
    if t["blocked"] > 0:
        lines.append(f"  ⚠️ Lỗi / Kẹt cần cứu (BLOCKED): {t['blocked']} (Kibe: {kibe['blocked']} | Admin: {admin['blocked']})")
    if t["login_quarantine"] > 0:
        lines.append(f"    - Trong đó QUARANTINE (chết cứng >= 3 lần): {t['login_quarantine']} nick "
                     f"(Kibe: {kibe['login_quarantine']}, Admin: {admin['login_quarantine']})")
    unknown = t["buckets"][STAGE_UNKNOWN]
    if unknown > 0:
        lines.append(f"  ⚠️ Stage không nhận diện (UNKNOWN): {unknown} (Kibe: {kibe['buckets'][STAGE_UNKNOWN]} | Admin: {admin['buckets'][STAGE_UNKNOWN]})")

    lines += ["", "⚡ BIẾN ĐỘNG TRONG 6H QUA:"]
    recent = snapshot["recent"]
    if recent["total_processed"] == 0:
        lines.append("  • Không có biến động nào trong 6h qua (farm idle).")
    else:
        kibe_recent, admin_recent = snapshot["farm_recent"]["kibe"], snapshot["farm_recent"]["admin"]
        lines += [
            f"  • Tổng số tài khoản xử lý : {recent['total_processed']} (Kibe: {kibe_recent['total_processed']} | Admin: {admin_recent['total_processed']})",
            f"  • Login Hotmail thành công: {recent['new_login']}",
            f"  • Login Hotmail lỗi       : {recent['failed_login']}",
            f"  • Reg ChatGPT thành công  : {recent['new_chatgpt']}",
            f"  • Sẵn sàng đổi info (WAIT_7D -> CHANGE_INFO): {recent['ready_change']}",
            f"  • Hoàn tất DONE mới       : {recent['new_done']}",
        ]
        if kibe_recent["total_processed"] == 0 and k_cd.get("count", 0) > 0:
            lines.append(f"    * Ghi chú Kibe: 0 biến động do {k_cd['ports']} cổng MobiProxy đang giữ giãn cách 24h (mở dần sau ~{k_cd['min_h']}h).")

    lines += ["", "🌐 CHATGPT WEB POOL (OMNIRoute :20129):"]
    if pool["connections_ok"]:
        suffix = f" | {pool['unknown']} Không rõ" if pool["unknown"] else ""
        lines.append(f"  ✅ Tổng kết nối Web          : {pool['total']} connections ({pool['active']} Active | {pool['soaking']} Soaking 48h{suffix})")
    else:
        lines.append("  ⚠️ Tổng kết nối Web          : không đọc được OmniRoute DB")
    if pool["combo_ok"]:
        lines.append(f"  🎯 Models trong Web Pool      : {pool['models']} accounts (Round-Robin 0đ)")
    else:
        lines.append("  ⚠️ Models trong Web Pool      : không đọc được combo chatgpt-web-pool")

    if snapshot["warning_count"]:
        lines += ["", f"⚠️ Dữ liệu có {snapshot['warning_count']} cảnh báo ({', '.join(snapshot['error_classes'])}) "
                      f"- correlation_id={snapshot['correlation_id']}"]
    return lines


def main() -> int:
    telemetry = Telemetry()
    snapshot = collect_snapshot(telemetry)
    prev_snapshot = load_previous_snapshot(PREV_SNAPSHOT_PATH)
    for line in render_report(snapshot, prev_snapshot):
        print(line)
    save_current_snapshot(PREV_SNAPSHOT_PATH, snapshot, telemetry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
