---
title: "Config & Prompt Hygiene Rules"
description: "Rules for keeping Hermes config, SOUL.md, and prompts minimal to save quota"
---

# Config & Prompt Hygiene Rules (2026-09-03)

## Principle
**When Farm Alert contains actionable commands + file paths, verbose prompt rules become redundant and waste token quota.**

## What Was Cleaned

### 1. `~/.hermes/SOUL.md`
- **Before**: Multiple paragraphs repeating "cấm grep", "cấm quét đĩa", farm safety rules
- **After**: Single line minimal identity

### 2. `config.yaml` - Channel Overrides
- **Farm Alert channel (-5373649734)**: Reduced to 5-step Action Gate only
- **Other channels (-5145780745, -5171154309, -5377611430, -5435853713, -5494641602)**: Stripped redundant farm rules
- **Personalities (im_lang, van_hanh_chi_tiet, van_hanh_mac_dinh)**: Removed duplicated "cấm grep" paragraphs

### 3. Memory
- **Before**: Long multi-line entries about alert handling
- **After**: Single compact line: `Alert [MAY N]: Chay python D:/Taadaa/tools/inspect_machine.py <N> hoac ban ADB theo serial. Coordinator doc log/plan/review, worker delegate sua code/test (<30s).`

## Result
- `config.yaml` reduced from **33.4 KB → 16 KB** (52% token savings per session)
- SOUL.md reduced to ~2 lines
- Memory freed for actual task context

## Rule Going Forward
**Any rule that is already enforced by the Alert payload format does NOT need to be repeated in prompts/config/memory.**

The Alert format IS the contract. The prompt only needs to say: "Follow the 5-step Action Gate in the alert."