#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sol_payload_guard.py — Kiểm soát và bảo vệ kích thước payload gửi Sol High (ChatGPT-web :20129).

Thiết kế & Review bởi Claude Code CLI (Lead System Architect).
Hai lớp phòng thủ vật lý:
  - Lớp 1 (Budgeter / Smart Truncator): Cắt tỉa thông minh theo thứ tự ưu tiên P0/P1/P2/Noise.
  - Lớp 2 (Transport Guard): Serialize UTF-8 (ensure_ascii=False), chặn cứng mọi payload > 37.952 Bytes trước khi chạm HTTP.
  - Cầu nối: fit_and_enforce() tự động hạ bậc budget nếu serialize JSON phình ký tự.
"""

from __future__ import annotations

import os
import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

# ─── CÁC NGƯỠNG AN TOÀN VẬT LÝ (SAFETY MARGINS) ──────────────────────────────
def _parse_env_int(key: str, default: int, min_limit: int, max_limit: int) -> int:
    """Đọc biến môi trường an toàn, kẹp chặt trong khoảng [min_limit, max_limit]."""
    try:
        val = os.getenv(key)
        res = int(val) if val is not None else default
        return max(min_limit, min(res, max_limit))
    except Exception:
        return default

# Trần cứng tuyệt đối bất biến (viết cứng trong mã nguồn)
ABSOLUTE_CEILING_BYTES: int = 40_000
ABSOLUTE_MIN_RESERVE_BYTES: int = 1_024

SOL_HARD_MAX_BYTES: int = _parse_env_int("SOL_HARD_MAX_BYTES", 40_000, min_limit=10_000, max_limit=ABSOLUTE_CEILING_BYTES)
SOL_WRAPPER_RESERVE: int = _parse_env_int("SOL_WRAPPER_RESERVE", 2_048, min_limit=ABSOLUTE_MIN_RESERVE_BYTES, max_limit=8_192)
MAX_RAW_READ_BYTES: int = _parse_env_int("MAX_RAW_READ_BYTES", 2_000_000, min_limit=100_000, max_limit=10_000_000)

CALCULATED_MAX_ALLOWED: int = min(SOL_HARD_MAX_BYTES - SOL_WRAPPER_RESERVE, ABSOLUTE_CEILING_BYTES - ABSOLUTE_MIN_RESERVE_BYTES)
SOL_TARGET_BYTES: int = _parse_env_int("SOL_TARGET_BYTES", 32_768, min_limit=4_096, max_limit=min(36_000, CALCULATED_MAX_ALLOWED))

if SOL_WRAPPER_RESERVE >= SOL_HARD_MAX_BYTES:
    raise RuntimeError(
        f"Lỗi cấu hình Sol Payload Guard: SOL_WRAPPER_RESERVE ({SOL_WRAPPER_RESERVE}) >= SOL_HARD_MAX_BYTES ({SOL_HARD_MAX_BYTES})"
    )

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07\x1b]*[\x07\x1b\\]")

# Bỏ \\w* để triệt tiêu hoàn toàn nguy cơ ReDoS bậc 2. Không có backtracking.
ANCHOR_PATTERN = re.compile(
    r"Traceback|(?:Error|Exception)\b(?!\s*=\s*0)|\bFAIL(?:ED|URE)?\b|\bFATAL\b|\bpanic\b|"
    r"\bTimeout\b|Caused by:|npm ERR!|^E\s",
    re.IGNORECASE
)

NOISE_PATTERN = re.compile(
    r"(\.lock$|lock\.json$|\.min\.(js|css)$|^dist/|^build/|\.snap$|\.(png|jpg|webp|apk|sqlite|db)$)",
    re.IGNORECASE
)


class PayloadTooLarge(Exception):
    """Ngoại lệ khi payload vượt quá trần cứng cho phép."""
    pass


def sanitize_str(s: str) -> str:
    """Khử triệt để lone surrogates và control chars xấu chống UnicodeEncodeError."""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    return clean.encode("utf-8", errors="replace").decode("utf-8")


def nbytes(s: str) -> int:
    """Tính chính xác số bytes UTF-8 của chuỗi sau khi khử surrogate."""
    return len(s.encode("utf-8", errors="replace"))


def sha256_full(s: str) -> str:
    """Băm SHA-256 đầy đủ 64 ký tự hex cho audit trail."""
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def _sanitize_obj(obj: Any) -> Any:
    """Đệ quy khử surrogate trong dictionary/list trước khi serialize."""
    if isinstance(obj, str):
        return sanitize_str(obj)
    elif isinstance(obj, dict):
        return {sanitize_str(str(k)): _sanitize_obj(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_obj(item) for item in obj]
    return obj


def serialize(body: Dict[str, Any]) -> bytes:
    """
    Serialize đúng một lần với ensure_ascii=False, allow_nan=False và separators thu gọn.
    Bảo toàn ký tự tiếng Việt (2-3 bytes) thay vì bị phình thành \\uXXXX (6 bytes).
    """
    clean_body = _sanitize_obj(body)
    return json.dumps(
        clean_body,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":")
    ).encode("utf-8", errors="replace")


def enforce(body: Dict[str, Any]) -> bytes:
    """
    Lớp 2 — Chốt chặn vật lý fail-closed ngay trước khi gửi HTTP.
    Kẹp cứng max_allowed không bao giờ vượt qua (ABSOLUTE_CEILING_BYTES - ABSOLUTE_MIN_RESERVE_BYTES = 38.976 B).
    """
    raw = serialize(body)
    if len(raw) > CALCULATED_MAX_ALLOWED:
        raise PayloadTooLarge(
            f"Payload quá lớn: {len(raw)} Bytes > trần an toàn {CALCULATED_MAX_ALLOWED} Bytes (HARD_MAX={SOL_HARD_MAX_BYTES})"
        )
    return raw


# ─── LỚP 1: CHUẨN HÓA & CẮT TỈA THÔNG MINH (SMART TRUNCATOR) ─────────────────

def normalize_text(text: str) -> str:
    """Chuẩn hóa log text chung: loại ANSI, xử lý carriage return, thống nhất CRLF."""
    if len(text) > MAX_RAW_READ_BYTES:
        half = MAX_RAW_READ_BYTES // 2
        text = text[:half] + "\n… [RAW LOG TRUNCATED: VƯỢT QUÁ TRẦN ĐỌC ĐẦU VÀO] …\n" + text[-half:]

    no_ansi = ANSI_PATTERN.sub("", text)
    lines = []
    for l in no_ansi.replace("\r\n", "\n").split("\n"):
        if "\r" in l:
            l = l.rstrip("\r").split("\r")[-1]
        lines.append(l)
    return sanitize_str("\n".join(lines))


def normalize_diff(diff: str) -> str:
    """Chuẩn hóa diff: bảo toàn khoảng trắng cuối dòng, loại ANSI & CRLF."""
    if len(diff) > MAX_RAW_READ_BYTES:
        half = MAX_RAW_READ_BYTES // 2
        diff = diff[:half] + "\n… [RAW DIFF TRUNCATED: VƯỢT QUÁ TRẦN ĐỌC ĐẦU VÀO] …\n" + diff[-half:]

    no_ansi = ANSI_PATTERN.sub("", diff)
    return sanitize_str(no_ansi.replace("\r\n", "\n"))


def _cap_line_length(line: str, max_line_bytes: int) -> str:
    """Cắt gọn 1 dòng siêu dài trước khi đưa vào head_tail để không làm nghẽn tail."""
    if nbytes(line) <= max_line_bytes:
        return line
    suffix = "… [dòng dài bị cắt]"
    avail = max(16, max_line_bytes - nbytes(suffix) - 2)
    truncated = line.encode("utf-8", errors="replace")[:avail].decode("utf-8", errors="ignore")
    return f"{truncated}{suffix}"


def head_tail(lines: List[str], budget: int, head_ratio: float = 0.6) -> List[str]:
    """Cắt theo ranh giới dòng nguyên vẹn. Tự động xử lý an toàn dòng khổng lồ."""
    if not lines or budget <= 0:
        return []

    max_line_bytes = max(256, min(2048, budget // 8))
    bounded_lines = [_cap_line_length(l, max_line_bytes) for l in lines]

    if len(bounded_lines) == 1:
        single = bounded_lines[0]
        if nbytes(single) <= budget:
            return [single]
        suffix = "… [dòng bị cắt bớt do quá dài]"
        avail = max(16, budget - nbytes(suffix) - 4)
        encoded = single.encode("utf-8", errors="replace")[:avail]
        truncated_str = encoded.decode("utf-8", errors="ignore")
        return [f"{truncated_str}{suffix}"]

    head: List[str] = []
    tail_reversed: List[str] = []
    used: int = 0
    head_budget = int(budget * head_ratio)

    for l in bounded_lines:
        cost = nbytes(l) + 1
        if used + cost > head_budget:
            break
        head.append(l)
        used += cost

    for l in reversed(bounded_lines[len(head):]):
        cost = nbytes(l) + 1
        if used + cost > budget - 64:
            break
        tail_reversed.append(l)
        used += cost

    tail = list(reversed(tail_reversed))
    elided = len(bounded_lines) - len(head) - len(tail)
    if elided > 0:
        return head + [f"… [{elided} dòng bị lược]"] + tail
    return head + tail


@dataclass
class LogDigest:
    text: str
    truncated: bool
    raw_bytes: int
    raw_sha256: str
    elided_lines: int = 0


def focus_log(log: str, budget: int, ctx: int = 4, head: int = 15, tail: int = 40) -> LogDigest:
    """
    Băm sha256 và đo raw_bytes trên chuỗi log GỐC trước khi normalize.
    Kiểm tra ANCHOR_PATTERN trên l[:4096] để phòng thủ triệt để ReDoS.
    """
    raw_bytes = nbytes(log)
    raw_sha = sha256_full(log)

    clean_log = normalize_text(log)
    if nbytes(clean_log) <= budget:
        return LogDigest(
            text=clean_log,
            truncated=False,
            raw_bytes=raw_bytes,
            raw_sha256=raw_sha,
            elided_lines=0
        )

    lines = clean_log.split("\n")
    n = len(lines)
    keep: Set[int] = set(range(min(head, n))) | set(range(max(0, n - tail), n))
    seen_sigs_first: Set[str] = set()
    seen_sigs_last: Set[str] = set()

    for i in range(n):
        l = lines[i]
        if ANCHOR_PATTERN.search(l[:4096]):
            sig = re.sub(r"\d+", "#", l[:120].strip())
            if sig not in seen_sigs_first:
                seen_sigs_first.add(sig)
                keep.update(range(max(0, i - ctx), min(n, i + ctx + 1)))

    for i in reversed(range(n)):
        l = lines[i]
        if ANCHOR_PATTERN.search(l[:4096]):
            sig = re.sub(r"\d+", "#", l[:120].strip())
            if sig not in seen_sigs_last:
                seen_sigs_last.add(sig)
                keep.update(range(max(0, i - ctx), min(n, i + ctx + 1)))

    out: List[str] = []
    last: int = -1
    elided_total = 0
    for i in sorted(keep):
        if i != last + 1 and last != -1:
            diff_lines = i - last - 1
            elided_total += diff_lines
            out.append(f"… [{diff_lines} dòng log bị lược]")
        out.append(lines[i])
        last = i

    focused_lines = head_tail(out, budget, head_ratio=0.35)
    for l in focused_lines:
        m = re.search(r"… \[(\d+) dòng bị lược\]", l)
        if m:
            elided_total += int(m.group(1))

    final_text = "\n".join(focused_lines)

    return LogDigest(
        text=final_text,
        truncated=True,
        raw_bytes=raw_bytes,
        raw_sha256=raw_sha,
        elided_lines=elided_total
    )


def parse_diff(diff: str) -> List[Dict[str, Any]]:
    """Phân rã git diff thành danh sách file chi tiết, bảo toàn meta headers (rename, mode)."""
    files: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            path_part = line[11:].strip()
            path = path_part.split(" b/", 1)[-1] if " b/" in path_part else path_part
            cur = {
                "path": path,
                "head": line,
                "meta": [],
                "hunks": [],
                "add": 0,
                "del": 0,
            }
            files.append(cur)
        elif cur is None:
            continue
        elif line.startswith("@@"):
            cur["hunks"].append([line])
        elif cur["hunks"]:
            cur["hunks"][-1].append(line)
            if line.startswith("+"):
                cur["add"] += 1
            elif line.startswith("-"):
                cur["del"] += 1
        elif not cur["hunks"]:
            cur["meta"].append(line)

    return files


def _render_file(f: Dict[str, Any], share: int) -> Tuple[Optional[str], bool]:
    """Render diff file tuân thủ trần share nghiêm ngặt, trả về (content, is_partial)."""
    meta_head = [f["head"]] + f.get("meta", [])
    full = "\n".join(meta_head + ["\n".join(h) for h in f["hunks"]])
    if nbytes(full) <= share:
        return full, False
    if not f["hunks"] or share < 128:
        return None, True

    per_hunk = max(32, (share - nbytes("\n".join(meta_head))) // len(f["hunks"]))
    parts = list(meta_head)
    for h in f["hunks"]:
        parts.append(h[0])
        chunk = head_tail(h[1:], max(32, per_hunk - nbytes(h[0])))
        parts.extend(chunk)

    rendered = "\n".join(parts)
    if nbytes(rendered) <= share:
        return rendered, True

    headers_only = "\n".join(meta_head + [h[0] for h in f["hunks"]])
    if nbytes(headers_only) <= share:
        return headers_only, True

    return None, True


@dataclass
class DiffDigest:
    text: str
    level: str
    raw_bytes: int
    raw_sha256: str
    omitted: List[str] = field(default_factory=list)


def digest_diff(diff: str, budget: int, hot_paths: frozenset = frozenset()) -> DiffDigest:
    """
    Thu gọn diff vừa vặn budget:
      - Băm sha256 và đo raw_bytes trên diff GỐC
      - Giới hạn kích thước stat (tối đa budget // 4)
      - Cập nhật omitted nếu fallback hard-truncated
    """
    raw_bytes = nbytes(diff)
    raw_sha = sha256_full(diff)

    clean_diff = normalize_diff(diff)
    if nbytes(clean_diff) <= budget:
        return DiffDigest(clean_diff, "L0", raw_bytes, raw_sha)

    files = parse_diff(clean_diff)
    if not files:
        compact = "\n".join(head_tail(clean_diff.split("\n"), budget))
        return DiffDigest(compact, "L4", raw_bytes, raw_sha, ["raw-diff-truncated"])

    stat_lines = [f"{f['path']} (+{f['add']}/-{f['del']}, {len(f['hunks'])} hunk)" for f in files]
    stat_budget = max(256, budget // 4)
    stat = "\n".join(head_tail(stat_lines, stat_budget))

    omitted: List[str] = [f"{f['path']}(stat-only)" for f in files if NOISE_PATTERN.search(f["path"])]

    code_files = sorted(
        (f for f in files if not NOISE_PATTERN.search(f["path"])),
        key=lambda f: nbytes("\n".join("\n".join(h) for h in f["hunks"]))
    )

    remaining = max(256, budget - nbytes(stat) - 512)
    weights = [2 if f["path"] in hot_paths else 1 for f in code_files]
    parts: List[str] = []

    for i, f in enumerate(code_files):
        sum_w = sum(weights[i:])
        share = remaining * weights[i] // sum_w if sum_w > 0 else remaining
        rendered, is_partial = _render_file(f, share)
        if rendered is None:
            omitted.append(f"{f['path']}(stat-only)")
            continue
        if is_partial:
            omitted.append(f"{f['path']}(partial)")
        parts.append(rendered)
        remaining -= (nbytes(rendered) + 1)

    body = "[FILES STAT]\n" + stat + "\n\n[DIFF CONTENT]\n" + "\n".join(parts)
    level = "L4" if parts else "L5"

    if nbytes(body) > budget:
        body = "\n".join(head_tail(body.split("\n"), budget))
        omitted.append("diff-body-hard-truncated")
        level = "L5"

    return DiffDigest(body, level, raw_bytes, raw_sha, omitted)


def split_budget(total_budget: int) -> Tuple[int, int, int]:
    """
    Phân bổ budget cho 3 thành phần chính:
      - Diff: 65%
      - Log:  25%
      - Prompt / Rubric / Manifest reserve: 10%
    Trả về: (diff_budget, log_budget, wrapper_reserve)
    """
    diff_b = int(total_budget * 0.65)
    log_b = int(total_budget * 0.25)
    reserve_b = total_budget - diff_b - log_b
    return diff_b, log_b, reserve_b


def format_manifest(
    diff_digest: Optional[DiffDigest] = None,
    log_digest: Optional[LogDigest] = None,
    sent_bytes: int = 0,
    extra: str = ""
) -> str:
    """
    Manifest bật lên nếu BẤT KỲ phần nào (diff hoặc log) bị cắt bớt.
    In rõ diff_sha256 và log_sha256 đầy đủ phục vụ audit trail.
    """
    diff_truncated = diff_digest is not None and (diff_digest.level != "L0" or diff_digest.omitted)
    log_truncated = log_digest is not None and log_digest.truncated

    if not diff_truncated and not log_truncated and not extra:
        return ""

    omitted_items = list(diff_digest.omitted) if diff_digest else []
    if log_truncated and log_digest:
        omitted_items.append(f"log({log_digest.elided_lines} lines elided)")

    if len(omitted_items) > 10:
        omitted_str = ", ".join(omitted_items[:8]) + f" … (+{len(omitted_items)-8} items)"
    else:
        omitted_str = ", ".join(omitted_items) if omitted_items else "none"

    raw_b = (diff_digest.raw_bytes if diff_digest else 0) + (log_digest.raw_bytes if log_digest else 0)
    level_str = diff_digest.level if diff_digest else "LOG_ONLY"

    diff_sha = diff_digest.raw_sha256[:12] if diff_digest else "none"
    log_sha = log_digest.raw_sha256[:12] if log_digest else "none"

    extra_str = extra if (not extra or extra.endswith("\n")) else (extra + "\n")

    return (
        f"[TRUNCATION_MANIFEST]\n"
        f"level={level_str} total_raw_bytes={raw_b} sent_bytes={sent_bytes}\n"
        f"diff_sha={diff_sha} log_sha={log_sha}\n"
        f"omitted_details={omitted_str}\n"
        f"{extra_str}"
        f"NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>.\n\n"
    )


# ─── CẦU NỐI: VÒNG THỬ LẠI FIT_AND_ENFORCE ─────────────────────────────────────

def fit_and_enforce(
    build_fn: Callable[[int], Dict[str, Any]],
    budgets: Optional[Sequence[int]] = None,
) -> bytes:
    """
    Nối Lớp 1 và Lớp 2. Gọi build_fn(budget) qua các bậc budget giảm dần (bắt đầu từ SOL_TARGET_BYTES).
    Nếu serialize JSON bị phình, tự động hạ bậc tiếp theo. Hết bậc -> fail-closed.
    QUY TẮC BẮT BUỘC: Khi gửi HTTP qua OmniRoute, caller BẮT BUỘC phải gửi data=raw (không dùng json=).
    """
    if budgets is None:
        candidates = {SOL_TARGET_BYTES, 24_576, 16_384, 8_192}
    else:
        candidates = set(budgets) | {SOL_TARGET_BYTES}

    effective_budgets = sorted([b for b in candidates if b <= SOL_TARGET_BYTES], reverse=True)
    if not effective_budgets:
        effective_budgets = [SOL_TARGET_BYTES]

    last_err: Optional[Exception] = None
    for b in effective_budgets:
        try:
            body = build_fn(b)
            return enforce(body)
        except PayloadTooLarge as e:
            last_err = e

    raise PayloadTooLarge(
        f"Không thể fit payload sau {len(effective_budgets)} bậc budget ({effective_budgets}): {last_err}"
    )
