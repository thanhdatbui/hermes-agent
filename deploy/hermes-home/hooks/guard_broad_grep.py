"""
[HERMES HARD GATE #4 - ZERO-BYPASS SCAN GUARD]
Pre-tool hook: Chặn toàn bộ họ lệnh quét diện rộng trên Windows/POSIX:
grep (-r, -rn, -R, --recursive), rg, find, findstr /s, dir /s, tree /f,
PowerShell alias (Get-ChildItem -Recurse, gci -Recurse, gci -r, ls -r, Select-String -Recurse),
và script Python quét đĩa (os.walk, rglob, glob.glob recursive).
"""
import json, sys, re

DANGEROUS_TARGETS = [
    r"D:[\\/]?$",
    r"D:[\\/]Taadaa[\\/]?$",
    r"D:[\\/]CodexRuntime",
    r"[\\/]\.ai-runs",
    r"runtime[\\/]kibe",
    r"python-envs",
    r"BACKUP_ALL",
    r"node_modules",
    r"__pycache__",
]

SCAN_TOOLS = [
    r"\bgrep\s+(?:-[a-zA-Z]*[rR]|--recursive)",
    r"\brg\b",
    r"\bfind\s+[\'\"]?(?:D:[\\/]|D:[\\/]Taadaa|\.)",
    r"\bfindstr\s+/[sS]",
    r"\bSelect-String\s+.*-Recurse",
    r"\b(?:Get-ChildItem|gci|ls)\s+.*-(?:Recurse|[rR])\b",
    r"\bdir\s+/[sS]",
    r"\btree\s+/[fF]",
    r"os\.walk",
    r"\.rglob\(",
    r"glob\.glob\(.*recursive\s*=\s*True",
]

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_name = payload.get("tool") or payload.get("tool_name") or ""
args = payload.get("args") or {}

if tool_name == "terminal":
    cmd = args.get("command") or ""
    norm_cmd = cmd.replace("\\", "/")
    
    is_scan = any(re.search(pat, cmd, re.IGNORECASE) for pat in SCAN_TOOLS)
    
    if is_scan:
        for target in DANGEROUS_TARGETS:
            if re.search(target, cmd, re.IGNORECASE) or re.search(target.replace(r"[\\/]", "/"), norm_cmd, re.IGNORECASE):
                msg = (
                    f"[HARD GATE #4 - ZERO-BYPASS SCAN] COMMAND BỊ CHẶN: Phát hiện lệnh quét đĩa ({cmd[:70]}...). "
                    f"CẤM TUYỆT ĐỐI dùng grep -r/--recursive, rg, find, findstr /s, gci -r hoặc python os.walk vào root / runs / runtime!\n"
                    f"AFFORDANCE (Đường thay thế hợp lệ):\n"
                    f"  1. Đọc đúng file cụ thể: grep -n 'PATTERN' D:/Taadaa/path/to/file.py\n"
                    f"  2. Tra cứu O(1) cấu hình trong D:/Taadaa/machine-config/ hoặc file mapping Excel\n"
                    f"  3. Dùng Python one-liner đọc trực tiếp file đích < 1s."
                )
                print(json.dumps({"action": "block", "message": msg}))
                sys.exit(0)
        
        if re.search(r"\b(?:grep\s+(?:-[a-zA-Z]*[rR]|--recursive)|rg)\b", cmd) and ("--exclude" not in cmd and "--include" not in cmd):
            msg = (
                f"[HARD GATE #4 - ZERO-BYPASS SCAN] grep/rg quét diện rộng BỊ CHẶN: '{cmd[:70]}...'. "
                f"BẮT BUỘC chỉ định file đích cụ thể (grep -n trên 1 file) hoặc có bộ lọc --include hẹp."
            )
            print(json.dumps({"action": "block", "message": msg}))
            sys.exit(0)

if tool_name == "search_files":
    path = args.get("path") or ""
    target_type = args.get("target") or "content"
    if target_type == "content":
        norm_path = path.replace("\\", "/")
        for target in DANGEROUS_TARGETS:
            if re.search(target, path, re.IGNORECASE) or re.search(target.replace(r"[\\/]", "/"), norm_path, re.IGNORECASE):
                msg = (
                    f"[HARD GATE #4 - ZERO-BYPASS SCAN] search_files BỊ CHẶN: Thư mục '{path}' cấm quét nội dung diện rộng.\n"
                    f"Hãy dùng read_file O(1) hoặc chỉ định sub-folder cụ thể có giới hạn."
                )
                print(json.dumps({"action": "block", "message": msg}))
                sys.exit(0)

sys.exit(0)
