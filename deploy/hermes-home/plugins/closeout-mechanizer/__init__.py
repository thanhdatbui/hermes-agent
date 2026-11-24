"""closeout-mechanizer: deterministic 'Done' closeout + completion-claim validator.

1. pre_gateway_dispatch: a bare "Done"/"xong" message is rewritten into a session-report request for the LLM; the
   gate runs in code and its verbatim verdict table is sent back separately.
2. post_tool_call records ground truth (ok / staged / blocked / failed) per turn.
3. transform_llm_output replaces a completion claim that has no successful
   tool receipt in the same turn with a fixed one-line template.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CLOSEOUT_SCRIPT = r"D:\Taadaa\tools\closeout_v2.py"
CLOSEOUT_REPOS = [r"D:\Taadaa\tools", r"D:\Taadaa\AI-Tools"]
CLOSEOUT_WORKSPACE = r"D:\Taadaa"
CLOSEOUT_MAX_REPOS = 8
CLOSEOUT_WORKERS = 4
CLOSEOUT_TIMEOUT = 300
CLOSEOUT_REWRITE_TEXT = (
    "[Done] User chot phien. Viet bao cao tong ket CA PHIEN theo skill session-close-protocol: "
    "viec da lam, loi da debug/fix, test da pass (chi neu co tool receipt that), "
    "cai da verify live vs chi unit test, ton dong. "
    "Bang CLOSEOUT GATE (verdict/push tung repo) do code gui rieng ngay sau tin nay: "
    "KHONG tu neu hay doan verdict gate/push, chi tham chieu bang do."
)

_TRIGGERS = {"done", "xong", "chot phien", "chot phien nhe", "done nhe", "xong roi", "done roi"}

_CLAIM_RE = re.compile(
    r"(đã|da)\s+(xong|hoàn\s*thành|hoan\s*thanh|cơ\s*giới\s*hóa|co\s*gioi\s*hoa|lưu|luu|sửa|sua|fix|vá|va|áp\s*dụng|ap\s*dung|đưa\s+vào|dua\s+vao|cập\s*nhật|cap\s*nhat|triển\s*khai|trien\s*khai|commit|push)"
    r"|hoàn\s*tất|hoan\s*tat|\bdone\b|\bfixed\b|\bcompleted\b|\bsaved\b|\bimplemented\b",
    re.IGNORECASE,
)
_MUTATING_TOOLS = re.compile(r"patch|write|edit|memory|terminal|skill|cronjob|delegate|execute", re.IGNORECASE)

_lock = threading.Lock()
_turn_receipts: Dict[str, List[Dict[str, Any]]] = {}


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", (text or "").strip().lower().replace("đ", "d"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", "", t).strip()


def is_done_signal(text: str) -> bool:
    return _norm(text) in _TRIGGERS


def classify_result(result: Any) -> str:
    """Return OK | STAGED | BLOCKED | FAILED from a raw tool result."""
    obj = result
    if isinstance(result, str):
        try:
            obj = json.loads(result)
        except Exception:
            obj = None
    if isinstance(obj, dict):
        if obj.get("staged") or obj.get("pending_id"):
            return "STAGED"
        if obj.get("action") == "block" or obj.get("blocked"):
            return "BLOCKED"
        if obj.get("success") is False or obj.get("error"):
            return "FAILED"
        rc = obj.get("exit_code", obj.get("returncode"))
        if isinstance(rc, int) and rc != 0:
            return "FAILED"
        return "OK"
    s = str(result or "")
    if re.search(r"staged for approval|not yet saved", s, re.I):
        return "STAGED"
    if re.search(r"\[GUARD|BLOCKED|⛔|budget", s):
        return "BLOCKED"
    return "OK"


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, timeout=60,
        encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def dirty_count(repo: str) -> int:
    try:
        return len([l for l in _git(repo, "status", "--porcelain", "-uno").stdout.splitlines() if l.strip()])
    except Exception:
        return -1


# Step 0: push already-committed work only; never commit (dirty files may belong to others)
def push_if_ahead(repo: str) -> str:
    try:
        ahead = _git(repo, "rev-list", "--count", "@{u}..HEAD")
        if ahead.returncode != 0:
            return "PUSH_SKIPPED_NO_UPSTREAM"
        if int(ahead.stdout.strip() or 0) == 0:
            return "NOTHING_TO_PUSH"
        branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        sys.path.insert(0, str(Path(CLOSEOUT_SCRIPT).parent))
        from safe_push import safe_push
        res = safe_push(repo, "origin", branch, timeout=120)
        if res.returncode != 0:
            return f"PUSH_FAILED:rc={res.returncode}"
        return f"PUSHED:origin/{branch}"
    except Exception as exc:
        return f"PUSH_FAILED:{type(exc).__name__}"


def _ahead_count(repo: str) -> int:
    try:
        r = _git(repo, "rev-list", "--count", "@{u}..HEAD")
        return int(r.stdout.strip() or 0) if r.returncode == 0 else 0
    except Exception:
        return 0


# Step 0b: repos to check = fixed defaults + any workspace repo with unpushed commits or tracked dirty files
def discover_repos(root: str = CLOSEOUT_WORKSPACE, limit: int = CLOSEOUT_MAX_REPOS) -> List[str]:
    repos = list(CLOSEOUT_REPOS)
    seen = {os.path.normcase(os.path.abspath(r)) for r in repos}
    try:
        children = sorted(Path(root).iterdir())
    except Exception:
        return repos
    for child in children:
        key = os.path.normcase(str(child.resolve()))
        if key in seen or not (child / ".git").exists():
            continue
        if _ahead_count(str(child)) > 0 or dirty_count(str(child)) > 0:
            repos.append(str(child))
            seen.add(key)
        if len(repos) >= limit:
            break
    return repos


def _gate_one(repo: str):
    repo_norm = str(repo).replace("\\", "/")
    try:
        p = subprocess.run(
            [sys.executable, CLOSEOUT_SCRIPT, "--repo", repo, "--json-output"],
            capture_output=True, text=True, timeout=CLOSEOUT_TIMEOUT, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        verdict = "UNPARSED"
        for line in reversed(p.stdout.strip().splitlines()):
            try:
                verdict = json.loads(line).get("verdict", "UNPARSED")
                break
            except Exception:
                continue
        push = push_if_ahead(repo) if p.returncode == 0 else "SKIPPED_GATE_NOT_APPROVED"
        fail = p.returncode != 0 or push.startswith("PUSH_FAILED")
        return (repo_norm, verdict, p.returncode, push, dirty_count(repo)), fail
    except Exception as exc:
        return (repo_norm, f"ERROR:{type(exc).__name__}", -1, "SKIPPED", -1), True


# Step 1: run the deterministic closeout gate per repo in parallel (code, not LLM)
def run_closeout(repos: Optional[List[str]] = None) -> str:
    """Run the deterministic gate on each repo; return a verbatim verdict table."""
    targets = list(repos or discover_repos())
    with ThreadPoolExecutor(max_workers=CLOSEOUT_WORKERS) as pool:
        results = list(pool.map(_gate_one, targets))
    rows = [r for r, _ in results]
    any_fail = any(f for _, f in results)
    lines = ["CLOSEOUT GATE (chay bang code, khong qua LLM)", "repo | verdict | exit | push | file_dirty_chua_commit"]
    lines += [f"{r} | {v} | {rc} | {ps} | {d}" for r, v, rc, ps, d in rows]
    lines.append("TONG: " + ("REJECTED - co repo khong dat" if any_fail else "APPROVED"))
    return "\n".join(lines)


async def _closeout_and_reply(gateway: Any, event: Any) -> None:
    text = await asyncio.to_thread(run_closeout)
    adapter = gateway._adapter_for_source(event.source)
    if adapter:
        thread_id = getattr(event.source, "thread_id", None)
        metadata = {"thread_id": thread_id} if thread_id is not None else {}
        await adapter.send(
            event.source.chat_id,
            text,
            reply_to=getattr(event, "message_id", None),
            metadata=metadata,
        )


# Step 2: intercept bare Done at the gateway and skip the LLM
def _on_pre_gateway_dispatch(event: Any = None, gateway: Any = None, **_: Any):
    try:
        if event is None or not is_done_signal(getattr(event, "text", "") or ""):
            return None
        loop = asyncio.get_running_loop()
        loop.create_task(_closeout_and_reply(gateway, event))
        return {"action": "rewrite", "text": CLOSEOUT_REWRITE_TEXT}
    except Exception as exc:
        logger.warning("[CLOSEOUT_MECH] dispatch hook failed, falling through: %s", exc)
        return None


def _on_pre_llm_call(session_id: str = "", **_: Any):
    with _lock:
        _turn_receipts[session_id or ""] = []
    return None


# Step 3: record per-turn tool ground truth
def _on_post_tool_call(tool_name: str = "", result: Any = None, session_id: str = "", **_: Any):
    try:
        with _lock:
            _turn_receipts.setdefault(session_id or "", []).append(
                {"tool": tool_name, "status": classify_result(result)}
            )
    except Exception:
        logger.exception("[CLOSEOUT_MECH] receipt record failed")
    return None


# Step 4: reject completion claims without successful tool receipts
def validate_claim(response_text: str, receipts: List[Dict[str, Any]]) -> Optional[str]:
    """Return a replacement text when a completion claim lacks ground truth."""
    if not response_text or not _CLAIM_RE.search(response_text):
        return None
    bad = [r for r in receipts if r["status"] in ("STAGED", "BLOCKED", "FAILED")]
    good = [r for r in receipts if r["status"] == "OK" and _MUTATING_TOOLS.search(r["tool"] or "")]
    if good and not bad:
        return None
    if good and bad and receipts[-1]["status"] == "OK":
        return None
    if bad:
        detail = ", ".join(f"{r['tool']}={r['status']}" for r in bad[-3:])
        code = "UNPROVEN_" + bad[-1]["status"]
    else:
        detail, code = "khong co tool nao chay thanh cong trong luot nay", "NO_RECEIPT"
    return (
        f"Trang thai: UNVERIFIED | Ma: {code} | Bang chung: {detail} | "
        "Viec tiep theo: CHUA hoan thanh - bao dung ket qua tool, khong claim xong."
    )


def _enforce() -> bool:
    return os.environ.get("CLOSEOUT_MECH_ENFORCE", "0") == "1"


def _on_transform_llm_output(response_text: str = "", session_id: str = "", **_: Any) -> Optional[str]:
    try:
        with _lock:
            receipts = list(_turn_receipts.get(session_id or "", []))
        replacement = validate_claim(response_text, receipts)
        if replacement is None:
            return None
        if not _enforce():
            logger.warning("[CLOSEOUT_MECH][LOG_ONLY] would block claim: %s", replacement)
            return None
        return replacement
    except Exception:
        logger.exception("[CLOSEOUT_MECH] validator error (fail-open)")
        return None


def register(ctx: Any) -> None:
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
    logger.info("[CLOSEOUT_MECH] registered")
