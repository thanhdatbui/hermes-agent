#!/usr/bin/env python3
"""
Canonical helper tool for executing commands on admin-farm over SSH.
Used by Coordinator and automation scripts to avoid raw terminal ssh blocks
and guarantee safe base64-encoded PowerShell execution on Admin PC.
"""
import sys
import json
import base64
import subprocess
import argparse

def execute_remote_powershell(ps_command: str, host: str = "admin-farm", timeout: int = 60) -> dict:
    """Execute PowerShell snippet on remote host via Base64 UTF-16LE EncodedCommand."""
    b64_ps = base64.b64encode(ps_command.encode("utf-16le")).decode("ascii")
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        host,
        f"powershell -NoProfile -NonInteractive -EncodedCommand {b64_ps}"
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": 124,
            "stdout": "",
            "stderr": f"SSH execution timed out after {timeout}s"
        }
    except Exception as exc:
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc)
        }

def execute_raw_cmd(cmd_str: str, host: str = "admin-farm", timeout: int = 60) -> dict:
    """Execute raw shell/cmd string on remote host."""
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-o", "ServerAliveInterval=15",
        host,
        cmd_str
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()
        }
    except Exception as exc:
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc)
        }

def main():
    parser = argparse.ArgumentParser(description="Execute commands on admin-farm over SSH")
    parser.add_argument("command", help="PowerShell command string (or raw command if --raw)")
    parser.add_argument("--host", default="admin-farm", help="SSH target host (default: admin-farm)")
    parser.add_argument("--raw", action="store_true", help="Execute as raw command instead of Encoded PowerShell")
    parser.add_argument("--timeout", type=int, default=60, help="Execution timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    if args.raw:
        res = execute_raw_cmd(args.command, host=args.host, timeout=args.timeout)
    else:
        res = execute_remote_powershell(args.command, host=args.host, timeout=args.timeout)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if res["stdout"]:
            print(res["stdout"])
        if res["stderr"]:
            print(f"[STDERR] {res['stderr']}", file=sys.stderr)

    sys.exit(0 if res["success"] else (res["exit_code"] or 1))

if __name__ == "__main__":
    main()
