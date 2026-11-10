#!/usr/bin/env python3
"""
Full-edition toolchain smoke test.

Uses the app's own processing functions with the tools NiRepurpose resolves (tools/ first, then PATH):
  1. generate a sample JPEG + MP4 with ffmpeg,
  2. plant device metadata (Make/Model/GPS/date/Artist) with ExifTool,
  3. run NiRepurpose.repurpose_image / repurpose_video,
  4. confirm outputs are valid JPEG/MP4 and the planted metadata is gone.

Usage:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import NiRepurpose as ni  # noqa: E402

PLANTED_IMAGE = [
    "-EXIF:Make=SmokeTestMake",
    "-EXIF:Model=SmokeTestModel",
    "-EXIF:DateTimeOriginal=2024:05:01 10:00:00",
    "-EXIF:Artist=SmokeTestArtist",
    "-GPSLatitude=51.5",
    "-GPSLatitudeRef=N",
]
PLANTED_VIDEO = ["-Keys:Make=SmokeTestMake", "-Keys:Model=SmokeTestModel", "-ItemList:Artist=SmokeTestArtist"]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=300, **ni.subprocess_kwargs_no_window())


def metadata(exiftool: str, path: Path) -> dict:
    proc = run(ni.exiftool_argv(exiftool, "-j", "-a", "-G1", str(path)))
    return json.loads(proc.stdout.decode("utf-8", errors="replace"))[0]


def main() -> int:
    ffmpeg = ni.get_tool_path("ffmpeg")
    exiftool = ni.get_tool_path("exiftool")
    if not ffmpeg or not exiftool:
        print(f"FAIL: tools not found (ffmpeg={ffmpeg}, exiftool={exiftool})")
        return 1
    print(f"ffmpeg:   {ffmpeg}\n  {run([ffmpeg, '-hide_banner', '-version']).stdout.decode().splitlines()[0]}")
    print(f"exiftool: {exiftool}\n  {run(ni.exiftool_argv(exiftool, '-ver')).stdout.decode().strip()}")

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ni_smoke_") as tmp:
        work = Path(tmp)
        src_img, src_vid = work / "sample.jpg", work / "sample.mp4"
        gen = [
            [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x480:duration=1",
             "-frames:v", "1", str(src_img)],
            [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x480:duration=2:rate=25",
             "-f", "lavfi", "-i", "sine=duration=2", "-shortest", str(src_vid)],
        ]
        for cmd in gen:
            proc = run(cmd)
            if proc.returncode != 0:
                print(f"FAIL: could not generate sample media: {proc.stderr.decode(errors='replace')}")
                return 1
        run(ni.exiftool_argv(exiftool, "-overwrite_original", *PLANTED_IMAGE, str(src_img)))
        run(ni.exiftool_argv(exiftool, "-overwrite_original", *PLANTED_VIDEO, str(src_vid)))

        cases = [
            ("image", src_img, work / "out.jpg", ni.repurpose_image, "JPEG"),
            ("video", src_vid, work / "out.mp4", ni.repurpose_video, "MP4"),
        ]
        for label, src, out, func, file_type in cases:
            planted = json.dumps(metadata(exiftool, src))
            if "SmokeTestMake" not in planted:
                failures.append(f"{label}: could not plant test metadata on the source")
                continue
            ok, err = func(str(src), str(out), mirror_flip=True, ffmpeg_path=ffmpeg, exiftool_path=exiftool)
            if not ok:
                failures.append(f"{label}: processing failed: {err}")
                continue
            data = metadata(exiftool, out)
            leftovers = [k for k, v in data.items() if "SmokeTest" in str(v) or k.endswith(("GPSLatitude", "Make", "Model"))]
            problems = []
            if data.get("File:FileType") != file_type:
                problems.append(f"expected {file_type}, got {data.get('File:FileType')}")
            if leftovers:
                problems.append(f"metadata not stripped: {leftovers}")
            if label == "video" and not str(data.get("QuickTime:Duration", "")).strip():
                problems.append("output has no duration")
            failures.extend(f"{label}: {p}" for p in problems)
            if not problems:
                size = data.get("Composite:ImageSize", "?")
                print(f"PASS {label}: {file_type} {size}, {out.stat().st_size} bytes, planted metadata removed")

    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
