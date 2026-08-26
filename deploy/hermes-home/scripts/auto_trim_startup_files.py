#!/usr/bin/env python3
"""
auto_trim_startup_files.py — Dọn dẹp định kỳ các file startup (HANDOFF.md, AGENTS.md, PROJECT_RULES.md)
tránh phình to context nạp vào Hermes session.

Quy tắc:
1. HANDOFF.md / handoff.md > 200 dòng: cắt bỏ phần giữa (giữ top 120 + bottom 60 dòng).
2. AGENTS.md / PROJECT_RULES.md > 400 dòng: cắt block duplicate workspace policy nếu có.
3. Tự backup vào D:/Taadaa/handoff-trim-backups/<timestamp>/ trước khi sửa.
4. Giữ nguyên EOL (CRLF/LF) per-file.
5. Watchdog pattern: im lặng khi không có file nào vượt ngưỡng. Báo cáo khi có dọn.
"""
import os, sys, pathlib, shutil, datetime, re

ROOT = pathlib.Path(r"D:\Taadaa")
BACKUP_ROOT = ROOT / "handoff-trim-backups"
SKIP_DIRS = {
    '.git', '.runtime', '.pytest_cache', '__pycache__', 'node_modules',
    'context-worktrees', '.ai-runs', '.codex-work', 'site ban hang clone-incomplete',
    'site ban hang clone-incomplete-20260719', 'handoff-trim-backups', 'consumer-worktrees',
    '_core031_build', '_lock_gate_backup_20260814', 'handoff-trim-rule-backup1-20260811-232050'
}

def trim_handoff(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= 200:
        return text
    head = lines[:130]
    tail = lines[-60:]
    notice = [
        "",
        "> [AUTO-TRIM NOTICE]: Đã lược bớt phần giữa của HANDOFF.md để giữ context gọn nhẹ.",
        f"> Gốc: {len(lines)} dòng -> {len(head) + len(tail) + 4} dòng. Chi tiết lưu tại backup.",
        ""
    ]
    return "\n".join(head + notice + tail)

def trim_duplicate_workspace_policy(text: str) -> str:
    """Cắt block AI Agent Workflow Rules hoặc CODEX duplicate policy nếu có trong repo con."""
    if len(text.splitlines()) <= 350:
        return text
    # Marker patterns from the 11-12/08 cleanup
    patterns = [
        r'(?s)# AI Agent Workflow Rules\n.*?(?=\n# |\Z)',
        r'(?s)<!-- CODEX-DIRECT-WORKER-POLICY:START -->.*?<!-- CODEX-DIRECT-WORKER-POLICY:END -->',
    ]
    result = text
    for p in patterns:
        result = re.sub(p, '<!-- [AUTO-TRIM]: AI Agent Workflow Rules duplicate workspace policy has been trimmed -->', result)
    return result

def main():
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / ts
    trimmed = []

    for d in sorted(os.listdir(ROOT)):
        dp = ROOT / d
        if not dp.is_dir() or d.startswith(('.', '_')) or d in SKIP_DIRS:
            continue

        # 1. HANDOFF files
        for fname in ['HANDOFF.md', 'handoff.md']:
            fp = dp / fname
            if not fp.is_file(): continue
            raw = fp.read_bytes()
            lines = raw.splitlines()
            if len(lines) > 200:
                if not backup_dir.exists(): backup_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, backup_dir / f"{d}__{fname}")
                eol = "\r\n" if b"\r\n" in raw else "\n"
                text = raw.decode("utf-8", errors="replace")
                new_text = trim_handoff(text)
                new_raw = new_text.replace("\r\n", "\n").replace("\n", eol).encode("utf-8")
                if len(new_raw) < len(raw):
                    fp.write_bytes(new_raw)
                    trimmed.append(f"{d}/{fname}: {len(lines)}L -> {len(new_text.splitlines())}L")

        # 2. AGENTS / PROJECT_RULES with duplicate policy
        for fname in ['AGENTS.md', 'PROJECT_RULES.md']:
            fp = dp / fname
            if not fp.is_file(): continue
            # don't trim root AGENTS.md with this generic regex
            if dp == ROOT: continue
            raw = fp.read_bytes()
            lines = raw.splitlines()
            if len(lines) > 400:
                text = raw.decode("utf-8", errors="replace")
                new_text = trim_duplicate_workspace_policy(text)
                if len(new_text) < len(text):
                    if not backup_dir.exists(): backup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fp, backup_dir / f"{d}__{fname}")
                    eol = "\r\n" if b"\r\n" in raw else "\n"
                    new_raw = new_text.replace("\r\n", "\n").replace("\n", eol).encode("utf-8")
                    fp.write_bytes(new_raw)
                    trimmed.append(f"{d}/{fname}: {len(lines)}L -> {len(new_text.splitlines())}L")

    if not trimmed:
        return 0

    print(f"=== AUTO-TRIM STARTUP FILES ({ts}) ===")
    print(f"Backup: {backup_dir}")
    for item in trimmed:
        print(f"  - {item}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
