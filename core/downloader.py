"""
Snatchr backend - wraps yt-dlp for metadata fetching and downloading.
Kept independent of the GUI so it can run on a worker thread.
"""
import subprocess
import json
import re


def has_ytdlp() -> bool:
    try:
        subprocess.run(["yt-dlp", "-h"], check=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], check=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def format_size(num_bytes) -> str:
    if not num_bytes:
        return "unknown size"
    n = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def get_video_info(url: str) -> dict:
    """Returns (info_dict, error_message). error_message is '' on success."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", url],
            capture_output=True, check=True, text=True
        )
        return json.loads(result.stdout), ""
    except subprocess.CalledProcessError as e:
        return {}, (e.stderr or "Unknown yt-dlp error").strip().splitlines()[-1]
    except json.JSONDecodeError:
        return {}, "Couldn't parse video info."
    except FileNotFoundError:
        return {}, "yt-dlp is not installed or not on PATH."


def get_mp4_formats(info: dict) -> list:
    """Returns mp4 video formats, best resolution first, with size + audio info attached."""
    if "formats" not in info:
        return []

    mp4_formats = [
        f for f in info["formats"]
        if f.get("ext") == "mp4" and f.get("vcodec", "none") != "none"
    ]
    mp4_formats.sort(key=lambda f: f.get("height") or 0, reverse=True)

    out = []
    for f in mp4_formats:
        out.append({
            "format_id": f["format_id"],
            "resolution": f.get("resolution") or f"{f.get('height', '?')}p",
            "fps": f.get("fps"),
            "filesize": f.get("filesize") or f.get("filesize_approx"),
            "has_audio": f.get("acodec", "none") != "none",
        })
    return out


_PROGRESS_RE = re.compile(r"(\d+(?:\.\d+)?)%")


def download_video(url: str, format_id: str, output_dir: str, on_progress=None, on_line=None):
    """
    Runs yt-dlp as a subprocess, streaming stdout so progress can be reported.
    on_progress(percent: float) is called as download percentage updates.
    on_line(str) is called with each raw output line (optional, for a log view).
    Returns (success: bool, message: str).
    """
    fmt_selector = f"{format_id}+bestaudio/{format_id}"
    cmd = [
        "yt-dlp",
        "-f", fmt_selector,
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--extractor-args", "youtube:player_client=tv,default",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        "--newline",
        url,
    ]

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
    except FileNotFoundError:
        return False, "yt-dlp is not installed or not on PATH."

    last_line = ""
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        last_line = line
        if on_line:
            on_line(line)
        match = _PROGRESS_RE.search(line)
        if match and on_progress:
            try:
                on_progress(float(match.group(1)))
            except ValueError:
                pass

    proc.wait()
    if proc.returncode == 0:
        if on_progress:
            on_progress(100.0)
        return True, "Download complete."
    return False, last_line or "Download failed."
