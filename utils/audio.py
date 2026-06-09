"""Pure macOS text-to-speech helpers (no streamlit)."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path


def macos_tts_audio(text: str, voice: str = "Majed") -> tuple[bytes, str] | None:
    cache_dir = Path(tempfile.gettempdir()) / "ottolingo_tts"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = hashlib.sha1(f"{voice}:{text}".encode("utf-8")).hexdigest()  # nosec B324
    aiff_path = cache_dir / f"{cache_key}.aiff"
    wav_path = cache_dir / f"{cache_key}.wav"

    if not aiff_path.exists():
        cmd = ["say", "-v", voice, "-o", str(aiff_path), text]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    if not wav_path.exists():
        convert_cmd = ["afconvert", "-f", "WAVE", "-d", "LEI16", str(aiff_path), str(wav_path)]
        try:
            subprocess.run(convert_cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return aiff_path.read_bytes(), "audio/aiff"

    return wav_path.read_bytes(), "audio/wav"


def list_macos_voices(voice_prefix: str, default_voice: str) -> list[str]:
    try:
        result = subprocess.run(["say", "-v", "?"], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [default_voice]

    voices: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, language = parts[0], parts[1]
        if language.startswith(voice_prefix):
            voices.append(name)

    if default_voice not in voices:
        voices.append(default_voice)

    return sorted(set(voices), key=str.lower)
