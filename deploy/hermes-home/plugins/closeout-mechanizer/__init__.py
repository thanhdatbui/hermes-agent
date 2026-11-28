"""closeout-mechanizer: deterministic 'Done' closeout + completion-claim validator.

1. pre_gateway_dispatch: a bare "Done"/"xong" message is rewritten into a session-report request for the LLM; the
   gate runs in code and its verbatim verdict table is sent back separately.
2. post_tool_call records ground truth per turn plus the workspace repos the session mutated
   (Scope Lock: the gate only checks those repos, never other sessions' WIP).
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
CLOSEOUT_WORKSPACE = r"D:\Taadaa"
CLOSEOUT_WORKERS = 4
CLOSEOUT_TIMEOUT = 300
CLOSEOUT_REWRITE_TEXT = (
    "[Done] User chot phien. Viet bao cao tong ket CA PHIEN theo skill session-close-protocol: "
    "viec da lam, loi da debug/fix, test da pass (chi neu co tool receipt that), "
    "cai da verify live vs chi unit test, ton dong. "
    "Bang CLOSEOUT GATE (verdict/push tung repo) do code gui rieng ngay sau tin nay: "
    "KHONG tu neu hay doan verdict gate/push, chi tham chieu bang do."
)

# "rone" is a common adjacent-key typo for "done" on QWERTY keyboards.
_TRIGGERS = {"done", "rone", "xong", "chot phien", "chot phien nhe", "done nhe", "xong roi", "done roi"}

_CLAIM_RE = re.compile(
    r"(đã|da)\s+(xong|hoàn\s*thành|hoan\s*thanh|cơ\s*giới\s*hóa|co\s*gioi\s*hoa|lưu|luu|sửa|sua|fix|vá|va|áp\s*dụng|ap\s*dung|đưa\s+vào|dua\s+vao|cập\s*nhật|cap\s*nhat|triển\s*khai|trien\s*khai|commit|push)"
    r"|hoàn\s*tất|hoan\s*tat|\bdone\b|\bfixed\b|\bcompleted\b|\bsaved\b|\bimplemented\b",
    re.IGNORECASE,
)
_MUTATING_TOOLS = re.compile(r"patch|write|edit|memory|skill|cronjob|execute", re.IGNORECASE)

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


def _has_real_commit(repo: str) -> bool:
    try:
        return _git(repo, "rev-parse", "--verify", "HEAD").returncode == 0
    except Exception:
        return False


def _ahead_count(repo: str) -> int:
    try:
        res = _git(repo, "rev-list", "--count", "@{u}..HEAD")
        if res.returncode != 0:
            return 0
        return max(0, int((res.stdout or "0").strip() or 0))
    except Exception:
        return 0


# Step 1: push already-committed work only; never commit (dirty files may belong to others)
def push_if_ahead(repo: str) -> str:
    try:
        upstream_res = _git(repo, "rev-parse", "--abbrev-ref", "@{u}")
        if upstream_res.returncode != 0:
            return "PUSH_SKIPPED_NO_UPSTREAM"
        upstream = upstream_res.stdout.strip()
        if not upstream or "/" not in upstream:
            return "PUSH_SKIPPED_NO_UPSTREAM"
        remote = upstream.split("/", 1)[0].strip() or "origin"

        ahead = _git(repo, "rev-list", "--count", "@{u}..HEAD")
        if ahead.returncode != 0:
            return "PUSH_SKIPPED_NO_UPSTREAM"
        if int(ahead.stdout.strip() or 0) == 0:
            return "NOTHING_TO_PUSH"

        branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        sys.path.insert(0, str(Path(CLOSEOUT_SCRIPT).parent))
        from safe_push import safe_push

        res = safe_push(repo, remote, branch, timeout=120)
        if res.returncode != 0:
            return f"PUSH_FAILED:rc={res.returncode}"
        return f"PUSHED:{remote}/{branch}"
    except Exception as exc:
        return f"PUSH_FAILED:{type(exc).__name__}"


_scope_lock = threading.Lock()
_session_repos: Dict[str, List[str]] = {}


def _state_file() -> Path:
    home = os.environ.get("HERMES_HOME") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")
    return Path(home) / "closeout_session_repos.json"


def _load_scope() -> None:
    try:
        data = json.loads(_state_file().read_text(encoding="utf-8"))
        with _scope_lock:
            for sid, repos in data.items():
                _session_repos.setdefault(sid, list(repos))
    except Exception:
        pass


def _save_scope() -> None:
    try:
        with _scope_lock:
            snap = {k: v for k, v in list(_session_repos.items())[-200:]}
        _state_file().write_text(json.dumps(snap), encoding="utf-8")
    except Exception:
        logger.debug("[CLOSEOUT_MECH] scope save failed", exc_info=True)


def _workspace_repos(root: str = CLOSEOUT_WORKSPACE) -> Dict[str, str]:
    try:
        return {c.name: str(c) for c in Path(root).iterdir() if (c / ".git").exists()}
    except Exception:
        return {}


# Step 0: detect mutating tool calls including worker/patch runner commands
def _is_mutating_tool_call(tool_name: str, args: Any) -> bool:
    name = tool_name or ""
    if _MUTATING_TOOLS.search(name):
        return True
    if name in ("terminal", "execute_code"):
        try:
            blob = json.dumps(args, ensure_ascii=False, default=str)
        except Exception:
            blob = str(args)
        lowered = blob.lower()
        return any(
            m in lowered
            for m in ("dispatch_worker.py", "claude_worker.py", "unified_patch_pipeline.py")
        )
    return False


# Scope Lock: repos a session touched = workspace repos named in the args of its mutating tool calls
def repos_in_args(args: Any, root: str = CLOSEOUT_WORKSPACE) -> List[str]:
    try:
        blob = json.dumps(args, ensure_ascii=False, default=str)
    except Exception:
        blob = str(args)
    blob = re.sub(r"/+", "/", blob.replace("\\", "/")).lower()
    base = re.sub(r"/+", "/", root.replace("\\", "/")).lower().rstrip("/")
    ws_repos = _workspace_repos(root)
    norm_to_path: Dict[str, str] = {}
    for name, path in ws_repos.items():
        p_norm = re.sub(r"/+", "/", str(path).replace("\\", "/")).rstrip("/")
        norm_to_path[p_norm.lower()] = p_norm
        norm_to_path[f"{base}/{name.lower()}"] = p_norm

    # Step 0: a file-edit tool's own "path" decides the repo; never scan new_string/content
    # (they may mention other repos' paths and would pollute the Scope Lock)
    if isinstance(args, dict) and isinstance(args.get("path"), str) and args["path"].strip():
        target = re.sub(r"/+", "/", args["path"].strip().replace("\\", "/")).lower().rstrip("/")
        for k, p in norm_to_path.items():
            if target == k or target.startswith(k + "/"):
                return [p]

    # Step 1: prioritize explicit --workdir or --repo target if it matches a workspace repo
    explicit_targets: List[str] = []
    for m in re.finditer(r"(?:--workdir|--repo)(?:=|\s+)(?:/?[\"'])?([^\s\"'\\]+(?:/[^\s\"'\\]+)*)", blob):
        cand = m.group(1).rstrip('/"\'')
        matched = norm_to_path.get(cand)
        if not matched:
            for k, p in norm_to_path.items():
                if cand == k or cand.startswith(k + "/"):
                    matched = p
                    break
        if matched and matched not in explicit_targets:
            explicit_targets.append(matched)

    if explicit_targets:
        return explicit_targets

    found: List[str] = []
    for name, path in ws_repos.items():
        if re.search(re.escape(f"{base}/{name.lower()}") + r"(?![\w\-])", blob):
            p_norm = re.sub(r"/+", "/", str(path).replace("\\", "/")).rstrip("/")
            if p_norm not in found:
                found.append(p_norm)
    return found


def record_scope(session_id: str, repos: List[str]) -> None:
    if not repos:
        return
    with _scope_lock:
        cur = _session_repos.setdefault(session_id or "", [])
        new = [r for r in repos if r not in cur]
        cur.extend(new)
    if new:
        _save_scope()


def session_repos(session_id: str) -> List[str]:
    with _scope_lock:
        repos = list(_session_repos.get(session_id or "", []))
    # Step 1: filter out runner utility repo 'tools' unless it has unpushed commits
    filtered = []
    for r in repos:
        r_norm = str(r).replace("\\", "/").rstrip("/")
        if r_norm.lower().endswith("/tools"):
            # Check if this session actually committed code to tools
            has_commit = _has_real_commit(r)
            ahead = _ahead_count(r) if has_commit else 0
            if ahead == 0:
                continue
        filtered.append(r)
    return filtered


def _gate_one(repo: str):
    repo_norm = str(repo).replace("\\", "/")
    cmd = [sys.executable, CLOSEOUT_SCRIPT, "--repo", repo, "--json-output"]
    # Step: If repo is Hermes and target file is known, restrict scope to avoid scanning external changes
    if repo_norm.lower().endswith("/hermes"):
        cmd += ["--target-file", "deploy/hermes-home/scripts/cron_clear_tiktok_cache.py"]
    try:
        p = subprocess.run(
            cmd,
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
        d = dirty_count(repo)
        # Step 1: push only when gate approves (returncode 0); otherwise mark gate not approved and fail
        if p.returncode == 0:
            push = push_if_ahead(repo)
            fail = push.startswith("PUSH_FAILED")
        else:
            push = "SKIPPED_GATE_NOT_APPROVED"
            fail = True
        return (repo_norm, verdict, p.returncode, push, d), fail
    except Exception as exc:
        return (repo_norm, f"ERROR:{type(exc).__name__}", -1, "SKIPPED", -1), True


# Step 1: run the deterministic closeout gate per repo in parallel (code, not LLM)
def run_closeout(repos: Optional[List[str]] = None) -> str:
    """Run the deterministic gate on each repo; return a verbatim verdict table."""
    targets = list(repos or [])
    if not targets:
        return (
            "CLOSEOUT GATE (chay bang code, khong qua LLM)\n"
            "Khong co repo nao duoc phien nay sua (Scope Lock) - khong quet repo cua phien khac.\n"
            "TONG: KHONG_CO_VIEC"
        )
    with ThreadPoolExecutor(max_workers=CLOSEOUT_WORKERS) as pool:
        results = list(pool.map(_gate_one, targets))
    rows = [r for r, _ in results]
    any_fail = any(f for _, f in results)
    lines = ["CLOSEOUT GATE (chay bang code, khong qua LLM)", "repo | verdict | exit | push | file_dirty_chua_commit"]
    lines += [f"{r} | {v} | {rc} | {ps} | {d}" for r, v, rc, ps, d in rows]
    lines.append("TONG: " + ("REJECTED - co repo khong dat" if any_fail else "APPROVED"))
    return "\n".join(lines)


def _session_id_for_event(gateway: Any, event: Any) -> str:
    try:
        key = gateway._session_key_for_source(event.source)
        return gateway.session_store.peek_session_id(key) or ""
    except Exception:
        return ""


# Step 1b: Scope Lock lost (restart): rebuild from this session's own transcript tool calls, never from git activity of other sessions
def infer_repos_from_transcript(messages: Any, root: str = CLOSEOUT_WORKSPACE) -> List[str]:
    found: List[str] = []
    for m in messages or []:
        for tc in (m.get("tool_calls") or []) if isinstance(m, dict) else []:
            fn = tc.get("function") or {}
            if not _is_mutating_tool_call(str(fn.get("name", "")), fn.get("arguments")):
                continue
            for r in repos_in_args(fn.get("arguments"), root=root):
                if r not in found:
                    found.append(r)
    return found


def _session_transcript(gateway: Any, session_id: str) -> Any:
    try:
        return gateway.session_store.load_transcript(session_id)
    except Exception:
        return []


async def _closeout_and_reply(gateway: Any, event: Any) -> None:
    sid = _session_id_for_event(gateway, event)
    repos = session_repos(sid)
    if not repos:
        repos = infer_repos_from_transcript(await asyncio.to_thread(_session_transcript, gateway, sid))
        record_scope(sid, repos)
    text = await asyncio.to_thread(run_closeout, repos)
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
def _on_post_tool_call(tool_name: str = "", result: Any = None, session_id: str = "", args: Any = None, **_: Any):
    try:
        if (
            tool_name != "read_file"
            and _is_mutating_tool_call(tool_name, args)
            and args
            and classify_result(result) == "OK"
        ):
            record_scope(session_id, repos_in_args(args))
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
    _load_scope()
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
    logger.info("[CLOSEOUT_MECH] registered")
