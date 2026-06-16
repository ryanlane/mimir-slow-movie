"""Video processing service using ffmpeg/ffprobe for frame extraction."""

from __future__ import annotations

import io
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("mimir.channels.slowmovie.video")

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    logger.warning("[SlowMovie] Pillow not installed – image resizing unavailable")
    _PIL_AVAILABLE = False

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
_FFPROBE_AVAILABLE = shutil.which("ffprobe") is not None

if not _FFMPEG_AVAILABLE:
    logger.warning("[SlowMovie] ffmpeg not found in PATH – frame extraction unavailable")
if not _FFPROBE_AVAILABLE:
    logger.warning("[SlowMovie] ffprobe not found in PATH – video introspection unavailable")

# Seconds of precise decoding used after a fast keyframe seek.
# Fast-seek lands on the nearest keyframe before the target; we then decode
# up to this many seconds to reach the exact frame.  10 s ≈ 240 frames @24fps.
_FINE_SEEK_WINDOW = 10.0


class VideoService:
    """Handles video introspection and frame extraction using ffmpeg."""

    @staticmethod
    def is_available() -> bool:
        return _FFMPEG_AVAILABLE and _FFPROBE_AVAILABLE and _PIL_AVAILABLE

    @staticmethod
    def get_video_info(video_path: Path) -> dict:
        """Return total_frames, fps, width, height, duration_seconds for a video file."""
        empty = {"total_frames": 0, "fps": 0.0, "width": 0, "height": 0, "duration_seconds": 0.0}
        if not _FFPROBE_AVAILABLE:
            return empty
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams", "-show_format",
                    str(video_path),
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.warning("[SlowMovie] ffprobe returned %d for %s", result.returncode, video_path)
                return empty

            data = json.loads(result.stdout)
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )
            if not video_stream:
                return empty

            fps = _parse_fps(video_stream.get("r_frame_rate") or video_stream.get("avg_frame_rate", "0/1"))
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            duration = 0.0
            dur_str = data.get("format", {}).get("duration") or video_stream.get("duration", "0")
            try:
                duration = float(dur_str)
            except (ValueError, TypeError):
                pass

            nb = video_stream.get("nb_frames")
            if nb and nb != "N/A":
                try:
                    total_frames = int(nb)
                except ValueError:
                    total_frames = int(duration * fps) if fps > 0 else 0
            else:
                total_frames = int(duration * fps) if fps > 0 else 0

            return {
                "total_frames": total_frames,
                "fps": round(fps, 3),
                "width": width,
                "height": height,
                "duration_seconds": round(duration, 2),
            }
        except Exception as exc:
            logger.error("[SlowMovie] ffprobe failed for %s: %s", video_path, exc)
            return empty

    @staticmethod
    def extract_frame(
        video_path: Path,
        frame_number: int,
        target_size: Optional[Tuple[int, int]] = None,
        fit_mode: str = "letterbox",
        fps: Optional[float] = None,
    ) -> Optional[bytes]:
        """Extract a single frame from a video, returning JPEG bytes.

        Uses a two-pass seek: fast keyframe seek followed by precise frame-level
        seek within a short window, so large frame offsets are fast and the result
        is still frame-accurate.
        """
        if not _FFMPEG_AVAILABLE or not _PIL_AVAILABLE:
            return None
        try:
            if fps is None or fps <= 0:
                fps = VideoService.get_video_info(video_path).get("fps") or 24.0

            timestamp = frame_number / fps

            if timestamp > _FINE_SEEK_WINDOW:
                coarse = timestamp - _FINE_SEEK_WINDOW
                fine = _FINE_SEEK_WINDOW
            else:
                coarse = 0.0
                fine = timestamp

            cmd = [
                "ffmpeg",
                "-ss", f"{coarse:.3f}",
                "-i", str(video_path),
                "-ss", f"{fine:.3f}",
                "-vframes", "1",
                "-f", "image2pipe",
                "-vcodec", "png",
                "pipe:1",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode != 0 or not result.stdout:
                logger.warning(
                    "[SlowMovie] ffmpeg frame extract failed (frame=%d, ts=%.3f): %s",
                    frame_number, timestamp, result.stderr.decode(errors="replace")[-200:],
                )
                return None

            img = Image.open(io.BytesIO(result.stdout)).convert("RGB")

            if target_size:
                if fit_mode == "crop":
                    img = _resize_crop(img, target_size)
                elif fit_mode == "stretch":
                    img = _resize_stretch(img, target_size)
                else:
                    img = _resize_letterbox(img, target_size)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92, optimize=True)
            return buf.getvalue()
        except Exception as exc:
            logger.error("[SlowMovie] Frame extraction failed: %s", exc)
            return None

    @staticmethod
    def extract_frame_to_file(
        video_path: Path,
        frame_number: int,
        output_path: Path,
        target_size: Optional[Tuple[int, int]] = None,
        fit_mode: str = "letterbox",
        fps: Optional[float] = None,
    ) -> bool:
        """Extract a frame and save it to disk. Returns True on success."""
        data = VideoService.extract_frame(
            video_path, frame_number, target_size, fit_mode=fit_mode, fps=fps,
        )
        if data is None:
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
        return True


def _parse_fps(rate_str: str) -> float:
    """Parse an ffprobe fraction fps string like '24000/1001' into a float."""
    try:
        if "/" in rate_str:
            num, den = rate_str.split("/")
            den = int(den)
            return int(num) / den if den > 0 else 0.0
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _resize_letterbox(img: "Image.Image", target: Tuple[int, int]) -> "Image.Image":
    tw, th = target
    iw, ih = img.size
    scale = min(tw / iw, th / ih)
    new_w, new_h = int(iw * scale), int(ih * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (tw, th), (0, 0, 0))
    canvas.paste(resized, ((tw - new_w) // 2, (th - new_h) // 2))
    return canvas


def _resize_crop(img: "Image.Image", target: Tuple[int, int]) -> "Image.Image":
    tw, th = target
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    new_w, new_h = int(iw * scale), int(ih * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _resize_stretch(img: "Image.Image", target: Tuple[int, int]) -> "Image.Image":
    return img.resize(target, Image.LANCZOS)
