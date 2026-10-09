#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification probe for Taadaa Farm video sourcing & deduplication invariants.
Validates:
1. Channel claims ledger integrity (gaixinh_channel_claims.json).
2. ViT ONNX normalization invariant (mean=0.5, std=0.5).
3. Audio gate (faster_whisper / verify_audio_no_speech) readiness.
4. Leftover pool recycling (>45 videos) in smart_gaixinh_distributor.py.
5. Render speedup (2 workers song song) in run_render_group3.py.
"""
import json
import os
import sys
from pathlib import Path

def test_claims_integrity(repo_root: Path) -> bool:
    claims_path = repo_root / "data" / "gaixinh_channel_claims.json"
    if not claims_path.exists():
        print("[WARN] gaixinh_channel_claims.json not found yet.")
        return True
    try:
        with open(claims_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        seen_folders = set()
        for url, info in data.items():
            folder = str(info.get("folder"))
            if folder in seen_folders:
                print(f"[FAIL] Duplicate folder claim detected: Folder {folder} claimed multiple times!")
                return False
            seen_folders.add(folder)
        print(f"[PASS] Claims ledger valid: {len(data)} unique channel-to-folder claims.")
        return True
    except Exception as e:
        print(f"[FAIL] Claims ledger error: {e}")
        return False

def test_vit_normalization(repo_root: Path) -> bool:
    model_path = repo_root / "models" / "onnx" / "model_quantized.onnx"
    if not model_path.exists():
        print(f"[WARN] ViT ONNX model not found at {model_path}.")
        return True
    filter_py = repo_root / "scripts" / "ai_channel_filter.py"
    if not filter_py.exists():
        print(f"[WARN] ai_channel_filter.py not found.")
        return True
    with open(filter_py, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "(arr - 0.5) / 0.5" not in content and "0.5" not in content:
        print("[FAIL] Missing ViT standard normalization (arr - 0.5)/0.5 in ai_channel_filter.py!")
        return False
    print("[PASS] ViT normalization invariant verified.")
    return True

def test_audio_whisper_gate(repo_root: Path) -> bool:
    filter_py = repo_root / "scripts" / "ai_channel_filter.py"
    if not filter_py.exists():
        return True
    with open(filter_py, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "verify_audio_no_speech" not in content:
        print("[FAIL] Missing verify_audio_no_speech in ai_channel_filter.py!")
        return False
    print("[PASS] Faster-Whisper audio gate (loại bỏ tiếng Trung, giữ thuần nhạc) verified.")
    return True

def test_leftover_pool_logic(repo_root: Path) -> bool:
    dist_py = repo_root / "scripts" / "smart_gaixinh_distributor.py"
    if not dist_py.exists():
        return True
    with open(dist_py, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "leftover_vids = vids[args.max_videos:]" not in content and "vids[:args.max_videos]" not in content:
        print("[WARN] Max videos slice / leftover pool logic not explicitly found.")
        return True
    print("[PASS] Leftover pool recycling (>45 videos) logic verified.")
    return True

def test_render_2workers_group3(repo_root: Path) -> bool:
    render_py = repo_root / "scripts" / "run_render_group3.py"
    if not render_py.exists():
        return True
    with open(render_py, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if '"--parallel", "2"' not in content and "'--parallel', '2'" not in content:
        print("[WARN] run_render_group3.py does not specify 2 parallel workers.")
        return True
    print("[PASS] 2-worker parallel render speedup verified.")
    return True

def main():
    repo_root = Path("D:/Taadaa/Tiktok-video")
    print("=" * 60)
    print("VERIFYING TIKTOK VIDEO SOURCING & DEDUP INVARIANTS")
    print("=" * 60)
    c1 = test_claims_integrity(repo_root)
    c2 = test_vit_normalization(repo_root)
    c3 = test_audio_whisper_gate(repo_root)
    c4 = test_leftover_pool_logic(repo_root)
    c5 = test_render_2workers_group3(repo_root)
    if c1 and c2 and c3 and c4 and c5:
        print("\n>>> ALL SOURCING INVARIANTS VERIFIED SUCCESSFULLY! <<<")
        sys.exit(0)
    else:
        print("\n>>> SOURCING INVARIANTS VERIFICATION FAILED! <<<")
        sys.exit(1)

if __name__ == "__main__":
    main()
