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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KIBE_STATE_PATH = Path("D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json")
ADMIN_STATE_PATH = Path("D:/Taadaa/runtime/admin/cron-state/batch_gpm_5profiles_supervisor_state.json")
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


def normalize_profiles(raw_profiles: dict[str, Any], telemetry: Telemetry, farm: str = "") -> list[dict[str, Any]]:
    """Chuẩn hoá từng profile; profile hỏng vẫn được đếm (bucket UNKNOWN) thay vì bị bỏ qua."""
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
        has_chatgpt = _has_valid_timestamp(raw, "chatgpt_registered_at", key, _flag)

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
        })

    if issues:
        telemetry.emit("profile_schema_warning", level="warning", error_class="PROFILE_SCHEMA_INVALID",
                       farm=farm, issues=dict(issues), samples=samples)
    return records


def _has_valid_timestamp(raw: dict[str, Any], field: str, key: str, flag) -> bool:
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
    done_without_chatgpt: list[str] = []
    for rec in records:
        buckets[rec["bucket"]] += 1
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
    }


def merge_metrics(*farms: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {"buckets": {name: 0 for name in BUCKETS}}
    for key in ("total", "login_ok", "login_pending", "login_blocked", "chatgpt_ok",
                "done_without_chatgpt", "wait_7d", "change_info", "done", "blocked"):
        merged[key] = sum(f[key] for f in farms)
    for name in BUCKETS:
        merged["buckets"][name] = sum(f["buckets"][name] for f in farms)
    return merged


# ── OmniRoute pool (SQLite) ──────────────────────────────────────────────────

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


# ── Snapshot & rendering ─────────────────────────────────────────────────────

def collect_snapshot(telemetry: Telemetry) -> dict[str, Any]:
    started = time.perf_counter()
    now = datetime.now(timezone.utc)

    farm_metrics: dict[str, dict[str, Any]] = {}
    farm_keys: dict[str, set[str]] = {}
    for farm, path in (("kibe", KIBE_STATE_PATH), ("admin", ADMIN_STATE_PATH)):
        raw = load_farm_state(path, telemetry, farm)
        farm_keys[farm] = set(raw)
        farm_metrics[farm] = aggregate_records(normalize_profiles(raw, telemetry, farm), telemetry, farm)

    overlap = farm_keys["kibe"] & farm_keys["admin"]
    if overlap:
        telemetry.emit("duplicate_profile_keys", level="warning", error_class="PROFILE_KEY_COLLISION",
                       count=len(overlap), sample=sorted(overlap)[:SCHEMA_SAMPLE_LIMIT])

    totals = merge_metrics(farm_metrics["kibe"], farm_metrics["admin"])
    pool = collect_omni_pool(DB_PATH, telemetry)

    warnings = telemetry.warnings()
    snapshot = {
        "correlation_id": telemetry.correlation_id,
        "timestamp": now.isoformat(),
        "farms": farm_metrics,
        "totals": totals,
        "pool": pool,
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


def render_report(snapshot: dict[str, Any]) -> list[str]:
    kibe, admin, t = snapshot["farms"]["kibe"], snapshot["farms"]["admin"], snapshot["totals"]
    pool = snapshot["pool"]
    total = t["total"]

    lines = [
        "📊 [BÁO CÁO 6H: VÒNG ĐỜI HOTMAIL -> GPM -> CHATGPT TOÀN FARM]",
        f"• Tổng số tài khoản trong Queue: {total} (Kibe: {kibe['total']} | Admin: {admin['total']})",
        "",
        "🔑 TIẾN ĐỘ HOTMAIL LOGIN:",
        f"  • Toàn Farm Đã Login Hotmail : {t['login_ok']}/{total} ({_pct(t['login_ok'], total):.1f}%)",
        f"    - Farm Kibe (M1-80)        : {kibe['login_ok']}/{kibe['total']}",
        f"    - Farm Admin (M201-280)    : {admin['login_ok']}/{admin['total']}",
        f"  • Đang Chờ Login (PENDING)   : {t['login_pending']} (Kibe: {kibe['login_pending']} | Admin: {admin['login_pending']})",
        f"  • Đang Cooldown 48h (BLOCKED): {t['login_blocked']} (Kibe: {kibe['login_blocked']} | Admin: {admin['login_blocked']})",
        "",
        "🤖 TIẾN ĐỘ CHATGPT REG:",
        f"  • Toàn Farm Đã Reg Thành Công : {t['chatgpt_ok']}/{total} ({_pct(t['chatgpt_ok'], total):.1f}%)",
        f"    - Farm Kibe (M1-80)        : {kibe['chatgpt_ok']}/{kibe['total']}",
        f"    - Farm Admin (M201-280)    : {admin['chatgpt_ok']}/{admin['total']}",
        "",
        "🔐 TIẾN ĐỘ CHANGE HOTMAIL & BẢO MẬT:",
        f"  • Đã Hoàn Tất Đổi Pass (DONE) : {t['done']}/{total} ({_pct(t['done'], total):.1f}%)",
        f"    - Farm Kibe (M1-80)        : {kibe['done']}/{kibe['total']}",
        f"    - Farm Admin (M201-280)    : {admin['done']}/{admin['total']}",
        f"  • Hàng đợi đổi pass (CHANGE_INFO): {t['change_info']} (Kibe: {kibe['change_info']} | Admin: {admin['change_info']})",
        f"  • Đang ngâm 7 ngày chờ đổi (WAIT_7D): {t['wait_7d']} (Kibe: {kibe['wait_7d']} | Admin: {admin['wait_7d']})",
    ]
    if t["blocked"] > 0:
        lines.append(f"  ⚠️ Lỗi / Kẹt cần cứu (BLOCKED): {t['blocked']} (Kibe: {kibe['blocked']} | Admin: {admin['blocked']})")
    unknown = t["buckets"][STAGE_UNKNOWN]
    if unknown > 0:
        lines.append(f"  ⚠️ Stage không nhận diện (UNKNOWN): {unknown} (Kibe: {kibe['buckets'][STAGE_UNKNOWN]} | Admin: {admin['buckets'][STAGE_UNKNOWN]})")

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
    for line in render_report(snapshot):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
