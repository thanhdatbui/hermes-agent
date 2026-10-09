#!/usr/bin/env python3
"""
Lightweight automated Douyin/TikTok video dubber:
Faster-Whisper (STT) + Edge-TTS (Voice) + FFmpeg (Mix & Subs).
"""
import asyncio
import os
import subprocess
import sys
from faster_whisper import WhisperModel
import edge_tts

def extract_and_transcribe(video_path: str, lang: str = "zh"):
    wav_temp = "temp_mono.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", wav_temp],
        capture_output=True, check=True
    )
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(wav_temp, language=lang)
    results = []
    for s in segments:
        results.append({
            "start": s.start,
            "end": s.end,
            "text": s.text.strip()
        })
    if os.path.exists(wav_temp):
        os.remove(wav_temp)
    return results

async def synthesize_audio(segments: list, voice: str = "vi-VN-HoaiMyNeural"):
    for idx, seg in enumerate(segments):
        out_name = f"voice_seg_{idx}.mp3"
        comm = edge_tts.Communicate(seg["vn_text"], voice)
        await comm.save(out_name)
        seg["audio_file"] = out_name

def render_final(video_path: str, segments: list, srt_file: str, output_path: str):
    inputs = ["-i", video_path]
    filter_parts = []
    amix_inputs = ["[abg]"]

    for idx, seg in enumerate(segments):
        inputs.extend(["-i", seg["audio_file"]])
        delay_ms = int(seg["start"] * 1000)
        filter_parts.append(f"[{idx+1}:a]adelay={delay_ms}|{delay_ms}[a{idx}];")
        amix_inputs.append(f"[a{idx}]")

    filter_parts.append("[0:a]volume=0.15[abg];")
    filter_parts.append(f"{''.join(amix_inputs)}amix=inputs={len(amix_inputs)}:duration=first:dropout_transition=2[aout]")

    escaped_srt = srt_file.replace(":", "\\:").replace("\\", "/")
    vf_sub = f"subtitles='{escaped_srt}':force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=30'"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", "".join(filter_parts),
        "-vf", vf_sub,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    subprocess.run(cmd, check=True)
    # Cleanup intermediate voice segments
    for seg in segments:
        if os.path.exists(seg["audio_file"]):
            os.remove(seg["audio_file"])
