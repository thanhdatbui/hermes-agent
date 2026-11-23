"""closeout-mechanizer: deterministic 'Done' closeout + completion-claim validator.

1. pre_gateway_dispatch: a bare "Done"/"xong" message never reaches the LLM. The
   gate runs in code and its verbatim verdict is sent back; the message is skipped.
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
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CLOSEOUT_SCRIPT = r"D:\Taadaa\tools\closeout_v2.py"
CLOSEOUT_REPOS = [r"D:\Taadaa\tools", r"D:\Taadaa\AI-Tools"]
CLOSEOUT_TIMEOUT = 300

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


# Step 1: run the deterministic closeout gate per repo (code, not LLM)
def run_closeout(repos: Optional[List[str]] = None) -> str:
    """Run the deterministic gate on each repo; return a verbatim verdict table."""
    rows, any_fail = [], False
    for repo in repos or CLOSEOUT_REPOS:
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
            rows.append((repo, verdict, p.returncode))
            any_fail |= p.returncode != 0
        except Exception as exc:
            rows.append((repo, f"ERROR:{type(exc).__name__}", -1))
            any_fail = True
    lines = ["CLOSEOUT GATE (chay bang code, khong qua LLM)", "repo | verdict | exit"]
    lines += [f"{r} | {v} | {rc}" for r, v, rc in rows]
    lines.append("TONG: " + ("REJECTED - co repo khong dat" if any_fail else "APPROVED"))
    return "\n".join(lines)


async def _closeout_and_reply(gateway: Any, event: Any) -> None:
    text = await asyncio.to_thread(run_closeout)
    adapter = gateway._adapter_for_source(event.source)
    if adapter:
        await adapter.send(event.source.chat_id, text)


# Step 2: intercept bare Done at the gateway and skip the LLM
def _on_pre_gateway_dispatch(event: Any = None, gateway: Any = None, **_: Any):
    try:
        if event is None or not is_done_signal(getattr(event, "text", "") or ""):
            return None
        loop = asyncio.get_running_loop()
        loop.create_task(_closeout_and_reply(gateway, event))
        return {"action": "skip", "reason": "closeout-mechanizer: Done handled by code"}
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
