#!/usr/bin/env python3
"""Verifica que las dependencias de sistema necesarias para xSlou Clips AI
esten instaladas: ffmpeg, ffprobe, Python 3.11+, Node.js 18+."""
from __future__ import annotations

import shutil
import subprocess
import sys


def check(name: str, cmd: list[str], min_hint: str = "") -> bool:
    path = shutil.which(cmd[0])
    if not path:
        print(f"[FALTA] {name}: no encontrado en PATH. {min_hint}")
        return False
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        version_line = (out.stdout or out.stderr).splitlines()[0]
        print(f"[OK]    {name}: {version_line} ({path})")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {name}: {exc}")
        return False


def main() -> int:
    print("Verificando dependencias de xSlou Clips AI...\n")
    ok = True
    ok &= check("FFmpeg", ["ffmpeg", "-version"], "Instala con: winget install Gyan.FFmpeg (Windows) / brew install ffmpeg (macOS) / apt-get install ffmpeg (Linux)")
    ok &= check("FFprobe", ["ffprobe", "-version"])
    ok &= check("Python", [sys.executable, "--version"])
    ok &= check("Node.js", ["node", "--version"], "Instala Node 18+ desde https://nodejs.org")
    ok &= check("npm", ["npm", "--version"])

    print()
    if ok:
        print("Todo listo. Continua con docs/SETUP.md.")
        return 0
    print("Faltan dependencias. Revisa docs/SETUP.md antes de continuar.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
